use chrono::DateTime;

#[derive(Debug, Clone)]
pub struct ExifData {
    pub timestamp: Option<DateTime<chrono::Utc>>,
    pub lat: Option<f64>,
    pub lon: Option<f64>,
}

#[derive(Debug, Clone)]
pub struct Candidate {
    pub name: String,
    pub country: String,
    pub admin: Option<String>,
    pub lat: f64,
    pub lon: f64,
    pub kind: PlaceKind,
    pub importance: f64,
}

#[derive(Debug, Clone)]
pub struct Place {
    pub name: String,
    pub country: String,
    pub admin: Option<String>,
    pub kind: PlaceKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlaceKind {
    Landmark,
    City,
    Town,
}
