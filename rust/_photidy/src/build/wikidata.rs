use ahash::AHashMap;
use flate2::read::MultiGzDecoder;
use memchr::memmem;
use percent_encoding::percent_decode_str;
use rusqlite::{params, Connection};
use std::io::{BufRead, BufReader};
use std::sync::mpsc;
use std::thread;

use super::WikidataResult;
use crate::errors::PhotoMetaError;

const BATCH_SIZE: usize = 20_000;
const SITELINK_CEILING: f64 = 300.0;
const LOG_INTERVAL: u64 = 1_000_000;

struct ParsedEntity {
    geonames_id: i64,
    score: f64,
    wiki_titles: Vec<(String, String)>,
}

// Per-entity state accumulator across RDF lines
struct EntityAccumulator {
    geonames_id: i64,
    sitelink_count: u32,
    wiki_titles: Vec<(String, String)>,
}

pub fn run(
    build_db_path: &str,
    source: &str,
    projects: Vec<String>,
    max_streamed: Option<u64>,
) -> Result<WikidataResult, PhotoMetaError> {
    let start_time = std::time::Instant::now();

    let mut conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;

    // Set PRAGMA options to optimise speed
    conn.execute_batch(
        "PRAGMA synchronous = OFF;
             PRAGMA journal_mode = WAL;
             PRAGMA cache_size = -200000;
             PRAGMA temp_store = MEMORY;
             PRAGMA mmap_size = 2147483648;",
    )
    .map_err(PhotoMetaError::Database)?;

    _create_wikidata_titles_table(&conn)?;

    // Move projects into the producer thread
    let target_projects: Vec<String> = projects;
    let source_str = source.to_string();

    // High channel capacity to avoid blocking if SQLite slows down
    let (tx_chan, rx_chan) = mpsc::sync_channel::<ParsedEntity>(100_000);

    let producer = thread::spawn(move || -> Result<(u64, u64), PhotoMetaError> {
        let stream: Box<dyn std::io::Read> = if source_str.starts_with("http") {
            let resp = ureq::Agent::new_with_config(
                ureq::config::Config::builder()
                    .user_agent(
                        "Photidy/0.2.0 (https://github.com/rdawebb/Photidy; rdawebb@gmail.com)",
                    )
                    .build(),
            )
            .get(source_str)
            .call()
            .map_err(|e| {
                eprintln!("Wikidata: HTTP error: {}", e);
                PhotoMetaError::Io(std::io::Error::new(
                    std::io::ErrorKind::Other,
                    e.to_string(),
                ))
            })?;

            Box::new(resp.into_body().into_reader())
        } else {
            Box::new(std::fs::File::open(source_str).map_err(PhotoMetaError::Io)?)
        };

        let gz = MultiGzDecoder::new(BufReader::with_capacity(4 * 1024 * 1024, stream));

        let mut reader = std::io::BufReader::with_capacity(1 << 20, gz);

        let mut lines_parsed = 0u64;
        let mut entities_matched = 0u64;

        // RDF NT format: one triple per line, entities grouped but not contiguous
        // Sitelinks are inverted: the Wikipedia URL is the subject, the QID is the object
        // All P1566 entities are accumulated in a map and flushed after the loop
        let finder_p1566 = memmem::Finder::new("/prop/direct/P1566>");
        let finder_article = memmem::Finder::new("schema.org/Article>");
        let finder_about = memmem::Finder::new("schema.org/about>");

        // QID -> EntityAccumulator
        let mut accum: AHashMap<i64, EntityAccumulator> = AHashMap::new();

        // Buffered URL from schema:Article lines, resolved on schema:about lines
        let mut pending_url: Option<String> = None;

        let mut buf: Vec<u8> = Vec::with_capacity(256);
        loop {
            buf.clear();
            let n = reader
                .read_until(b'\n', &mut buf)
                .map_err(PhotoMetaError::Io)?;
            if n == 0 {
                break;
            }

            // Trim whitespace + trailing commas on bytes
            let mut trimmed = buf.trim_ascii();
            while let Some(s) = trimmed.strip_suffix(b",") {
                trimmed = s;
            }
            if trimmed.is_empty() {
                continue;
            }

            lines_parsed += 1;
            // For testing: limit to max_streamed if set
            if lines_parsed >= max_streamed.unwrap_or(u64::MAX) {
                eprintln!(
                    "Wikidata: {:>10} streamed  {:>8} matched in {:?}",
                    lines_parsed,
                    entities_matched,
                    start_time.elapsed()
                );
                break;
            }

            if lines_parsed % LOG_INTERVAL == 0 {
                eprintln!(
                    "Wikidata: {:>10} streamed  {:>8} matched in {:?}",
                    lines_parsed,
                    entities_matched,
                    start_time.elapsed()
                );
            }

            // Only lines that hit a finder get validated as UTF-8
            if finder_article.find(trimmed).is_some() {
                if let Ok(s) = std::str::from_utf8(trimmed) {
                    pending_url = _extract_subject(s).map(str::to_owned);
                }
                continue;
            }

            if finder_about.find(trimmed).is_some() {
                if let Ok(s) = std::str::from_utf8(trimmed) {
                    if let Some(url) = pending_url.take() {
                        if let Some(qid) = _extract_qid_from_object(s) {
                            if let Some(entry) = accum.get_mut(&qid) {
                                entry.sitelink_count += 1;
                                if let Some(project) = _url_to_project(&url) {
                                    if target_projects.contains(&project) {
                                        if let Some(title) = _extract_title_from_url(&url) {
                                            entry.wiki_titles.push((project, title));
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                continue;
            }

            pending_url = None;

            if finder_p1566.find(trimmed).is_some() {
                if let Ok(s) = std::str::from_utf8(trimmed) {
                    if let (Some(qid), Some(geonames_id)) =
                        (_extract_qid_from_subject(s), _extract_p1566_value(s))
                    {
                        // Insert only if the QID is not already present
                        accum.entry(qid).or_insert_with(|| {
                            entities_matched += 1;
                            EntityAccumulator {
                                geonames_id,
                                sitelink_count: 0,
                                wiki_titles: Vec::new(),
                            }
                        });
                    }
                }
            }
        }

        // Flush the accumulator to the channel
        for (_qid, entry) in accum {
            let score = (entry.sitelink_count as f64 / SITELINK_CEILING).min(1.0);
            let payload = ParsedEntity {
                geonames_id: entry.geonames_id,
                score,
                wiki_titles: entry.wiki_titles,
            };
            if tx_chan.send(payload).is_err() {
                break;
            }
        }

        Ok((lines_parsed, entities_matched))
    });

    let tx = conn.transaction().map_err(PhotoMetaError::Database)?;
    let (mut places_updated, mut titles_mapped) = (0u64, 0u64);

    let mut sitelink_batch: Vec<(f64, i64)> = Vec::with_capacity(BATCH_SIZE);
    let mut title_batch: Vec<(i64, String, String)> = Vec::with_capacity(BATCH_SIZE);

    for parsed in rx_chan {
        sitelink_batch.push((parsed.score, parsed.geonames_id));

        for (project, title) in parsed.wiki_titles {
            title_batch.push((parsed.geonames_id, project, title));
            titles_mapped += 1;
        }

        if sitelink_batch.len() >= BATCH_SIZE {
            places_updated += _flush_sitelinks(&tx, &sitelink_batch)?;
            sitelink_batch.clear();
        }
        if title_batch.len() >= BATCH_SIZE {
            _flush_titles(&tx, &title_batch)?;
            title_batch.clear();
        }
    }

    // Flush remainders
    if !sitelink_batch.is_empty() {
        places_updated += _flush_sitelinks(&tx, &sitelink_batch)?;
    }
    if !title_batch.is_empty() {
        _flush_titles(&tx, &title_batch)?;
    }

    tx.commit().map_err(PhotoMetaError::Database)?;

    // Wait for the producer to finish and get the results
    let (lines_parsed, entities_matched) = producer.join().unwrap()?;

    Ok(WikidataResult {
        lines_parsed,
        entities_matched,
        places_updated,
        titles_mapped,
    })
}

fn _create_wikidata_titles_table(conn: &Connection) -> Result<(), PhotoMetaError> {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS wikidata_titles (
            geonames_id INTEGER NOT NULL,
            project     TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            PRIMARY KEY (geonames_id, project)
        );
        CREATE INDEX IF NOT EXISTS idx_wikidata_titles_title
            ON wikidata_titles (project, title);
    ",
    )
    .map_err(PhotoMetaError::Database)
}

// Extracts the subject line from a NT triple
fn _extract_subject(line: &str) -> Option<&str> {
    let start = line.find('<')? + 1;
    let end = line[start..].find('>')? + start;
    Some(&line[start..end])
}

// Extracts the QID from the object position of a triple whose subject is a Wikipedia URL
fn _extract_qid_from_object(line: &str) -> Option<i64> {
    let mut iter = line.splitn(4, '>');
    iter.next()?;
    iter.next()?;
    let third = iter.next()?;
    let q_pos = third.rfind("/Q")? + 2;
    third[q_pos..].parse::<i64>().ok()
}

// Extracts the QID from the subject position of a P1566 triple
fn _extract_qid_from_subject(line: &str) -> Option<i64> {
    let start = line.find("/Q")? + 2;
    let end = line[start..].find('>')? + start;
    line[start..end].parse::<i64>().ok()
}

// Extracts the GeoNames ID from the P1566 triple
fn _extract_p1566_value(line: &str) -> Option<i64> {
    let start = line.find('"')? + 1;
    let end = line[start..].find('"')? + start;
    line[start..end].parse::<i64>().ok()
}

// Converts a Wikipedia/Wikimedia URL host into the project key used by the target_projects
fn _url_to_project(url: &str) -> Option<String> {
    let host_and_path = url.strip_prefix("https://")?;
    let slash = host_and_path.find('/')?;
    let host = &host_and_path[..slash];

    let mut parts = host.splitn(3, '.');
    let lang = parts.next()?;
    let site = parts.next()?;

    let project = match site {
        "wikipedia" => format!("{}wiki", lang),
        "wikimedia" => format!("{}wiki", lang),
        other => format!("{}{}", lang, other),
    };

    Some(project)
}

// Extracts and percent-decodes the title from the URL
fn _extract_title_from_url(url: &str) -> Option<String> {
    let marker = "/wiki/";
    let start = url.find(marker)? + marker.len();
    let encoded = &url[start..];
    let decoded = percent_decode_str(encoded).decode_utf8().ok()?.into_owned();
    Some(decoded)
}

fn _flush_sitelinks(
    tx: &rusqlite::Transaction,
    batch: &[(f64, i64)],
) -> Result<u64, PhotoMetaError> {
    let mut stmt = tx
        .prepare_cached("UPDATE places SET score_sitelinks = ?1 WHERE geonames_id = ?2")
        .map_err(PhotoMetaError::Database)?;
    let mut changed = 0u64;
    for (score, id) in batch {
        changed += stmt
            .execute(params![score, id])
            .map_err(PhotoMetaError::Database)? as u64;
    }
    Ok(changed)
}

fn _flush_titles(
    tx: &rusqlite::Transaction,
    batch: &[(i64, String, String)],
) -> Result<(), PhotoMetaError> {
    let mut stmt = tx
        .prepare_cached(
            "INSERT OR REPLACE INTO wikidata_titles (geonames_id, project, title)
         VALUES (?1, ?2, ?3)",
        )
        .map_err(PhotoMetaError::Database)?;
    for (id, project, title) in batch {
        stmt.execute(params![id, project, title])
            .map_err(PhotoMetaError::Database)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    fn setup_db() -> Connection {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch(
            "CREATE TABLE places (
                  geonames_id INTEGER PRIMARY KEY,
                  score_sitelinks REAL
               );
               CREATE TABLE wikidata_titles (
                  geonames_id INTEGER NOT NULL,
                  project     TEXT    NOT NULL,
                  title       TEXT    NOT NULL,
                  PRIMARY KEY (geonames_id, project)
               );",
        )
        .unwrap();
        conn
    }

    #[test]
    fn extract_subject_wikipedia_url() {
        let line = "<https://en.wikipedia.org/wiki/Belgium> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://schema.org/Article> .";
        assert_eq!(
            _extract_subject(line),
            Some("https://en.wikipedia.org/wiki/Belgium")
        );
    }

    #[test]
    fn extract_qid_from_object_q31() {
        let line = "<https://en.wikipedia.org/wiki/Belgium> <http://schema.org/about> <http://www.wikidata.org/entity/Q31> .";
        assert_eq!(_extract_qid_from_object(line), Some(31));
    }

    #[test]
    fn extract_qid_from_subject_p1566_line() {
        let line = "<http://www.wikidata.org/entity/Q31> <http://www.wikidata.org/prop/direct/P1566> \"2802361\" .";
        assert_eq!(_extract_qid_from_subject(line), Some(31));
    }

    #[test]
    fn extract_p1566_value_parses_geonames_id() {
        let line = "<http://www.wikidata.org/entity/Q31> <http://www.wikidata.org/prop/direct/P1566> \"2802361\" .";
        assert_eq!(_extract_p1566_value(line), Some(2802361));
    }

    #[test]
    fn url_to_project_wikipedia() {
        assert_eq!(
            _url_to_project("https://en.wikipedia.org/wiki/Belgium"),
            Some("enwiki".to_string())
        );
        assert_eq!(
            _url_to_project("https://fr.wikipedia.org/wiki/Belgique"),
            Some("frwiki".to_string())
        );
    }

    #[test]
    fn url_to_project_wikivoyage() {
        assert_eq!(
            _url_to_project("https://en.wikivoyage.org/wiki/Belgium"),
            Some("enwikivoyage".to_string())
        );
    }

    #[test]
    fn url_to_project_commons() {
        assert_eq!(
            _url_to_project("https://commons.wikimedia.org/wiki/File:Flag.svg"),
            Some("commonswiki".to_string())
        );
    }

    #[test]
    fn extract_title_plain_ascii() {
        assert_eq!(
            _extract_title_from_url("https://en.wikipedia.org/wiki/Belgium"),
            Some("Belgium".to_string())
        );
    }

    #[test]
    fn extract_title_percent_encoded() {
        assert_eq!(
            _extract_title_from_url("https://fr.wikipedia.org/wiki/Ren%C3%A9_Magritte"),
            Some("René_Magritte".to_string())
        );
    }

    #[test]
    fn extract_title_multibyte_encoded() {
        // zh.wikivoyage Belgium
        assert_eq!(
            _extract_title_from_url("https://zh.wikivoyage.org/wiki/%E6%AF%94%E5%88%A9%E6%97%B6"),
            Some("比利时".to_string())
        );
    }

    #[test]
    fn sitelink_score_caps_at_1() {
        // 300 sitelinks → score = 300/300 = 1.0 exactly
        let score = (300f64 / SITELINK_CEILING).min(1.0);
        assert_eq!(score, 1.0);
        // 600 sitelinks → still 1.0
        let score_over = (600f64 / SITELINK_CEILING).min(1.0);
        assert_eq!(score_over, 1.0);
    }

    #[test]
    fn flush_sitelinks_updates_existing_row() {
        let mut conn = setup_db();
        conn.execute("INSERT INTO places (geonames_id) VALUES (1234)", [])
            .unwrap();
        let tx = conn.transaction().unwrap();
        let changed = _flush_sitelinks(&tx, &[(0.75, 1234)]).unwrap();
        tx.commit().unwrap();
        assert_eq!(changed, 1);
        let score: f64 = conn
            .query_row(
                "SELECT score_sitelinks FROM places WHERE geonames_id = 1234",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert!((score - 0.75).abs() < 1e-10);
    }

    #[test]
    fn flush_sitelinks_skips_missing_geonames_id() {
        let mut conn = setup_db();
        let tx = conn.transaction().unwrap();
        let changed = _flush_sitelinks(&tx, &[(0.5, 9999)]).unwrap();
        tx.commit().unwrap();
        assert_eq!(changed, 0); // no matching row → 0 rows changed
    }

    #[test]
    fn flush_titles_inserts_and_replaces() {
        let mut conn = setup_db();
        conn.execute("INSERT INTO places (geonames_id) VALUES (42)", [])
            .unwrap();
        let batch = vec![(42i64, "enwiki".to_string(), "London".to_string())];
        let tx = conn.transaction().unwrap();
        _flush_titles(&tx, &batch).unwrap();
        tx.commit().unwrap();
        let title: String = conn
            .query_row(
                "SELECT title FROM wikidata_titles WHERE geonames_id = 42 AND project = 'enwiki'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(title, "London");
    }
}
