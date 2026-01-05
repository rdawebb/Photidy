"""Module to manage the embedded database for reverse geocoding"""

from _photidy import reverse_geocode  # type: ignore
from src.utils.errors import DatabaseError

from .extraction import extract_db
from .paths import db_path


def ensure_db() -> None:
    """Ensure the embedded database is extracted to the expected location"""
    db = db_path()

    if not db.exists():
        extract_db(db)

    try:
        reverse_geocode(0.0, 0.0, str(db))
    except RuntimeError as e:
        if "incompatible" in str(e).lower():
            extract_db(db)
        else:
            raise DatabaseError("Database is corrupted or inaccessible") from e
