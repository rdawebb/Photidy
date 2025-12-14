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

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::PyDict;

    // ============ Unit tests (no fixtures) ============

    // Unit test: dict structure with data
    #[test]
    fn test_extract_metadata_returns_dict_with_required_keys() {
        Python::with_gil(|py| {
            let result = extract_metadata("tests/fixtures/complete_exif.jpg").unwrap();
            let dict: &PyDict = result.as_ref(py).downcast().unwrap();

            assert!(dict.contains("date_taken").unwrap());
            assert!(dict.contains("lat").unwrap());
            assert!(dict.contains("lon").unwrap());
            assert!(dict.contains("location").unwrap());
        });
    }

    // Unit test: graceful handling of missing files
    #[test]
    fn test_extract_metadata_gracefully_handles_missing_file() {
        let result = extract_metadata("nonexistent/path/file.jpg");
        assert!(result.is_ok());
        Python::with_gil(|py| {
            let dict: &PyDict = result.unwrap().as_ref(py).downcast().unwrap();
            assert!(dict.get_item("date_taken").is_none());
            assert!(dict.get_item("lat").is_none());
            assert!(dict.get_item("lon").is_none());
            let location: &str = dict.get_item("location").unwrap().extract().unwrap();
            assert_eq!(location, "Unknown location");
        });
    }

    // Unit test: Python type conversion
    #[test]
    fn test_extract_metadata_dict_values_have_correct_python_types() {
        Python::with_gil(|py| {
            let result = extract_metadata("tests/fixtures/complete_exif.jpg").unwrap();
            let dict: &PyDict = result.as_ref(py).downcast().unwrap();

            // date_taken should be a string
            let date_taken = dict.get_item("date_taken").unwrap();
            assert!(date_taken.is_instance_of::<pyo3::types::PyString>().unwrap());

            // lat/lon should be floats
            let lat = dict.get_item("lat").unwrap();
            assert!(lat.extract::<f64>().is_ok());
            let lon = dict.get_item("lon").unwrap();
            assert!(lon.extract::<f64>().is_ok());

            // location should be a string
            let location = dict.get_item("location").unwrap();
            assert!(location.is_instance_of::<pyo3::types::PyString>().unwrap());
        });
    }

    // Unit test: location formatting with/without admin
    #[test]
    fn test_extract_metadata_location_format_structure() {
        Python::with_gil(|py| {
            let result = extract_metadata("tests/fixtures/complete_exif.jpg").unwrap();
            let dict: &PyDict = result.as_ref(py).downcast().unwrap();

            let location: &str = dict.get_item("location").unwrap().extract().unwrap();
            let parts: Vec<&str> = location.split(',').map(|s| s.trim()).collect();
            
            // Location should be either "name, country" or "name, admin, country"
            assert!(parts.len() == 2 || parts.len() == 3);
            for part in parts {
                assert!(!part.is_empty());
            }
        });
    }

    // Unit test: missing data handling
    #[test]
    fn test_extract_metadata_handles_missing_location() {
        Python::with_gil(|py| {
            let result = extract_metadata("tests/fixtures/no_exif.jpg").unwrap();
            let dict: &PyDict = result.as_ref(py).downcast().unwrap();

            let location: &str = dict.get_item("location").unwrap().extract().unwrap();
            assert_eq!(location, "Unknown location");
        });
    }

    // Unit test: module export
    #[test]
    fn test_pymodule_exports_extract_metadata_function() {
        Python::with_gil(|py| {
            let module = PyModule::new(py, "photo_meta").unwrap();
            photo_meta(module).unwrap();

            let func = module.getattr("extract_metadata").unwrap();
            assert!(func.is_callable());
        });
    }
}