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
