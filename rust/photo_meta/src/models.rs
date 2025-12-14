#[derive(Debug)]
pub struct Place {
    pub name: String,
    pub country: String,
    pub admin: Option<String>,
    pub lat: f64,
    pub lon: f64,
    pub kind: String,
    pub importance: f64,
}
