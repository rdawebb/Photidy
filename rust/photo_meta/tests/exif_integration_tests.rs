use photo_meta::exif::extract_exif;

#[test]
fn test_extract_exif_from_image_without_exif() {
    let result = extract_exif("tests/fixtures/no_exif.jpg");
    assert!(result.timestamp.is_none());
    assert!(result.lat.is_none());
    assert!(result.lon.is_none());
}

#[test]
fn test_extract_exif_with_complete_data() {
    let result = extract_exif("tests/fixtures/complete_exif.jpg");
    assert!(result.timestamp.is_some());
    assert!(result.lat.is_some());
    assert!(result.lon.is_some());
    assert!(result.lat.unwrap() >= -90.0 && result.lat.unwrap() <= 90.0);
    assert!(result.lon.unwrap() >= -180.0 && result.lon.unwrap() <= 180.0);
}

#[test]
fn test_extract_exif_with_only_gps_no_date() {
    let result = extract_exif("tests/fixtures/only_gps.jpg");
    assert!(result.timestamp.is_none());
    assert!(result.lat.is_some());
    assert!(result.lon.is_some());
}

#[test]
fn test_extract_exif_with_only_date_no_gps() {
    let result = extract_exif("tests/fixtures/only_date.jpg");
    assert!(result.timestamp.is_some());
    assert!(result.lat.is_none());
    assert!(result.lon.is_none());
}
