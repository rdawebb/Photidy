use std::path::Path;
use rusqlite::{Connection, params};

use crate::compat;
use crate::errors::DbError;
use crate::models::{Candidate, PlaceKind};

pub fn db_filename() -> &'static str {
    "places_v0.1.db"
}

pub fn validate_db(path: &Path) -> Result<(), DbError> {
    let conn = Connection::open(path)
        .map_err(DbError::Open)?;
    
    compat::assert_compatible(&conn)
        .map_err(DbError::Incompatible)?;

    Ok(())
}

pub fn get_db(path: &Path) -> Result<Connection, DbError> {
    let conn = Connection::open(path)
        .map_err(DbError::Open)?;

    compat::assert_compatible(&conn)
        .map_err(DbError::Incompatible)?;

    Ok(conn)
}

pub fn fetch_candidates(
    path: &Path,
    lat: f64,
    lon: f64,
) -> Result<Vec<Candidate>, DbError> {
    let conn = get_db(path)?;

    let delta = 0.5; // degrees (~55 km)
    let mut stmt = conn.prepare(
        r#"
        SELECT name, country, admin, lat, lon, kind, importance
        FROM places
        WHERE lat BETWEEN ? AND ?
            AND lon BETWEEN ? AND ?
        ORDER BY importance DESC
        LIMIT 50
        "#,
    ).map_err(DbError::Query)?;

    let rows = stmt.query_map(
        params![lat - delta, lat + delta, lon - delta, lon + delta],
        |row| {
            let kind: String = row.get(5)?;
            Ok(Candidate {
                name: row.get(0)?,
                country: row.get(1)?,
                admin: row.get(2)?,
                lat: row.get(3)?,
                lon: row.get(4)?,
                kind: match kind.as_str() {
                    "landmark" => PlaceKind::Landmark,
                    "city" => PlaceKind::City,
                    _ => PlaceKind::Town,
                },
                importance: row.get(6)?,
            })
        },
    ).map_err(DbError::Query)?;

    rows.collect::<Result<_, _>>()
        .map_err(DbError::Query)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use tempfile::NamedTempFile;

    fn setup_test_db() -> (NamedTempFile, PathBuf) {
        let temp_file = NamedTempFile::new()
            .expect("Failed to create temp file");
        let path = temp_file.path().to_path_buf();

        let conn = Connection::open(&path)
            .expect("Failed to open test DB");

        conn.execute_batch(
            "CREATE TABLE meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )"
        ).expect("Failed to create meta table");

        conn.execute(
            "INSERT INTO meta VALUES (?, ?)",
            params!["db_version", env!("CARGO_PKG_VERSION")],
        ).expect("Failed to insert version");

        conn.execute_batch(
            "CREATE TABLE places (
                name TEXT,
                country TEXT,
                admin TEXT,
                lat REAL,
                lon REAL,
                kind TEXT,
                importance REAL
            )"
        ).expect("Failed to create test table");

        conn.execute(
            "INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?)",
            params!["London", "UK", Some("London"), 51.5074, -0.1278, "city", 0.9],
        ).expect("Failed to insert test data");

        conn.execute(
            "INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?)",
            params!["Richmond", "UK", Some("Richmond-upon-Thames"), 51.4415, -0.3005, "town", 0.7],
        ).expect("Failed to insert test data");

        conn.execute(
            "INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?)",
            params!["Tower Bridge", "UK", Some("London"), 51.5055, -0.0754, "landmark", 0.95],
        ).expect("Failed to insert test data");

        drop(conn);
        (temp_file, path)
    }

    #[test]
    fn test_fetch_candidates_returns_all_in_range() {
        let (_temp, path) = setup_test_db();
        let result = fetch_candidates(&path, 51.5074, -0.1278);

        assert!(result.is_ok());
        let candidates = result.unwrap();
        assert_eq!(candidates.len(), 3); // All three entries are within range
    }

    #[test]
    fn test_fetch_candidates_filters_by_distance() {
        let (_temp, path) = setup_test_db();
        let result = fetch_candidates(&path, 0.0, 0.0);

        assert!(result.is_ok());
        let candidates = result.unwrap();
        assert_eq!(candidates.len(), 0); // No entries are within range
    }

    #[test]
    fn test_fetch_candidates_converts_string_kind_to_enum() {
        let (_temp, path) = setup_test_db();
        let result = fetch_candidates(&path, 51.5074, -0.1278);

        assert!(result.is_ok());
        let candidates = result.unwrap();
        
        for candidate in candidates {
            match candidate.name.as_str() {
                "London" => assert_eq!(candidate.kind, PlaceKind::City),
                "Richmond" => assert_eq!(candidate.kind, PlaceKind::Town),
                "Tower Bridge" => assert_eq!(candidate.kind, PlaceKind::Landmark),
                _ => panic!("Unexpected candidate name"),
            }
        }
    }

    #[test]
    fn test_fetch_candidates_respects_limit() {
        let (_temp, path) = setup_test_db();
        let conn = Connection::open(&path)
            .expect("Failed to open test DB");

        // Insert additional entries to exceed the limit
        for i in 0..60 {
            let name = format!("Place {}", i);
            conn.execute(
                "INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?)",
                params![name, "UK", None::<String>, 51.5 + (i as f64 * 0.001), -0.1 - (i as f64 * 0.001), "town", 0.5],
            ).expect("Failed to insert test data");
        }
        drop(conn);

        let result = fetch_candidates(&path, 51.5074, -0.1278);

        assert!(result.is_ok());
        let candidates = result.unwrap();
        assert_eq!(candidates.len(), 50); // Should respect the LIMIT of 50
    }

    #[test]
    fn test_fetch_candidates_orders_by_importance() {
        let (_temp, path) = setup_test_db();
        let result = fetch_candidates(&path, 51.5074, -0.1278);

        assert!(result.is_ok());
        let candidates = result.unwrap();
        
        let mut last_importance = std::f64::INFINITY;
        for candidate in candidates {
            assert!(candidate.importance <= last_importance);
            last_importance = candidate.importance;
        }
    }

    #[test]
    fn test_fetch_candidates_with_invalid_db_path() {
        let invalid_path = Path::new("/nonexistent/path/places.db");
        let result = fetch_candidates(invalid_path, 51.5074, -0.1278);
        assert!(result.is_err());
    }

    #[test]
    fn test_fetch_candidates_with_no_matching_entries() {
        let (_temp, path) = setup_test_db();
        let result = fetch_candidates(&path, 90.0, 180.0);
        assert!(result.is_ok());
        let candidates = result.unwrap();
        assert_eq!(candidates.len(), 0);
    }

    #[test]
    fn test_fetch_candidates_with_null_admin_field() {
        let (_temp, path) = setup_test_db();
        let conn = Connection::open(&path)
            .expect("Failed to open test DB");

        conn.execute(
            "INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?)",
            params!["NoAdminPlace", "UK", None::<String>, 51.5, -0.1, "town", 0.6],
        ).expect("Failed to insert test data");
        drop(conn);

        let result = fetch_candidates(&path, 51.5, -0.1);
        assert!(result.is_ok());
        let candidates = result.unwrap();
        let no_admin_place = candidates.iter().find(|c| c.name == "NoAdminPlace");
        assert!(no_admin_place.is_some());
        assert!(no_admin_place.unwrap().admin.is_none());
    }

    #[test]
    fn test_fetch_candidates_with_unknown_kind() {
        let (_temp, path) = setup_test_db();
        let conn = Connection::open(&path)
            .expect("Failed to open test DB");

        conn.execute(
            "INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?)",
            params!["UnknownPlace", "UK", Some("SomeAdmin"), 51.5, -0.1, "unknown_kind", 0.6],
        ).expect("Failed to insert test data");
        drop(conn);

        let result = fetch_candidates(&path, 51.5, -0.1);
        assert!(result.is_ok());
        let candidates = result.unwrap();
        let unknown = candidates.iter().find(|c| c.name == "UnknownPlace");
        assert!(unknown.is_some());
        assert_eq!(unknown.unwrap().kind, PlaceKind::Town); // Default to Town
    }
}
