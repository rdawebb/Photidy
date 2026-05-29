use pyo3::prelude::*;

mod export;
mod pageviews;
mod scoring;
mod wikidata;

use crate::errors::PhotoMetaError;

// Results returned to Python for logging only, no data crosses the boundary

#[pyclass]
pub struct WikidataResult {
    #[pyo3(get)]
    pub lines_parsed: u64,
    #[pyo3(get)]
    pub entities_matched: u64,
    #[pyo3(get)]
    pub places_updated: u64,
    #[pyo3(get)]
    pub titles_mapped: u64,
}

#[pyclass]
pub struct PageviewResult {
    #[pyo3(get)]
    pub year_month: String,
    #[pyo3(get)]
    pub lines_parsed: u64,
    #[pyo3(get)]
    pub places_matched: u64,
}

#[pyclass]
pub struct ScoringResult {
    #[pyo3(get)]
    pub places_scored: u64,
    #[pyo3(get)]
    pub places_unscored: u64, // NULL importance after scoring
}

#[pyclass]
pub struct ExportResult {
    #[pyo3(get)]
    pub places_exported: u64,
    #[pyo3(get)]
    pub output_path: String,
}

/// Stream the Wikidata dump from a URL or local path.
/// Writes score_sitelinks to the build DB and populates wikidata_titles.
/// Returns counts for logging.
#[pyfunction]
pub fn build_wikidata_enrichment(
    build_db_path: &str,
    source: &str,
    projects: Vec<String>,
    max_streamed: Option<u64>,
) -> Result<WikidataResult, PhotoMetaError> {
    wikidata::run(build_db_path, source, projects, max_streamed)
}

/// Download, parse, and store raw pageview counts for one month.
/// Deletes the dump file after parsing.
/// Returns counts for logging.
#[pyfunction]
pub fn build_pageview_months(
    build_db_path: &str,
    year_months: Vec<String>, // ["2026-04", "2026-03", ...]
    project: &str,
) -> Result<Vec<PageviewResult>, PhotoMetaError> {
    let refs: Vec<&str> = year_months.iter().map(String::as_str).collect();
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .map_err(PhotoMetaError::Io)?;
    rt.block_on(pageviews::run_months(build_db_path, &refs, project))
}

/// Aggregate pageview_monthly raw counts into normalised scores and
/// compute weighted importance. Called after all months are loaded,
/// or during a monthly update.
#[pyfunction]
pub fn build_compute_scores(
    build_db_path: &str,
    months_total: u32,  // 12
    months_recent: u32, // 3
    w_views_12m: f64,
    w_views_3m: f64,
    w_sitelinks: f64,
) -> Result<ScoringResult, PhotoMetaError> {
    scoring::run(
        build_db_path,
        months_total,
        months_recent,
        w_views_12m,
        w_views_3m,
        w_sitelinks,
    )
}

/// Export the build DB to the app DB, stripping all build-time tables.
/// Applies regional pruning at export time so the build DB retains full data.
#[pyfunction]
pub fn build_export_app_db(
    build_db_path: &str,
    app_db_path: &str,
    regional_cap: u32,
) -> Result<ExportResult, PhotoMetaError> {
    export::run(build_db_path, app_db_path, regional_cap)
}
