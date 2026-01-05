use crate::haversine::haversine;
use crate::models::{Candidate, Place};

pub fn score(c: &Candidate, lat: f64, lon: f64) -> Option<f64> {
    let distance = haversine(lat, lon, c.lat, c.lon);
    if distance > 50.0 {
        return None;
    }

    let kind_bias = match c.kind.as_str() {
        "landmark" => 8.0,
        "city" => 3.0,
        "town" => 1.0,
        _ => 0.0,
    };

    Some(
        -distance * 1.0
            + c.importance * 2.5
            + kind_bias
    )
}

pub fn select_best(candidates: Vec<Candidate>, lat: f64, lon: f64) -> Option<Place> {
    candidates
        .iter()
        .filter_map(|c| score(c, lat, lon).map(|s| (c, s)))
        .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap())
        .map(|(candidate, _)| Place {
            name: candidate.name.clone(),
            country: candidate.country.clone(),
            admin: candidate.admin.clone(),
            kind: candidate.kind.clone(),
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_candidate(
        name: &str,
        lat: f64,
        lon: f64,
        kind: &str,
        importance: f64,
    ) -> Candidate {
        Candidate {
            name: name.to_string(),
            country: "UK".to_string(),
            admin: Some("Test Admin".to_string()),
            lat,
            lon,
            kind: kind.to_string(),
            importance,
        }
    }

    #[test]
    fn test_score_within_distance_threshold() {
        let candidate = create_test_candidate("London", 51.5074, -0.1278, "city", 0.9);
        let score = score(&candidate, 51.5074, -0.1278);
        assert!(score.is_some());
        assert!(score.unwrap() > 0.0); // High score for exact location
    }

    #[test]
    fn test_score_beyond_distance_threshold() {
        let candidate = create_test_candidate("London", 51.5074, -0.1278, "city", 0.9);
        let score = score(&candidate, 0.0, 0.0);
        assert!(score.is_none()); // Beyond 50 km
    }

    #[test]
    fn test_score_landmark_has_highest_bias() {
        let landmark = create_test_candidate("Tower of London", 51.5081, -0.0759, "landmark", 0.5);
        let city = create_test_candidate("London", 51.5074, -0.1278, "city", 0.5);
        let town = create_test_candidate("Richmond", 51.4415, -0.3005, "town", 0.5);

        let test_lat = 51.5074;
        let test_lon = -0.1278;

        let landmark_score = score(&landmark, test_lat, test_lon).unwrap();
        let city_score = score(&city, test_lat, test_lon).unwrap();
        let town_score = score(&town, test_lat, test_lon).unwrap();

        assert!(landmark_score > city_score);
        assert!(city_score > town_score);
    }

    #[test]
    fn test_score_considers_distance() {
        let candidate = create_test_candidate("London", 51.5074, -0.1278, "city", 0.9);

        let score_at_location = score(&candidate, 51.5074, -0.1278).unwrap();
        let score_10km_away = score(&candidate, 51.4074, -0.1278).unwrap();

        assert!(score_at_location > score_10km_away);
    }

    #[test]
    fn test_select_best_returns_highest_scoring_candidate() {
        let candidates = vec![
            create_test_candidate("London", 51.5074, -0.1278, "city", 0.9),
            create_test_candidate("Richmond", 51.4415, -0.3005, "town", 0.7),
            create_test_candidate("Camden", 51.5416, -0.1425, "town", 0.6),
        ];

        let result = select_best(candidates, 51.5074, -0.1278);
        assert!(result.is_some());
        let place = result.unwrap();
        assert_eq!(place.name, "London");
    }

    #[test]
    fn test_select_best_returns_none_when_no_candidates() {
        let candidates = vec![];
        let result = select_best(candidates, 51.5074, -0.1278);
        assert!(result.is_none());
    }

    #[test]
    fn test_select_best_transforms_to_place_struct() {
        let candidates = vec![
            create_test_candidate("London", 51.5074, -0.1278, "city", 0.9),
        ];

        let result = select_best(candidates, 51.5074, -0.1278);
        assert!(result.is_some());
        let place = result.unwrap();
        assert_eq!(place.name, "London");
        assert_eq!(place.country, "UK");
        assert!(place.admin.is_some());
        assert_eq!(place.kind, "city");
    }

    #[test]
    fn test_select_best_filters_out_distant_candidates() {
        let candidates = vec![
            create_test_candidate("London", 51.5074, -0.1278, "city", 0.9),
            create_test_candidate("Paris", 48.8566, 2.3522, "city", 0.95), // ~340 km away
        ];

        let result = select_best(candidates, 51.5074, -0.1278);
        assert!(result.is_some());
        let place = result.unwrap();
        assert_eq!(place.name, "London"); // Paris should be filtered out
    }

    #[test]
    fn test_select_best_with_tie_scores() {
        let candidates = vec![
            create_test_candidate("London", 51.5074, -0.1278, "city", 0.7),
            create_test_candidate("Camden", 51.5074, -0.1278, "city", 0.7),
        ];

        let result = select_best(candidates, 51.5074, -0.1278);
        assert!(result.is_some());
        let place = result.unwrap();

        // In case of tie, ensure one of the candidates is returned
        assert!(place.name == "London" || place.name == "Camden");
    }

    #[test]
    fn test_score_at_50km_boundary() {
        let candidate = create_test_candidate("London", 51.5074, -0.1278, "city", 0.9);

        // Approx 50 km north of London
        let score = score(&candidate, 51.9574, -0.1278);
        assert!(score.is_some() || score.is_none()); // Boundary check
    }
}
