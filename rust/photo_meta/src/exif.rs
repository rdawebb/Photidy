use std::fs::File;
use std::io::BufReader;
use exif::{Reader, Tag, In};
use chrono::{DateTime, NaiveDateTime};

pub struct ExifData {
    pub timestamp: Option<DateTime<chrono::Utc>>,
    pub lat: Option<f64>,
    pub lon: Option<f64>,
}

pub fn parse_gps_coordinate(field: &exif::Field) -> Option<f64> {
    let mut rationals = Vec::new();

    match &field.value {
        exif::Value::Rational(values) => {
            if values.len() >= 3 {
                for i in 0..3 {
                    rationals.push(values[i]);
                }
            } else {
                return None;
            }
        }
        _ => return None,
    }

    if rationals.len() == 3 {
        Some(
            rationals[0].to_f64()
            + rationals[1].to_f64() / 60.0
            + rationals[2].to_f64() / 3600.0
        )
    } else {
        None
    }
}

pub fn parse_datetime(datetime_str: &str) -> Option<DateTime<chrono::Utc>> {
    NaiveDateTime::parse_from_str(datetime_str, "%Y:%m:%d %H:%M:%S")
        .ok()
        .map(|dt| DateTime::<chrono::Utc>::from_naive_utc_and_offset(dt, chrono::Utc))
}

pub fn extract_exif(path: &str) -> ExifData {
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return ExifData { timestamp: None, lat: None, lon: None },
    };

    let mut bufreader = BufReader::new(file);
    let exif = match Reader::new().read_from_container(&mut bufreader) {
        Ok(e) => e,
        Err(_) => return ExifData { timestamp: None, lat: None, lon: None },
    };

    let timestamp = exif.get_field(Tag::DateTimeOriginal, In::PRIMARY)
        .or_else(|| exif.get_field(Tag::DateTime, In::PRIMARY))
        .and_then(|f| parse_datetime(&f.display_value().to_string()));

    let mut lat = exif.get_field(Tag::GPSLatitude, In::PRIMARY)
        .and_then(parse_gps_coordinate);

    let mut lon = exif.get_field(Tag::GPSLongitude, In::PRIMARY)
        .and_then(parse_gps_coordinate);

    // Apply latitude reference (S = negative)
    if let Some(lat_val) = lat {
        if let Some(ref_field) = exif.get_field(Tag::GPSLatitudeRef, In::PRIMARY) {
            if ref_field.display_value().to_string().contains('S') {
                lat = Some(-lat_val);
            }
        } else {
            lat = Some(lat_val);
        }
    }

    // Apply longitude reference (W = negative)
    if let Some(lon_val) = lon {
        if let Some(ref_field) = exif.get_field(Tag::GPSLongitudeRef, In::PRIMARY) {
            if ref_field.display_value().to_string().contains('W') {
                lon = Some(-lon_val);
            }
        } else {
            lon = Some(lon_val);
        }
    }

    ExifData { timestamp, lat, lon }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ============ Unit tests for parse_datetime ============

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

    // ============ Unit tests for extract_exif error handling ============

    #[test]
    fn test_extract_exif_from_nonexistent_file() {
        let exif_data = extract_exif("/nonexistent/path/file.jpg");
        assert!(exif_data.timestamp.is_none());
        assert!(exif_data.lat.is_none());
        assert!(exif_data.lon.is_none());
    }

    #[test]
    fn test_extract_exif_from_invalid_image_file() {
        let result = extract_exif("tests/fixtures/not_an_image.txt");
        assert!(result.timestamp.is_none());
        assert!(result.lat.is_none());
        assert!(result.lon.is_none());
    }
}
