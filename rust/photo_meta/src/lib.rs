use pyo3::prelude::*;
use once_cell::sync::Lazy;
use std::sync::Mutex;
use rusqlite::Connection;

mod exif;
mod geocode;
mod haversine;
mod models;

// Wrap Connection in Mutex for thread-safe access
static DB: Lazy<Mutex<Connection>> = Lazy::new(|| {
    let conn = Connection::open("places.db").expect("Failed to open DB");
    Mutex::new(conn)
});

#[pyfunction]
fn extract_metadata(path: &str) -> PyResult<Py<pyo3::types::PyDict>> {
    let exif_data = exif::extract_exif(path);

    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);

        if let Some(timestamp) = exif_data.timestamp {
            dict.set_item("date_taken", timestamp.to_rfc3339())?;
        } else {
            dict.set_item("date_taken", py.None())?;
        }

        if let (Some(lat), Some(lon)) = (exif_data.lat, exif_data.lon) {
            dict.set_item("lat", lat)?;
            dict.set_item("lon", lon)?;

            let db = DB.lock().unwrap();
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

#[pymodule]
fn photo_meta(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_metadata, m)?)?;
    Ok(())
}
