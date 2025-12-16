use pyo3::prelude::*;
use crate::db::{get_db};

mod compat;
mod db;
pub mod exif;
pub mod gps;
mod geocode;
mod haversine;
pub mod models;

#[pyfunction]
fn extract_metadata(path: &str, db_path: &str) -> PyResult<Py<pyo3::types::PyDict>> {
    let exif_data = exif::extract_exif(path);

    Python::attach(|py| {
        let dict = pyo3::types::PyDict::new(py);

        if let Some(timestamp) = exif_data.timestamp {
            dict.set_item("date_taken", timestamp.to_rfc3339())?;
        } else {
            dict.set_item("date_taken", py.None())?;
        }

        if let Some(lat) = exif_data.lat {
            dict.set_item("lat", lat)?;
        } else {
            dict.set_item("lat", py.None())?;
        }

        if let Some(lon) = exif_data.lon {
            dict.set_item("lon", lon)?;
        } else {
            dict.set_item("lon", py.None())?;
        }

        if let (Some(lat), Some(lon)) = (exif_data.lat, exif_data.lon) {
            let db = get_db(std::path::Path::new(db_path))
                .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to open database"))?;
            let location_string = geocode::reverse_geocode(&db, lat, lon)
                .map(|place| {
                    match place.admin {
                        Some(admin) => format!("{}, {}, {}", place.name, admin, place.country),
                        None => format!("{}, {}", place.name, place.country),
                    }
                })
                .unwrap_or_else(|| "Unknown location".to_string());
            
            dict.set_item("location", location_string)?;
        } else {
            dict.set_item("location", "Unknown location")?;
        }

        Ok(dict.into())
    })
}

#[pyfunction]
fn db_filename() -> &'static str {
    crate::db::db_filename()
}

#[pyfunction]
fn validate_db(path: &str) -> PyResult<()> {
    crate::db::validate_db(std::path::Path::new(path))
        .map_err(|e| match e {
            crate::db::DbError::Open(err) => 
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open database: {}", err)),
            crate::db::DbError::Incompatible(err) => 
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Database incompatible: {}", err)),
        })
}

#[pymodule]
fn photo_meta(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(db_filename, m)?)?;
    m.add_function(wrap_pyfunction!(validate_db, m)?)?;
    Ok(())
}
