use ahash::AHashMap;
use bzip2::read::MultiBzDecoder;
use rusqlite::{params, Connection};
use std::io::{BufRead, BufReader};
use std::sync::mpsc;
use std::thread;

use super::PageviewResult;
use crate::errors::PhotoMetaError;

const BATCH_SIZE: usize = 20_000;
const PAGEVIEW_BASE_URL: &str = "https://dumps.wikimedia.org/other/pageview_complete/monthly";

pub fn run_month(
    build_db_path: &str,
    year_month: &str,
    project: &str,
) -> Result<PageviewResult, PhotoMetaError> {
    _create_pageview_table_if_needed(build_db_path)?;

    // Build URL: year_month = "2026-04"
    let year = &year_month[..4];
    let ym_compact = year_month.replace('-', "");
    let url = format!(
        "{}/{}/{}/pageviews-{}-user.bz2",
        PAGEVIEW_BASE_URL, year, year_month, ym_compact
    );

    let sitelink_key = _project_to_sitelink_key(project);

    // Build title -> geonames_id map from wikidata_titles for this project
    let conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;
    let title_map = _load_title_map(&conn, &sitelink_key)?;
    drop(conn); // release before write transaction

    let project_prefix = format!("{} ", project);

    // High channel capacity to avoid blocking if SQLite slows down
    let (tx_chan, rx_chan) = mpsc::sync_channel::<(i64, i64)>(100_000);

    let producer = thread::spawn(move || -> Result<(u64, u64), PhotoMetaError> {
        // Stream, parse, write — no temp file
        let resp = ureq::Agent::new_with_config(
            ureq::config::Config::builder()
                .user_agent("Photidy/0.2.0 (https://github.com/rdawebb/Photidy; rdawebb@gmail.com)")
                .build(),
        )
        .get(&url)
        .call()
        .map_err(|e| {
            eprintln!("Pageviews: HTTP error: {}", e);
            PhotoMetaError::Io(std::io::Error::new(
                std::io::ErrorKind::Other,
                e.to_string(),
            ))
        })?;

        let bz = MultiBzDecoder::new(BufReader::with_capacity(
            4 * 1024 * 1024,
            resp.into_body().into_reader(),
        ));
        let mut reader = BufReader::new(bz);

        let mut lines_parsed = 0u64;
        let mut places_matched = 0u64;

        // View aggregation map: title hash -> view count
        let mut views_map: AHashMap<i64, i64> = AHashMap::new();

        // Persistent string buffer to avoid allocations
        let mut line = String::with_capacity(256);

        while reader.read_line(&mut line).map_err(PhotoMetaError::Io)? > 0 {
            if !line.starts_with(&project_prefix) {
                line.clear();
                continue;
            }

            lines_parsed += 1;
            let trimmed = line.trim_end(); // Strip trailing newline

            let mut parts = trimmed.splitn(4, ' ');
            let _project = parts.next();
            let Some(raw_title) = parts.next() else {
                line.clear();
                continue;
            };
            let Some(count_str) = parts.next() else {
                line.clear();
                continue;
            };
            let Ok(view_count) = count_str.parse::<i64>() else {
                line.clear();
                continue;
            };

            // Normalise title: percent-decode + underscores to spaces
            let title = _decode_title(raw_title);
            let Some(&geonames_id) = title_map.get(title.as_str()) else {
                line.clear();
                continue;
            };

            places_matched += 1;

            // Aggregate view count for this geonames_id
            *views_map.entry(geonames_id).or_insert(0) += view_count;

            // Clear line to reuse for next iteration
            line.clear();
        }

        // Push aggregated view counts onto channel
        for (geonames_id, total_views) in views_map {
            if tx_chan.send((geonames_id, total_views)).is_err() {
                break;
            }
        }

        Ok((lines_parsed, places_matched))
    });

    let mut conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;

    // Set PRAGMA options for performance
    conn.execute_batch(
        "PRAGMA synchronous = OFF;
             PRAGMA journal_mode = WAL;
             PRAGMA cache_size = -200000;
             PRAGMA temp_store = MEMORY;
             PRAGMA mmap_size = 2147483648;",
    )
    .map_err(PhotoMetaError::Database)?;

    let tx = conn.transaction().map_err(PhotoMetaError::Database)?;

    // Remove existing data for this month (idempotent reruns)
    tx.execute(
        "DELETE FROM pageview_monthly WHERE year_month = ?1",
        params![year_month],
    )
    .map_err(PhotoMetaError::Database)?;

    let mut batch: Vec<(i64, i64)> = Vec::with_capacity(BATCH_SIZE);

    // rx_chan yields values until the producer thread finishes
    for (geonames_id, view_count) in rx_chan {
        batch.push((geonames_id, view_count));

        // Can't borrow year_month into batch easily with lifetimes here,
        // so flushed eagerly and written directly
        if batch.len() >= BATCH_SIZE {
            _flush_pageviews(&tx, &batch, year_month)?;
            batch.clear();
        }
    }

    if !batch.is_empty() {
        _flush_pageviews(&tx, &batch, year_month)?;
    }

    tx.commit().map_err(PhotoMetaError::Database)?;

    // Wait for the producer thread to exit and retrieve its parsing stats
    let (lines_parsed, places_matched) = producer.join().unwrap()?;

    Ok(PageviewResult {
        year_month: year_month.to_string(),
        lines_parsed,
        places_matched,
    })
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

// Converts a project name to Wikidata sitelink key
fn _project_to_sitelink_key(project: &str) -> String {
    if let Some(lang) = project.strip_suffix(".wikipedia") {
        format!("{}wiki", lang)
    } else {
        project.to_string()
    }
}

fn _decode_title(raw: &str) -> String {
    // Fast path with no percent-encoding or underscores
    if !raw.contains('%') && !raw.contains('_') {
        return raw.to_string();
    }
    let decoded_cow = percent_encoding::percent_decode_str(raw).decode_utf8_lossy();

    // If there are no underscores, return the decoded string as-is
    if !decoded_cow.contains('_') {
        return decoded_cow.into_owned();
    }

    // Replace underscores with spaces
    let mut final_string = String::with_capacity(decoded_cow.len());
    for c in decoded_cow.chars() {
        if c == '_' {
            final_string.push(' ');
        } else {
            final_string.push(c);
        }
    }

    final_string
}

fn _create_pageview_table_if_needed(build_db_path: &str) -> Result<(), PhotoMetaError> {
    let conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS pageview_monthly (
            geonames_id INTEGER NOT NULL,
            year_month  TEXT    NOT NULL,
            view_count  INTEGER NOT NULL,
            PRIMARY KEY (geonames_id, year_month)
        );
        CREATE INDEX IF NOT EXISTS idx_pv_year_month
            ON pageview_monthly (year_month);
    ",
    )
    .map_err(PhotoMetaError::Database)
}

fn _flush_pageviews(
    tx: &rusqlite::Transaction,
    batch: &[(i64, i64)],
    year_month: &str,
) -> Result<(), PhotoMetaError> {
    let mut stmt = tx
        .prepare_cached(
            "INSERT OR REPLACE INTO pageview_monthly (geonames_id, year_month, view_count)
         VALUES (?1, ?2, ?3)",
        )
        .map_err(PhotoMetaError::Database)?;
    for (geonames_id, view_count) in batch {
        stmt.execute(params![geonames_id, year_month, view_count])
            .map_err(PhotoMetaError::Database)?;
    }
    Ok(())
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
        assert_eq!(_decode_title("London"), "London");
    }

    #[test]
    fn decode_title_underscores_to_spaces() {
        assert_eq!(_decode_title("New_York_City"), "New York City");
    }

    #[test]
    fn decode_title_percent_encoded() {
        assert_eq!(_decode_title("S%C3%A3o_Paulo"), "São Paulo");
    }

    #[test]
    fn decode_title_mixed_encoding() {
        assert_eq!(_decode_title("Caf%C3%A9_de_Flore"), "Café de Flore");
    }

    #[test]
    fn decode_title_no_encoding_fast_path() {
        // Must not call percent_decode, covered implicitly by not panicking
        assert_eq!(_decode_title("Paris"), "Paris");
    }
}
