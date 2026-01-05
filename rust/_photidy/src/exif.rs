use std::fs::File;
use std::io::BufReader;
use exif::{Reader, Tag, In};
use chrono::{DateTime, NaiveDateTime};

use crate::errors::PhotoMetaError;
use crate::gps::extract_gps;
use crate::models::ExtractedMetadata;

pub fn parse_datetime(datetime_str: &str) -> Option<DateTime<chrono::Utc>> {
    NaiveDateTime::parse_from_str(datetime_str, "%Y-%m-%d %H:%M:%S")
        .ok()
        .or_else(|| {
            // Fall back to colon format for raw EXIF values
            NaiveDateTime::parse_from_str(datetime_str, "%Y:%m:%d %H:%M:%S").ok()
        })
        .map(|dt| DateTime::<chrono::Utc>::from_naive_utc_and_offset(dt, chrono::Utc))
}

pub fn extract_exif(path: &str) -> Result<ExtractedMetadata, PhotoMetaError> {
    let file = File::open(path).map_err(PhotoMetaError::Io)?;
    let mut bufreader = BufReader::new(file);
    let exif = match Reader::new().read_from_container(&mut bufreader) {
        Ok(exif) => exif,
        Err(_) => {
            // No EXIF data found, return empty metadata
            return Ok(ExtractedMetadata {
                timestamp: None,
                lat: None,
                lon: None,
            });
        }
    };

    let timestamp = exif.get_field(Tag::DateTimeOriginal, In::PRIMARY)
        .or_else(|| exif.get_field(Tag::DateTime, In::PRIMARY))
        .and_then(|f| parse_datetime(&f.display_value().to_string()))
        .map(|dt| dt.to_rfc3339());

    let (lat, lon) = extract_gps(&exif)
        .map(|(lat, lon)| (Some(lat), Some(lon)))
        .unwrap_or((None, None));

    Ok(ExtractedMetadata { timestamp, lat, lon })
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{Datelike, Timelike};

    #[test]
    fn test_parse_datetime_valid_format() {
        let result = parse_datetime("2024:06:15 14:30:45");
        assert!(result.is_some());
        let dt = result.unwrap();
        assert_eq!(dt.year(), 2024);
        assert_eq!(dt.month(), 6);
        assert_eq!(dt.day(), 15);
        assert_eq!(dt.hour(), 14);
        assert_eq!(dt.minute(), 30);
        assert_eq!(dt.second(), 45);
    }

    #[test]
    fn test_parse_datetime_invalid_format() {
        let result = parse_datetime("15-06-2024 14:30:45");
        assert!(result.is_none());
    }

    #[test]
    fn test_parse_datetime_invalid_date() {
        let result = parse_datetime("2024:13:32 25:61:61");
        assert!(result.is_none());
    }

    #[test]
    fn test_parse_datetime_returns_utc() {
        let result = parse_datetime("2024:06:15 14:30:45");
        assert!(result.is_some());
        let dt = result.unwrap();
        assert_eq!(dt.timezone(), chrono::Utc);
    }

    #[test]
    fn test_parse_datetime_leap_year() {
        let result = parse_datetime("2024:02:29 12:00:00");
        assert!(result.is_some()); // 2024 is a leap year
    }

    #[test]
    fn test_parse_datetime_invalid_leap_day() {
        let result = parse_datetime("2023:02:29 12:00:00");
        assert!(result.is_none()); // 2023 is not a leap year
    }

    #[test]
    fn test_parse_datetime_midnight() {
        let result = parse_datetime("2024:06:15 00:00:00");
        assert!(result.is_some());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 0);
        assert_eq!(dt.minute(), 0);
        assert_eq!(dt.second(), 0);
    }

    #[test]
    fn test_parse_datetime_end_of_day() {
        let result = parse_datetime("2024:06:15 23:59:59");
        assert!(result.is_some());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 23);
        assert_eq!(dt.minute(), 59);
        assert_eq!(dt.second(), 59);
    }

    #[test]
    fn test_extract_exif_from_nonexistent_file() {
        let result = extract_exif("/nonexistent/path/file.jpg");
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_exif_from_invalid_image_file() {
        let fixture_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/not_an_image.txt");
        let result = extract_exif(fixture_path);
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_exif_from_image_without_exif() {
        let fixture_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/no_exif.jpg");
        let result = extract_exif(fixture_path).unwrap();
        assert!(result.timestamp.is_none());
        assert!(result.lat.is_none());
        assert!(result.lon.is_none());
    }

    #[test]
    fn test_extract_exif_with_complete_data() {
        let fixture_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/complete_exif.jpg");
        let result = extract_exif(fixture_path).unwrap();
        assert!(result.timestamp.is_some());
        assert!(result.lat.is_some());
        assert!(result.lon.is_some());
        assert!(result.lat.unwrap() >= -90.0 && result.lat.unwrap() <= 90.0);
        assert!(result.lon.unwrap() >= -180.0 && result.lon.unwrap() <= 180.0);
    }

    #[test]
    fn test_extract_exif_with_only_gps_no_date() {
        let fixture_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/only_gps.jpg");
        let result = extract_exif(fixture_path).unwrap();
        assert!(result.timestamp.is_none());
        assert!(result.lat.is_some());
        assert!(result.lon.is_some());
    }

    #[test]
    fn test_extract_exif_with_only_date_no_gps() {
        let fixture_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/only_date.jpg");
        let result = extract_exif(fixture_path).unwrap();
        assert!(result.timestamp.is_some());
        assert!(result.lat.is_none());
        assert!(result.lon.is_none());
    }
}
