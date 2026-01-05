use pyo3::exceptions::*;
use pyo3::PyErr;

#[derive(Debug)]
pub enum PhotoMetaError {
    Exif(String),
    Io(std::io::Error),
    Database(rusqlite::Error),
    Incompatible {
        db_version: String,
        crate_version: String,
    },
}

impl From<PhotoMetaError> for PyErr {
    fn from(err: PhotoMetaError) -> PyErr {
        match err {
            PhotoMetaError::Incompatible { db_version, crate_version } => {
                PyRuntimeError::new_err(format!(
                    "Database version ({}) is incompatible with crate version ({}) - please migrate the database",
                    db_version, crate_version
                ))
            }
            PhotoMetaError::Exif(msg) => {
                PyValueError::new_err(msg)
            }
            PhotoMetaError::Io(e) => {
                PyIOError::new_err(e.to_string())
            }
            PhotoMetaError::Database(e) => {
                PyRuntimeError::new_err(e.to_string())
            }
        }
    }
}
