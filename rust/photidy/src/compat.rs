use rusqlite::Connection;
use crate::errors::PhotoMetaError;

const DB_VERSION_KEY: &str = "db_version";

pub fn crate_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

pub fn read_db_version(conn: &Connection) -> Result<String, PhotoMetaError> {
    let version: String = conn.query_row(
        "SELECT value FROM meta WHERE key = ?1",
        [DB_VERSION_KEY],
        |row| row.get(0),
    ).map_err(PhotoMetaError::Database)?;

    Ok(version)
}

pub fn assert_compatible(conn: &Connection) -> Result<(), PhotoMetaError> {
    let db = read_db_version(conn)?;
    let crate_ver = crate_version();

    if db != crate_ver {
        return Err(PhotoMetaError::Incompatible {
            db_version: db,
            crate_version: crate_ver.to_string(),
        });
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    fn setup_test_db_with_version(version: &str) -> Connection {
        let conn = Connection::open_in_memory()
            .expect("Failed to create in-memory DB");
        
        conn.execute_batch(
            "CREATE TABLE meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )"
        ).expect("Failed to create meta table");

        conn.execute(
            "INSERT INTO meta VALUES (?, ?)",
            rusqlite::params!["db_version", version],
        ).expect("Failed to insert version");

        conn
    }

    #[test]
    fn test_crate_version_returns_static_str() {
        let version = crate_version();
        assert!(!version.is_empty());

        // Should be a valid semantic version
        assert!(version.contains('.'));
    }

    #[test]
    fn test_read_db_version_success() {
        let conn = setup_test_db_with_version("1.0.0");
        let result = read_db_version(&conn);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "1.0.0");
    }

    #[test]
    fn test_read_db_version_missing_table() {
        let conn = Connection::open_in_memory()
            .expect("Failed to create in-memory DB");
        let result = read_db_version(&conn);
        assert!(result.is_err());
    }

    #[test]
    fn test_assert_compatible_matching_versions() {
        let current_version = crate_version();
        let conn = setup_test_db_with_version(current_version);
        let result = assert_compatible(&conn);
        assert!(result.is_ok());
    }

    #[test]
    fn test_assert_compatible_mismatched_versions() {
        let conn = setup_test_db_with_version("0.0.1");
        let result = assert_compatible(&conn);
        assert!(result.is_err());
    }

    #[test]
    fn test_assert_compatible_missing_version() {
        let conn = Connection::open_in_memory()
            .expect("Failed to create in-memory DB");
        let result = assert_compatible(&conn);
        assert!(result.is_err());
    }
}