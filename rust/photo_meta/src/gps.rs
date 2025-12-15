use exif::{Exif, Tag, In};

pub fn extract_gps(exif: &Exif) -> Option<(f64, f64)> {
    let lat = extract_coord(exif, Tag::GPSLatitude, Tag::GPSLatitudeRef)?;
    let lon = extract_coord(exif, Tag::GPSLongitude, Tag::GPSLongitudeRef)?;
    
    if !(-90.0..=90.0).contains(&lat) || !(-180.0..=180.0).contains(&lon) {
        return None;
    }

    Some((lat, lon))
}

fn extract_coord(exif: &Exif, tag: Tag, ref_tag: Tag) -> Option<f64> {
    let field = exif.get_field(tag, In::PRIMARY)?;
    let values = match &field.value {
        exif::Value::Rational(values) => values.as_slice(),
        _ => return None,
    };
    let mut coord = dms_to_decimal(values)?;

    if let Some(ref_field) = exif.get_field(ref_tag, In::PRIMARY) {
        let ref_str = ref_field.display_value().to_string().trim().to_uppercase();
        if ref_str == "S" || ref_str == "W" {
            coord = -coord;
        }
    }

    Some(coord)
}

fn dms_to_decimal(values: &[exif::Rational]) -> Option<f64> {
    match values.len() {
        3 => {
            let degrees = rational(values[0])?;
            let minutes = rational(values[1])?;
            let seconds = rational(values[2])?;

            if !(0.0..=90.0).contains(&degrees) || !(0.0..60.0).contains(&minutes) || !(0.0..60.0).contains(&seconds) {
                return None;
            }

            Some(degrees + (minutes / 60.0) + (seconds / 3600.0))
        }
        1 => rational(values[0]),
        _ => None,
    }
}

fn rational(r: exif::Rational) -> Option<f64> {
    if r.denom == 0 {
        None
    } else {
        Some(r.num as f64 / r.denom as f64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rational_valid() {
        let r = exif::Rational { num: 1, denom: 2 };
        assert_eq!(rational(r), Some(0.5));
    }

    #[test]
    fn test_rational_zero_denom() {
        let r = exif::Rational { num: 1, denom: 0 };
        assert_eq!(rational(r), None);
    }

    #[test]
    fn test_dms_to_decimal_three_values() {
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 26, denom: 1 },
            exif::Rational { num: 46, denom: 1 },
        ];
        let result = dms_to_decimal(&values);
        assert!(result.is_some());
        let coord = result.unwrap();
        assert!((coord - 40.4461111).abs() < 0.0001);
    }

    #[test]
    fn test_dms_to_decimal_single_value() {
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
        ];
        let result = dms_to_decimal(&values);
        assert_eq!(result, Some(40.0));
    }

    #[test]
    fn test_dms_to_decimal_invalid_degrees() {
        let values = vec![
            exif::Rational { num: 91, denom: 1 },
            exif::Rational { num: 0, denom: 1 },
            exif::Rational { num: 0, denom: 1 },
        ];
        assert_eq!(dms_to_decimal(&values), None);
    }

    #[test]
    fn test_dms_to_decimal_invalid_minutes() {
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 61, denom: 1 },
            exif::Rational { num: 0, denom: 1 },
        ];
        assert_eq!(dms_to_decimal(&values), None);
    }

    #[test]
    fn test_dms_to_decimal_invalid_seconds() {
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 30, denom: 1 },
            exif::Rational { num: 61, denom: 1 },
        ];
        assert_eq!(dms_to_decimal(&values), None);
    }

    #[test]
    fn test_dms_to_decimal_wrong_length() {
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 26, denom: 1 },
        ];
        assert_eq!(dms_to_decimal(&values), None);
    }

    #[test]
    fn test_dms_to_decimal_zero_values() {
        let values = vec![
            exif::Rational { num: 0, denom: 1 },
            exif::Rational { num: 0, denom: 1 },
            exif::Rational { num: 0, denom: 1 },
        ];
        let result = dms_to_decimal(&values);
        assert_eq!(result, Some(0.0));
    }

    #[test]
    fn test_dms_to_decimal_maximum_valid_values() {
        // Checking values at usual precision limits (7 decimal places)
        let values = vec![
            exif::Rational { num: 90, denom: 1 },
            exif::Rational { num: 599999999, denom: 10000000 },
            exif::Rational { num: 599999999, denom: 10000000 },
        ];
        let result = dms_to_decimal(&values);
        assert!(result.is_some());
        let coord = result.unwrap();
        assert!((coord - 91.01666666497167).abs() < 0.0001);
    }

    #[test]
    fn test_dms_to_decimal_fractional_seconds() {
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 26, denom: 1 },
            exif::Rational { num: 465, denom: 10 }, // 46.5 seconds
        ];
        let result = dms_to_decimal(&values);
        assert!(result.is_some());
        let coord = result.unwrap();
        assert!((coord - 40.44625).abs() < 0.0001);
    }

    #[test]
    fn test_rational_large_values() {
        let r = exif::Rational { num: 1000000, denom: 1000000 };
        assert_eq!(rational(r), Some(1.0));
    }

    #[test]
    fn test_dms_to_decimal_empty_values() {
        let values = vec![];
        assert_eq!(dms_to_decimal(&values), None);
    }

    #[test]
    fn test_dms_to_decimal_four_values() {
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 26, denom: 1 },
            exif::Rational { num: 46, denom: 1 },
            exif::Rational { num: 0, denom: 1 },
        ];
        assert_eq!(dms_to_decimal(&values), None);
    }

    #[test]
    fn test_dms_to_decimal_minutes_boundary_59() {
        // Checking minutes at usual precision (7 decimal places)
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 599999999, denom: 10000000 },
            exif::Rational { num: 0, denom: 1 },
        ];
        let result = dms_to_decimal(&values);
        assert!(result.is_some());
        let coord = result.unwrap();
        assert!((coord - 41.0).abs() < 0.0001);
    }

    #[test]
    fn test_dms_to_decimal_seconds_boundary_59() {
        // Checking seconds at usual precision (7 decimal places)
        let values = vec![
            exif::Rational { num: 40, denom: 1 },
            exif::Rational { num: 30, denom: 1 },
            exif::Rational { num: 599999999, denom: 10000000 },
        ];
        let result = dms_to_decimal(&values);
        assert!(result.is_some());
        let coord = result.unwrap();
        assert!((coord - 40.51667).abs() < 0.0001);
    }
}