"""Module to manage the embedded database for reverse geocoding"""

from _photidy import reverse_geocode
from src.utils.errors import DatabaseError

from .extraction import extract_db
from .paths import get_db_path


def ensure_db() -> None:
    """Ensure the embedded database is extracted to the expected location"""
    db_path = get_db_path()

    if not db_path.exists():
        extract_db(db_path)

    try:
        reverse_geocode(0.0, 0.0, str(db_path))
    except RuntimeError as e:
        if "incompatible" in str(e).lower():
            extract_db(db_path)
        else:
            raise DatabaseError("Database is corrupted or inaccessible") from e
