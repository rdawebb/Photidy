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

fn get_major_minor(version: &str) -> &str {
    let parts: Vec<&str> = version.split('.').collect();
    if parts.len() >= 2 {
        let major_minor = format!("{}.{}", parts[0], parts[1]);
        if version.starts_with(&major_minor) {
            &version[..major_minor.len()]
        } else {
            version
        }
    } else {
        version
    }
}

pub fn assert_compatible(conn: &Connection) -> Result<(), PhotoMetaError> {
    let db = read_db_version(conn)?;
    let crate_ver = crate_version();

    let db_major_minor = get_major_minor(&db);
    let crate_major_minor = get_major_minor(crate_ver);

    if db_major_minor != crate_major_minor {
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
    fn test_get_major_minor() {
        assert_eq!(get_major_minor("0.1.0"), "0.1");
        assert_eq!(get_major_minor("0.1"), "0.1");
        assert_eq!(get_major_minor("1.2.3"), "1.2");
        assert_eq!(get_major_minor("10.20"), "10.20");
    }

    #[test]
    fn test_assert_compatible_matching_versions() {
        let current_version = crate_version();
        let conn = setup_test_db_with_version(current_version);
        let result = assert_compatible(&conn);
        assert!(result.is_ok());
    }

    #[test]
    fn test_assert_compatible_different_patch_versions() {
        // Database with 0.1 should be compatible with crate 0.1.0
        let conn = setup_test_db_with_version("0.1");
        let result = assert_compatible(&conn);
        assert!(result.is_ok(), "Major.minor match should be compatible");
    }

    #[test]
    fn test_assert_compatible_patch_difference() {
        // Database with 0.1.0 should be compatible with crate 0.1.1
        let conn = setup_test_db_with_version("0.1.0");
        // We'll simulate this by checking the logic works
        assert_eq!(get_major_minor("0.1.0"), get_major_minor("0.1.1"));
    }

    #[test]
    fn test_assert_compatible_mismatched_minor_versions() {
        let conn = setup_test_db_with_version("0.0.1");
        let result = assert_compatible(&conn);
        assert!(result.is_err(), "Different minor versions should be incompatible");
    }

    #[test]
    fn test_assert_compatible_mismatched_major_versions() {
        let conn = setup_test_db_with_version("1.0.0");
        let result = assert_compatible(&conn);
        assert!(result.is_err(), "Different major versions should be incompatible");
    }

    #[test]
    fn test_assert_compatible_missing_version() {
        let conn = Connection::open_in_memory()
            .expect("Failed to create in-memory DB");
        let result = assert_compatible(&conn);
        assert!(result.is_err());
    }
}