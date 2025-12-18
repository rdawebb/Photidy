#[derive(Debug)]
pub enum DbError {
    Open(rusqlite::Error),
    Incompatible(String),
    Query(rusqlite::Error),
}