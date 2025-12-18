use std::path::Path;
use crate::db;
use crate::models::Place;
use crate::scoring;

pub fn reverse_geocode(
    db_path: &Path,
    lat: f64,
    lon: f64,
) -> Option<Place> {
    let candidates = db::fetch_candidates(db_path, lat, lon).ok()?;
    scoring::select_best(candidates, lat, lon)
}
