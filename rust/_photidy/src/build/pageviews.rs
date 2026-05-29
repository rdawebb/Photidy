use ahash::AHashMap;
use async_compression::tokio::bufread::BzDecoder;
use futures::stream::{FuturesUnordered, StreamExt};
use rusqlite::{params, Connection};
use std::borrow::Cow;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::Semaphore;
use tokio_util::io::StreamReader;

use super::PageviewResult;
use crate::errors::PhotoMetaError;

const MAX_CONCURRENT_DOWNLOADS: usize = 3;
const PAGEVIEW_BASE_URL: &str = "https://dumps.wikimedia.org/other/pageview_complete/monthly";

pub async fn run_months(
    build_db_path: &str,
    year_months: &[&str],
    project: &str,
) -> Result<Vec<PageviewResult>, PhotoMetaError> {
    _create_pageview_table_if_needed(build_db_path)?;

    let sitelink_key = _project_to_sitelink_key(project);

    // Load title map once: read-only and shared across all tasks
    let conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;
    let title_map = Arc::new(_load_title_map(&conn, &sitelink_key)?);
    drop(conn);

    let semaphore = Arc::new(Semaphore::new(MAX_CONCURRENT_DOWNLOADS));
    let client = Arc::new(
        reqwest::Client::builder()
            .user_agent("Photidy/0.2.0 (https://github.com/rdawebb/Photidy; rdawebb@gmail.com)")
            .build()
            .map_err(|e| PhotoMetaError::Io(std::io::Error::new(std::io::ErrorKind::Other, e)))?,
    );

    // Spawn all 12 tasks immediately, semaphore caps concurrency at 3
    let mut futures = FuturesUnordered::new();
    for &ym in year_months {
        let sem = semaphore.clone();
        let client = client.clone();
        let title_map = title_map.clone();
        let project = project.to_string();
        let ym = ym.to_string();

        futures.push(tokio::spawn(async move {
            let _permit = sem.acquire().await.unwrap();
            _fetch_and_parse(&client, &ym, &project, &title_map).await
        }));
    }

    // Open a single write connection, WAL mode set once here
    let mut conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;
    conn.execute_batch(
        "PRAGMA synchronous = OFF;
         PRAGMA journal_mode = WAL;
         PRAGMA cache_size = -200000;
         PRAGMA temp_store = MEMORY;
         PRAGMA mmap_size = 2147483648;",
    )
    .map_err(PhotoMetaError::Database)?;

    let mut results = Vec::with_capacity(year_months.len());

    // Write each month as it finishes
    while let Some(join_result) = futures.next().await {
        // Unwrap JoinError, then the inner Result
        let (ym, views_map, lines_parsed, places_matched) = join_result
            .map_err(|e| PhotoMetaError::Io(std::io::Error::new(std::io::ErrorKind::Other, e)))??;

        _write_month(&mut conn, &ym, &views_map)?;

        results.push(PageviewResult {
            year_month: ym,
            lines_parsed,
            places_matched,
        });
    }

    Ok(results)
}

async fn _fetch_and_parse(
    client: &reqwest::Client,
    year_month: &str,
    project: &str,
    title_map: &AHashMap<String, i64>,
) -> Result<(String, AHashMap<i64, i64>, u64, u64), PhotoMetaError> {
    let url = _build_url(year_month);

    let response = client
        .get(&url)
        .send()
        .await
        .and_then(|r| r.error_for_status())
        .map_err(|e| {
            eprintln!("Pageviews: HTTP error for {year_month}: {e}");
            PhotoMetaError::Io(std::io::Error::new(std::io::ErrorKind::Other, e))
        })?;

    // Bridge reqwest's byte stream → AsyncRead → BzDecoder → AsyncBufRead
    let stream = response
        .bytes_stream()
        .map(|r| r.map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e)));

    let stream_reader = StreamReader::new(stream);
    let bz = BzDecoder::new(BufReader::with_capacity(4 * 1024 * 1024, stream_reader));
    let mut reader = BufReader::with_capacity(256 * 1024, bz);

    let project_prefix = format!("{} ", project);
    let prefix = project_prefix.as_bytes();
    let mut views_map: AHashMap<i64, i64> = AHashMap::new();
    let mut line: Vec<u8> = Vec::with_capacity(256);
    let mut lines_parsed = 0u64;
    let mut places_matched = 0u64;

    loop {
        line.clear();
        let n = reader
            .read_until(b'\n', &mut line)
            .await
            .map_err(PhotoMetaError::Io)?;
        if n == 0 {
            break;
        }

        // Byte-level prefix filter: skips UTF-8 validation on the lines belonging to other projects
        if !line.starts_with(prefix) {
            continue;
        }

        lines_parsed += 1;
        let trimmed = line.trim_ascii_end();

        let mut parts = trimmed.splitn(4, |b| *b == b' ');
        parts.next(); // project column
        let Some(raw_title) = parts.next() else {
            continue;
        };
        let Some(count_bytes) = parts.next() else {
            continue;
        };

        // Only validate/parse the small slices actually needed
        let Ok(count_str) = std::str::from_utf8(count_bytes) else {
            continue;
        };
        let Ok(view_count) = count_str.parse::<i64>() else {
            continue;
        };
        let Ok(raw_title) = std::str::from_utf8(raw_title) else {
            continue;
        };

        let title = _decode_title(raw_title);
        let Some(&geonames_id) = title_map.get(&*title) else {
            continue;
        };

        places_matched += 1;
        *views_map.entry(geonames_id).or_insert(0) += view_count;
    }

    Ok((
        year_month.to_string(),
        views_map,
        lines_parsed,
        places_matched,
    ))
}

fn _write_month(
    conn: &mut Connection,
    year_month: &str,
    views_map: &AHashMap<i64, i64>,
) -> Result<(), PhotoMetaError> {
    let tx = conn.transaction().map_err(PhotoMetaError::Database)?;

    // Remove any existing data for this month before reinserting
    tx.execute(
        "DELETE FROM pageview_monthly WHERE year_month = ?1",
        params![year_month],
    )
    .map_err(PhotoMetaError::Database)?;

    {
        let mut stmt = tx
            .prepare_cached(
                "INSERT OR REPLACE INTO pageview_monthly (geonames_id, year_month, view_count)
                 VALUES (?1, ?2, ?3)",
            )
            .map_err(PhotoMetaError::Database)?;
        for (&geonames_id, &view_count) in views_map {
            stmt.execute(params![geonames_id, year_month, view_count])
                .map_err(PhotoMetaError::Database)?;
        }
    }

    tx.commit().map_err(PhotoMetaError::Database)?;
    Ok(())
}

fn _build_url(year_month: &str) -> String {
    let year = &year_month[..4];
    let ym_compact = year_month.replace('-', "");
    format!(
        "{}/{}/{}/pageviews-{}-user.bz2",
        PAGEVIEW_BASE_URL, year, year_month, ym_compact
    )
}

fn _load_title_map(
    conn: &Connection,
    project: &str,
) -> Result<AHashMap<String, i64>, PhotoMetaError> {
    let mut stmt = conn
        .prepare("SELECT title, geonames_id FROM wikidata_titles WHERE project = ?1")
        .map_err(PhotoMetaError::Database)?;

    let map = stmt
        .query_map(params![project], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
        })
        .map_err(PhotoMetaError::Database)?
        .filter_map(|r| r.ok())
        .collect();

    Ok(map)
}

fn _project_to_sitelink_key(project: &str) -> String {
    if let Some(lang) = project.strip_suffix(".wikipedia") {
        format!("{}wiki", lang)
    } else {
        project.to_string()
    }
}

fn _decode_title(raw: &str) -> Cow<'_, str> {
    if !raw.contains('%') && !raw.contains('_') {
        return Cow::Borrowed(raw);
    }
    let decoded = percent_encoding::percent_decode_str(raw).decode_utf8_lossy();
    if !decoded.contains('_') {
        return decoded;
    }
    let mut out = String::with_capacity(decoded.len());
    for c in decoded.chars() {
        out.push(if c == '_' { ' ' } else { c });
    }
    Cow::Owned(out)
}

fn _create_pageview_table_if_needed(build_db_path: &str) -> Result<(), PhotoMetaError> {
    let conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS pageview_monthly (
            geonames_id INTEGER NOT NULL,
            year_month  TEXT    NOT NULL,
            view_count  INTEGER NOT NULL,
            PRIMARY KEY (geonames_id, year_month)
        );
        CREATE INDEX IF NOT EXISTS idx_pv_year_month
            ON pageview_monthly (year_month);",
    )
    .map_err(PhotoMetaError::Database)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sitelink_key_wikipedia() {
        assert_eq!(_project_to_sitelink_key("en.wikipedia"), "enwiki");
        assert_eq!(_project_to_sitelink_key("fr.wikipedia"), "frwiki");
    }

    #[test]
    fn sitelink_key_non_wikipedia_passthrough() {
        assert_eq!(_project_to_sitelink_key("en.wikivoyage"), "en.wikivoyage");
    }

    #[test]
    fn decode_title_plain() {
        assert_eq!(&*_decode_title("London"), "London");
    }

    #[test]
    fn decode_title_underscores_to_spaces() {
        assert_eq!(&*_decode_title("New_York_City"), "New York City");
    }

    #[test]
    fn decode_title_percent_encoded() {
        assert_eq!(&*_decode_title("S%C3%A3o_Paulo"), "São Paulo");
    }

    #[test]
    fn decode_title_mixed_encoding() {
        assert_eq!(&*_decode_title("Caf%C3%A9_de_Flore"), "Café de Flore");
    }

    #[test]
    fn decode_title_no_encoding_fast_path() {
        assert_eq!(&*_decode_title("Paris"), "Paris");
    }

    #[test]
    fn build_url_format() {
        assert_eq!(
            _build_url("2026-04"),
            "https://dumps.wikimedia.org/other/pageview_complete/monthly/2026/2026-04/pageviews-202604-user.bz2"
        );
    }
}
