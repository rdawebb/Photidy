pub fn haversine(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let r = 6371.0_f64; // km
    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();

    let a = (dlat / 2.0).sin().powi(2)
        + lat1.to_radians().cos()
        * lat2.to_radians().cos()
        * (dlon / 2.0).sin().powi(2);

    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
    r * c
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_same_location_distance_is_zero() {
        let distance = haversine(40.7128, -74.0060, 40.7128, -74.0060);
        assert!((distance - 0.0) < 0.001); // Within 1 meter
    }

    #[test]
    fn test_known_distance_london_to_paris() {
        let distance = haversine(51.5074, -0.1278, 48.8566, 2.3522);
        assert!((distance - 343.0).abs() < 10.0); // Within 10 km
    }

    #[test]
    fn test_distance_is_symmetric() {
        let distance1 = haversine(40.7128, -74.0060, 34.0522, -118.2437);
        let distance2 = haversine(34.0522, -118.2437, 40.7128, -74.0060);
        assert!((distance1 - distance2).abs() < 0.01); // Within 10 meters
    }

    #[test]
    fn test_north_pole() {
        let distance = haversine(90.0, 0.0, 89.0, 0.0);
        assert!(distance > 0.0);
        assert!(distance < 200.0); // Should be approx 111 km
    }

    #[test]
    fn test_south_pole() {
        let distance = haversine(-90.0, 0.0, -89.0, 0.0);
        assert!(distance > 0.0);
        assert!(distance < 200.0); // Should be approx 111 km
    }

    #[test]
    fn test_equator_distance() {
        // One degree of longitude at the equator is approx 111km
        let distance = haversine(0.0, 0.0, 0.0, 1.0);
        assert!((distance - 111.3).abs() < 2.0); 
    }

    #[test]
    fn test_antimeridian_crossing() {
        let distance = haversine(0.0, 179.9, 0.0, -179.9);
        assert!(distance < 23.0); // Should be approx 22 km
    }
}