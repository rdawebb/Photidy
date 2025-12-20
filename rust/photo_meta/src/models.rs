use pyo3::pyclass;

#[pyclass]
#[derive(Debug, Clone)]
pub struct ExtractedMetadata {
    #[pyo3(get)]
    pub timestamp: Option<String>,
    #[pyo3(get)]
    pub lat: Option<f64>,
    #[pyo3(get)]
    pub lon: Option<f64>,
}

#[derive(Debug, Clone)]
pub struct Candidate {
    pub name: String,
    pub country: String,
    pub admin: Option<String>,
    pub lat: f64,
    pub lon: f64,
    pub kind: String,
    pub importance: f64,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct Place {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub country: String,
    #[pyo3(get)]
    pub admin: Option<String>,
    #[pyo3(get)]
    pub kind: String,
}
