use rusqlite::Connection;

use crate::db;
use crate::errors::PhotoMetaError;
use crate::geo_scoring;
use crate::models::Place;

pub fn reverse_geocode(
    conn: &Connection,
    lat: f64,
    lon: f64,
) -> Result<Option<Place>, PhotoMetaError> {
    let candidates = db::fetch_candidates(conn, lat, lon)?;
    Ok(geo_scoring::select_best(candidates, lat, lon))
}
