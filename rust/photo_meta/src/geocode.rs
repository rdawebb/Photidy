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
