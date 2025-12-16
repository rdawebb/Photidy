use std::path::Path;
use rusqlite::Connection;
use crate::compat;

pub enum DbError {
    Open(rusqlite::Error),
    Incompatible(String),
}

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