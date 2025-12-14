use rusqlite::{Connection, params};
use crate::{models::Place, haversine::haversine};

pub fn reverse_geocode(
    conn: &Connection,
    lat: f64,
    lon: f64,
) -> Option<Place> {

    let delta = 0.5; // degrees
    let mut stmt = conn.prepare(
        "SELECT name, country, admin, lat, lon, kind, importance
         FROM places
         WHERE lat BETWEEN ? AND ?
           AND lon BETWEEN ? AND ?"
    ).ok()?;

    let rows = stmt.query_map(
        params![lat - delta, lat + delta, lon - delta, lon + delta],
        |row| {
            Ok(Place {
                name: row.get(0)?,
                country: row.get(1)?,
                admin: row.get(2)?,
                lat: row.get(3)?,
                lon: row.get(4)?,
                kind: row.get(5)?,
                importance: row.get(6)?,
            })
        }
    ).ok()?;

    rows.filter_map(Result::ok)
        .min_by(|a, b| {
            let da = haversine(lat, lon, a.lat, a.lon);
            let db = haversine(lat, lon, b.lat, b.lon);
            da.partial_cmp(&db).unwrap()
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::{Connection, params};
    
    fn setup_test_db() -> Connection {
        let conn = Connection::open_in_memory().expect("Failed to open test DB");
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
            params!["Camden", "UK", Some("London"), 51.5416, -0.1425, "borough", 0.8],
        ).expect("Failed to insert test data");

        conn
    }

    #[test]
    fn test_reverse_geocode_finds_closest_location() {
        let conn = setup_test_db();
        // Test coordinates near London
        let result = reverse_geocode(&conn, 51.5074, -0.1278);
        assert!(result.is_some());
        let place = result.unwrap();
        assert_eq!(place.name, "London");
    }

    #[test]
    fn test_reverse_geocode_finds_nearest_not_first() {
        let conn = setup_test_db();
        // Test coordinates closer to Richmond than London
        let result = reverse_geocode(&conn, 51.4500, -0.2800);
        assert!(result.is_some());
        let place = result.unwrap();
        assert_eq!(place.name, "Richmond");
    }

    #[test]
    fn test_reverse_geocode_no_locations_found() {
        let conn = setup_test_db();
        // Test coordinates with no nearby locations
        let result = reverse_geocode(&conn, 0.0, 0.0);
        assert!(result.is_none());
    }

    #[test]
    fn test_reverse_geocode_includes_admin_in_place_struct() {
        let conn = setup_test_db();
        let result = reverse_geocode(&conn, 51.5416, -0.1425);
        assert!(result.is_some());
        let place = result.unwrap();
        assert!(place.admin.is_some());
        assert_eq!(place.admin.unwrap(), "London");
    }

    #[test]
    fn test_reverse_geocode_at_boundary_of_search_radius() {
        let conn = setup_test_db();
        // Coordinates exactly 0.5 degrees from London
        let result = reverse_geocode(&conn, 52.0074, -0.1278);
        assert!(result.is_some());
    }

    #[test]
    fn test_reverse_geocode_just_outside_search_radius() {
        let conn = setup_test_db();
        // Coordinates just outside 0.5 degrees from London
        let result = reverse_geocode(&conn, 52.0516, -0.1425);
        assert!(result.is_none());
    }

    #[test]
    fn test_reverse_geocode_empty_database() {
        let conn = Connection::open_in_memory().expect("Failed to open test DB");
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

        let result = reverse_geocode(&conn, 51.5074, -0.1278);
        assert!(result.is_none());
    }

    #[test]
    fn test_reverse_geocode_returns_all_fields() {
        let conn = setup_test_db();
        let result = reverse_geocode(&conn, 51.5074, -0.1278);
        assert!(result.is_some());
        let place = result.unwrap();
        assert!(!place.name.is_empty());
        assert!(!place.country.is_empty());
        assert!(!place.kind.is_empty());
        assert!(place.lat > 0.0);
        assert!(place.lon < 0.0);
        assert!(place.importance >= 0.0);
    }
}