use flate2::read::MultiGzDecoder;
use memchr::memmem;
use rusqlite::{params, Connection};
use sonic_rs::{JsonContainerTrait, JsonValueTrait, Value};
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

    // Convert projects to owned Strings so they can be safely moved into the background thread
    let target_projects: Vec<String> = projects.iter().map(|p| p.to_string()).collect();
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

        // Wikidata dump is a JSON array — one entity per line (after first/last)
        // Each line (trimmed of trailing comma) is a self-contained JSON object
        let reader = std::io::BufReader::new(gz);

        let mut entities_streamed = 0u64;
        let mut entities_matched = 0u64;

        let needle = memmem::Finder::new("\"P1566\"");

        for line in reader.lines() {
            let line = line.map_err(PhotoMetaError::Io)?;
            let trimmed = line.trim().trim_end_matches(',');
            if trimmed == "[" || trimmed == "]" || trimmed.is_empty() {
                continue;
            }

            entities_streamed += 1;
            // For testing: limit to max_streamed if set
            if entities_streamed > max_streamed.unwrap_or(u64::MAX) {
                eprintln!(
                    "Wikidata: {:>10} streamed  {:>8} matched in {:?}",
                    entities_streamed,
                    entities_matched,
                    start_time.elapsed()
                );
                break;
            }

            if entities_streamed % LOG_INTERVAL == 0 {
                eprintln!(
                    "Wikidata: {:>10} streamed  {:>8} matched in {:?}",
                    entities_streamed,
                    entities_matched,
                    start_time.elapsed()
                );
            }

            // Skip entities that don't have a P1566 claim (GeoNames ID)
            if needle.find(trimmed.as_bytes()).is_none() {
                continue;
            }

            let Ok(entity): Result<Value, _> = sonic_rs::from_str::<Value>(trimmed) else {
                continue;
            };

            // Extract P1566 (GeoNames ID)
            let Some(raw_id) = entity["claims"]["P1566"]
                .get(0)
                .and_then(|c| c["mainsnak"]["datavalue"]["value"].as_str())
            else {
                continue;
            };

            let Ok(geonames_id) = raw_id.parse::<i64>() else {
                continue;
            };

            entities_matched += 1;

            // Sitelink count and enwiki title
            let sitelinks = &entity["sitelinks"];
            let sitelink_count = sitelinks.as_object().map(|o| o.len()).unwrap_or(0);
            let score = (sitelink_count as f64 / SITELINK_CEILING).min(1.0);

            let mut wiki_titles = Vec::with_capacity(target_projects.len());

            for proj in &target_projects {
                if let Some(title) = sitelinks[proj]["title"].as_str() {
                    wiki_titles.push((proj.clone(), title.to_string()));
                }
            }

            let payload = ParsedEntity {
                geonames_id,
                score,
                wiki_titles,
            };

            if tx_chan.send(payload).is_err() {
                break;
            }
        }

        Ok((entities_streamed, entities_matched))
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
    let (entities_streamed, entities_matched) = producer.join().unwrap()?;

    Ok(WikidataResult {
        entities_streamed,
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
