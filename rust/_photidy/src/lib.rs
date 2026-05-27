use pyo3::prelude::*;
use std::path::Path;

mod compat;
mod db;
mod errors;
pub mod exif;
pub mod geo_scoring;
mod geocode;
pub mod gps;
mod haversine;
pub mod models;

use crate::errors::PhotoMetaError;
use crate::models::{ExtractedMetadata, Place};

#[cfg(feature = "build-db")]
pub mod build;

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
fn _photidy(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(reverse_geocode, m)?)?;

    #[cfg(feature = "build-db")]
    {
        m.add_function(wrap_pyfunction!(build::build_wikidata_enrichment, m)?)?;
        m.add_function(wrap_pyfunction!(build::build_pageview_month, m)?)?;
        m.add_function(wrap_pyfunction!(build::build_compute_scores, m)?)?;
        m.add_function(wrap_pyfunction!(build::build_export_app_db, m)?)?;
    }

    Ok(())
}
