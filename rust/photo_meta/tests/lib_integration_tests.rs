use photo_meta::extract_metadata;
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[test]
fn test_extract_metadata_integration_with_complete_exif() {
    Python::with_gil(|py| {
        let result = extract_metadata("tests/fixtures/complete_exif.jpg").unwrap();
        let dict: &PyDict = result.as_ref(py).downcast().unwrap();

        // Verify all required keys exist
        assert!(dict.contains("date_taken").unwrap());
        assert!(dict.contains("lat").unwrap());
        assert!(dict.contains("lon").unwrap());
        assert!(dict.contains("location").unwrap());

        // Verify date_taken is valid RFC3339
        let date_taken = dict.get_item("date_taken").unwrap();
        assert!(!date_taken.is_none());
        let date_str: &str = date_taken.extract().unwrap();
        assert!(date_str.parse::<chrono::DateTime<chrono::Utc>>().is_ok());

        // Verify lat/lon are valid floats in correct range
        let lat: f64 = dict.get_item("lat").unwrap().extract().unwrap();
        assert!(lat.is_finite());
        assert!(lat >= -90.0 && lat <= 90.0);
        
        let lon: f64 = dict.get_item("lon").unwrap().extract().unwrap();
        assert!(lon.is_finite());
        assert!(lon >= -180.0 && lon <= 180.0);

        // Verify location has proper structure (2 or 3 parts)
        let location: &str = dict.get_item("location").unwrap().extract().unwrap();
        let parts: Vec<&str> = location.split(',').map(|s| s.trim()).collect();
        assert!(parts.len() == 2 || parts.len() == 3);
        assert!(!parts[0].is_empty()); // Place name
        assert!(!parts[parts.len() - 1].is_empty()); // Country
    });
}

#[test]
fn test_extract_metadata_integration_no_exif() {
    Python::with_gil(|py| {
        let result = extract_metadata("tests/fixtures/no_exif.jpg").unwrap();
        let dict: &PyDict = result.as_ref(py).downcast().unwrap();

        assert!(dict.get_item("date_taken").is_none());
        assert!(dict.get_item("lat").is_none());
        assert!(dict.get_item("lon").is_none());
        
        let location: &str = dict.get_item("location").unwrap().extract().unwrap();
        assert_eq!(location, "Unknown location");
    });
}
