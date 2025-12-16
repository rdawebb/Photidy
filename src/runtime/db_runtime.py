"""Database runtime logic"""

from pathlib import Path

from .extraction import extract_embedded_db
from .paths import user_data_path

APP_NAME = "photidy"


def runtime_db_path(rust) -> Path:
    """Get the path to the runtime database file

    Args:
        rust: The rust photo_meta module

    Returns:
        Path: The path to the runtime database file
    """
    return user_data_path() / rust.db_filename()


def ensure_db(rust) -> Path:
    """Ensure the runtime database exists and is valid

    Args:
        rust: The rust photo_meta module

    Returns:
        Path: The path to the valid runtime database file
    """
    path = runtime_db_path(rust)

    if path.exists():
        try:
            rust.validate_db(path)
            return path
        except Exception:
            path.unlink()

    extract_embedded_db(path)
    rust.validate_db(path)
    return path
