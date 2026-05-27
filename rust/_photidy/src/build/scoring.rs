use super::ScoringResult;
use crate::errors::PhotoMetaError;
use rusqlite::{params, Connection};

pub fn run(
    build_db_path: &str,
    months_total: u32,
    months_recent: u32,
    w_views_12m: f64,
    w_views_3m: f64,
    w_sitelinks: f64,
) -> Result<ScoringResult, PhotoMetaError> {
    let conn = Connection::open(build_db_path).map_err(PhotoMetaError::Database)?;

    // Get the N most recent year_months present in pageview_monthly
    let all_months = _recent_months(&conn, months_total)?;
    let recent_months = _recent_months(&conn, months_recent)?;

    if all_months.is_empty() {
        eprintln!("Scoring: no pageview data found, skipping pageview scores");
    }

    // Aggregate raw counts per place for each window
    // Stored as intermediate columns, then normalised via 99th percentile

    if !all_months.is_empty() {
        _aggregate_views(&conn, &all_months, "score_views_12m")?;
        _aggregate_views(&conn, &recent_months, "score_views_3m")?;
        _normalise_column(&conn, "score_views_12m")?;
        _normalise_column(&conn, "score_views_3m")?;
    }

    // Weighted importance
    conn.execute(
        &format!(
            "UPDATE places SET importance = (
            {w_views_12m} * COALESCE(score_views_12m, 0.0) +
            {w_views_3m}  * COALESCE(score_views_3m,  0.0) +
            {w_sitelinks} * COALESCE(score_sitelinks,  0.0)
        )
        WHERE score_sitelinks IS NOT NULL
           OR score_views_12m IS NOT NULL
           OR score_views_3m  IS NOT NULL"
        ),
        [],
    )
    .map_err(PhotoMetaError::Database)?;

    let places_scored: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM places WHERE importance IS NOT NULL",
            [],
            |r| r.get(0),
        )
        .map_err(PhotoMetaError::Database)?;

    let places_unscored: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM places WHERE importance IS NULL",
            [],
            |r| r.get(0),
        )
        .map_err(PhotoMetaError::Database)?;

    Ok(ScoringResult {
        places_scored: places_scored as u64,
        places_unscored: places_unscored as u64,
    })
}

fn _recent_months(conn: &Connection, n: u32) -> Result<Vec<String>, PhotoMetaError> {
    let mut stmt = conn
        .prepare(
            "SELECT DISTINCT year_month FROM pageview_monthly
         ORDER BY year_month DESC LIMIT ?1",
        )
        .map_err(PhotoMetaError::Database)?;

    let months: Vec<String> = stmt
        .query_map(params![n], |r| r.get(0))
        .map_err(PhotoMetaError::Database)?
        .filter_map(|r| r.ok())
        .collect();

    Ok(months)
}

fn _aggregate_views(
    conn: &Connection,
    months: &[String],
    target_col: &str,
) -> Result<(), PhotoMetaError> {
    // Build placeholder list for IN clause
    let placeholders: String = months
        .iter()
        .enumerate()
        .map(|(i, _)| format!("?{}", i + 1))
        .collect::<Vec<_>>()
        .join(", ");

    let sql = format!(
        "UPDATE places SET {target_col} = (
            SELECT CAST(SUM(view_count) AS REAL)
            FROM pageview_monthly
            WHERE pageview_monthly.geonames_id = places.geonames_id
              AND year_month IN ({placeholders})
        )"
    );

    let params: Vec<&dyn rusqlite::ToSql> =
        months.iter().map(|m| m as &dyn rusqlite::ToSql).collect();

    conn.execute(&sql, params.as_slice())
        .map_err(PhotoMetaError::Database)?;
    Ok(())
}

fn _normalise_column(conn: &Connection, col: &str) -> Result<(), PhotoMetaError> {
    // Compute 99th percentile from non-null values
    // SQLite has no built-in percentile, so computed in Rust
    let mut stmt = conn
        .prepare(&format!(
            "SELECT {col} FROM places WHERE {col} IS NOT NULL ORDER BY {col}"
        ))
        .map_err(PhotoMetaError::Database)?;

    let values: Vec<f64> = stmt
        .query_map([], |r| r.get(0))
        .map_err(PhotoMetaError::Database)?
        .filter_map(|r| r.ok())
        .collect();

    if values.is_empty() {
        return Ok(());
    }

    let ceiling = _percentile_99(&values);
    if ceiling == 0.0 {
        return Ok(());
    }

    conn.execute(
        &format!("UPDATE places SET {col} = MIN({col} / ?1, 1.0) WHERE {col} IS NOT NULL"),
        params![ceiling],
    )
    .map_err(PhotoMetaError::Database)?;

    Ok(())
}

fn _percentile_99(sorted: &[f64]) -> f64 {
    // Values arrive pre-sorted from the ORDER BY query
    let idx = (0.99 * (sorted.len() - 1) as f64) as usize;
    sorted[idx.min(sorted.len() - 1)]
}
