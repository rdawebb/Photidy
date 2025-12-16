use rusqlite::Connection;

#[derive(Debug, PartialEq)]
pub struct Version {
    pub major: u32,
    pub minor: u32,
}

impl Version {
    pub fn parse(s: &str) -> Option<Self> {
        let mut parts = s.split('.');
        Some(Self {
            major: parts.next()?.parse().ok()?,
            minor: parts.next()?.parse().ok()?,
        })
    } 
}

pub fn crate_version() -> Version {
    Version::parse(env!("CARGO_PKG_VERSION"))
        .expect("Invalid crate version")
}

pub fn read_db_version(conn: &Connection) -> rusqlite::Result<Version> {
    let raw: String = conn.query_row(
        "SELECT value FROM metadata WHERE key = 'db_version'",
        [],
        |row| row.get(0),
    )?;

    Version::parse(&raw)
        .ok_or_else(|| rusqlite::Error::InvalidQuery)
}

pub fn assert_compatible(conn: &Connection) -> rusqlite::Result<(), String> {
    let db = read_db_version(conn)
        .map_err(|_| "Missing or invalid database version")?;

    let crate_ver = crate_version();

    if db != crate_ver {
        Err(format!(
            "Incompatible DB version {}.{} for crate {}.{}",
            db.major, db.minor, crate_ver.major, crate_ver.minor
        ))
    } else {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version_parse() {
        let v = Version::parse("1.2").unwrap();
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 2);

        assert!(Version::parse("1").is_none());
        assert!(Version::parse("a.b").is_none());
    }
}