use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use rusqlite::Connection;
use crate::compat;

static DB_CONN: OnceLock<Connection> = OnceLock::new();

pub enum DbError {
    Open(rusqlite::Error),
    Incompatible(String),
}

pub fn db_filename() -> &'static str {
    "places_v1.0.db"
}

pub fn validate_db(path: &Path) -> Result<(), DbError> {
    let conn = Connection::open(path)
        .map_err(DbError::Open)?;
    
    compat::assert_compatible(&conn)
        .map_err(DbError::Incompatible)?;
}

pub fn get_db(path: &Path) -> Result<&'static Connection, DbError> {
    DB_CONN.get_or_try_init(|| {
        let conn = Connection::open(path)
            .map_err(DbError::Open)?;

        compat::assert_compatible(&conn)
            .map_err(DbError::Incompatible)?;

        Ok(conn)
    })
}