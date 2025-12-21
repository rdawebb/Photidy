use pyo3::prelude::*;
use std::path::Path;

mod compat;
mod db;
mod errors;
pub mod exif;
mod geocode;
pub mod gps;
mod haversine;
pub mod models;
mod scoring;

use crate::errors::PhotoMetaError;
use crate::models::{ExtractedMetadata, Place};

#[pyfunction]
pub fn extract_metadata(path: &str) -> Result<ExtractedMetadata, PhotoMetaError> {
    exif::extract_exif(path)
}

#[pyfunction]
pub fn reverse_geocode(lat: f64, lon: f64, db_path: &str) -> Result<Option<Place>, PhotoMetaError> {
    let conn = db::open_db(Path::new(db_path))?;
    geocode::reverse_geocode(&conn, lat, lon)
}

#[pymodule]
fn photidy(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(reverse_geocode, m)?)?;
    Ok(())
}
