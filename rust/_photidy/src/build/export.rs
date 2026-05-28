use super::ExportResult;
use crate::errors::PhotoMetaError;
use rusqlite::{params, Connection};

pub fn run(
    build_db_path: &str,
    app_db_path: &str,
    regional_cap: u32,
) -> Result<ExportResult, PhotoMetaError> {
    // Delete existing app DB if present
    let app_path = std::path::Path::new(app_db_path);
    if app_path.exists() {
        std::fs::remove_file(app_path).map_err(PhotoMetaError::Io)?;
    }

    let build_conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;
    let app_conn = Connection::open(app_db_path).map_err(PhotoMetaError::Database)?;

    // Create minimal app schema
    app_conn
        .execute_batch(
            "
        CREATE TABLE places (
            id          INTEGER PRIMARY KEY,
            geonames_id INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            country     TEXT    NOT NULL,
            admin       TEXT,
            lat         REAL    NOT NULL,
            lon         REAL    NOT NULL,
            kind        TEXT    NOT NULL,
            importance  REAL    NOT NULL
        );
        CREATE TABLE meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    ",
        )
        .map_err(PhotoMetaError::Database)?;

    // Attach build DB and copy pruned places in one statement
    app_conn
        .execute_batch(&format!(
            "ATTACH DATABASE '{build_db_path}' AS build;

         INSERT INTO places (geonames_id, name, country, admin, lat, lon, kind, importance)
         SELECT geonames_id, name, country, admin, lat, lon, kind, importance
         FROM (
             SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY country, COALESCE(admin, '')
                        ORDER BY importance DESC
                    ) AS rn
             FROM build.places
             WHERE importance IS NOT NULL
         )
         WHERE rn <= {regional_cap};

         DETACH DATABASE build;"
        ))
        .map_err(PhotoMetaError::Database)?;

    // Copy meta, adding export info
    let mut stmt = build_conn
        .prepare("SELECT key, value FROM meta")
        .map_err(PhotoMetaError::Database)?;

    let rows: Vec<(String, String)> = stmt
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
        .map_err(PhotoMetaError::Database)?
        .filter_map(|r| r.ok())
        .collect();

    for (key, value) in &rows {
        app_conn
            .execute(
                "INSERT INTO meta (key, value) VALUES (?1, ?2)",
                params![key, value],
            )
            .map_err(PhotoMetaError::Database)?;
    }

    // Final indexes on the app DB
    app_conn
        .execute_batch(
            "
        CREATE INDEX idx_places_lat_lon     ON places (lat, lon);
        CREATE INDEX idx_places_importance  ON places (importance DESC);
        CREATE INDEX idx_lat_lon_importance ON places (lat, lon, importance DESC);
        PRAGMA journal_mode = DELETE;
        VACUUM;
    ",
        )
        .map_err(PhotoMetaError::Database)?;

    let places_exported: i64 = app_conn
        .query_row("SELECT COUNT(*) FROM places", [], |r| r.get(0))
        .map_err(PhotoMetaError::Database)?;

    eprintln!(
        "Export: {} places written to {}",
        places_exported, app_db_path
    );

    Ok(ExportResult {
        places_exported: places_exported as u64,
        output_path: app_db_path.to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;
    use tempfile::tempdir;

    // Temporary build database for testing
    fn make_build_db(path: &str) {
        let conn = Connection::open(path).unwrap();
        conn.execute_batch(
            "CREATE TABLE places (
                  geonames_id INTEGER PRIMARY KEY,
                  name        TEXT    NOT NULL,
                  country     TEXT    NOT NULL,
                  admin       TEXT,
                  lat         REAL    NOT NULL,
                  lon         REAL    NOT NULL,
                  kind        TEXT    NOT NULL,
                  importance  REAL
               );
               CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
               INSERT INTO meta VALUES ('version', '1');",
        )
        .unwrap();
    }

    #[test]
    fn export_empty_build_db_produces_empty_app_db() {
        let dir = tempdir().unwrap();
        let build = dir.path().join("build.db").to_str().unwrap().to_string();
        let app = dir.path().join("app.db").to_str().unwrap().to_string();
        make_build_db(&build);

        let result = run(&build, &app, 50).unwrap();
        assert_eq!(result.places_exported, 0);
        assert_eq!(result.output_path, app);
    }

    #[test]
    fn export_respects_regional_cap() {
        let dir = tempdir().unwrap();
        let build = dir.path().join("build.db").to_str().unwrap().to_string();
        let app = dir.path().join("app.db").to_str().unwrap().to_string();
        make_build_db(&build);

        let conn = Connection::open(&build).unwrap();
        // Insert 5 places in the same country/admin with varying importance
        for i in 1..=5i64 {
            conn.execute(
                "INSERT INTO places (geonames_id, name, country, admin, lat, lon, kind, importance)
                   VALUES (?1, ?2, 'US', 'CA', 0.0, 0.0, 'city', ?3)",
                params![i, format!("Place{i}"), i as f64],
            )
            .unwrap();
        }
        drop(conn);

        let result = run(&build, &app, 3).unwrap();
        // Cap = 3 per country+admin region
        assert_eq!(result.places_exported, 3);
    }

    #[test]
    fn export_excludes_null_importance() {
        let dir = tempdir().unwrap();
        let build = dir.path().join("build.db").to_str().unwrap().to_string();
        let app = dir.path().join("app.db").to_str().unwrap().to_string();
        make_build_db(&build);

        let conn = Connection::open(&build).unwrap();
        conn.execute(
            "INSERT INTO places (geonames_id, name, country, admin, lat, lon, kind, importance)
               VALUES (1, 'Scored', 'US', NULL, 0.0, 0.0, 'city', 0.5)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO places (geonames_id, name, country, admin, lat, lon, kind, importance)
               VALUES (2, 'Unscored', 'US', NULL, 1.0, 1.0, 'city', NULL)",
            [],
        )
        .unwrap();
        drop(conn);

        let result = run(&build, &app, 100).unwrap();
        assert_eq!(result.places_exported, 1);
    }

    #[test]
    fn export_copies_meta_table() {
        let dir = tempdir().unwrap();
        let build = dir.path().join("build.db").to_str().unwrap().to_string();
        let app = dir.path().join("app.db").to_str().unwrap().to_string();
        make_build_db(&build);

        run(&build, &app, 50).unwrap();

        let app_conn = Connection::open(&app).unwrap();
        let version: String = app_conn
            .query_row("SELECT value FROM meta WHERE key = 'version'", [], |r| {
                r.get(0)
            })
            .unwrap();
        assert_eq!(version, "1");
    }
}
