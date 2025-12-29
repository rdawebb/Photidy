"""Script to build reverse geocoding database"""

import csv
import io
import sqlite3
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.utils.errors import DatabaseError
from src.utils.logger import get_logger

from scripts.constants import (
    ALLOWED_FEATURE_CODES,
    ALLCOUNTRIES_ZIP,
    CITIES_ZIP,
    CITIES_COLUMNS,
    COMPILED_CLASS_REGEXES,
    COMPILED_MISC_REGEXES,
    DB_VERSION,
    EXCLUDED_FEATURE_PREFIXES,
    FAMOUS_PARK_KEYWORDS,
    FEATURE_CODE_IMPORTANCE,
    LANDMARKS_COLUMNS,
    OUTPUT_DB,
    OUTPUT_DIR,
    PARK_REGEX,
)

logger = get_logger(__name__)


def _ensure_dirs() -> None:
    """Ensure output directories exist"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def _connect_db() -> sqlite3.Connection:
    """Connect to the SQLite database

    Returns:
        sqlite3.Connection: Database connection
    """
    path = Path(OUTPUT_DIR) / OUTPUT_DB
    if path.exists():
        path.unlink()
    return sqlite3.connect(path)


def _create_schema(conn) -> None:
    """Create the database schema

    Args:
        conn (sqlite3.Connection): Database connection
    """
    conn.executescript("""
        DROP TABLE IF EXISTS places;
        CREATE TABLE places (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            admin TEXT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            kind TEXT NOT NULL,
            importance REAL NOT NULL
        );
                       
        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)


def _create_indexes(conn) -> None:
    """Create indexes for the database

    Args:
        conn (sqlite3.Connection): Database connection
    """
    conn.executescript("""
        CREATE INDEX idx_places_lat_lon ON places (lat, lon);
        CREATE INDEX idx_places_kind ON places (kind);
        CREATE INDEX idx_places_importance ON places (importance DESC);
    """)


def _write_meta(conn) -> None:
    """Write metadata to the database

    Args:
        conn (sqlite3.Connection): Database connection
    """
    today = date.today().isoformat()
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [("db_version", DB_VERSION), ("source", "GeoNames"), ("generated", today)],
    )


def _valid_coords(lat, lon) -> bool:
    """Check if coordinates are valid

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        bool: True if coordinates are valid, False otherwise
    """
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _park_filter(name: str, feature_code: str) -> bool:
    """Filter parks based on name patterns

    Args:
        name (str): Name of the park
        feature_code (str): Feature code

    Returns:
        bool: True if park should be included, False otherwise
    """
    if feature_code == "NPRK":
        return True

    name_lower = name.lower()

    if "national park" in name_lower:
        return True

    if any(k in name_lower for k in FAMOUS_PARK_KEYWORDS):
        return True

    words = name.split()
    if len(words) >= 2 and not PARK_REGEX.search(name):
        return True

    return False


def _valid_location(name: str, feature_code: str, elevation: int | None) -> bool:
    """Check if a location is valid based on name and feature attributes

    Args:
        name (str): Name of the location
        feature_class (str): Feature class
        feature_code (str): Feature code

    Returns:
        bool: True if location is valid, False otherwise
    """
    if feature_code not in ALLOWED_FEATURE_CODES:
        return False

    if any(feature_code.startswith(prefix) for prefix in EXCLUDED_FEATURE_PREFIXES):
        return False

    if len(name) <= 3 or name.isupper() or name.isdigit():
        return False

    if feature_code == "PRK":
        if not _park_filter(name, feature_code):
            return False

    if feature_code == "MT":
        if elevation is not None and elevation != "":
            try:
                if int(elevation) < 1500:
                    return False
            except (ValueError, TypeError):
                return False
        else:
            return False

    class_regex = COMPILED_CLASS_REGEXES.get(feature_code)
    if class_regex and class_regex.search(name):
        return False

    for regex in COMPILED_MISC_REGEXES:
        if regex.search(name):
            return False

    return True


def _city_importance(population: int, feature_code: str) -> float:
    """Compute importance for a city based on population

    Args:
        population (int): Population of the city
        feature_code (str): Feature code

    Returns:
        float: Importance score
    """
    if feature_code == "PPLC":  # capital
        return 5.0
    elif feature_code.startswith("PPLA"):  # major city
        return 4.8
    elif population >= 10_000_000:
        return 4.7
    elif population >= 5_000_000:
        return 4.6
    elif population >= 1_000_000:
        return 4.5
    elif population >= 250_000:
        return 4.4
    elif population >= 50_000:
        return 4.1
    elif population >= 10_000:
        return 3.8
    else:
        return 3.4


def _park_importance(name: str, feature_code: str) -> float:
    """Compute importance for a park based on name patterns

    Args:
        name (str): Name of the park
        feature_code (str): Feature code

    Returns:
        float: Importance score
    """
    if feature_code == "NPRK":
        return 4.6

    if any(k in name.lower() for k in FAMOUS_PARK_KEYWORDS):
        return 4.4

    return 3.8


def load_cities(conn) -> None:
    """Load city data from cities1000.zip

    Args:
        conn (sqlite3.Connection): Database connection

    Raises:
        DatabaseError: If there is an error loading the data
    """
    logger.info("Loading cities1000...")

    rows = []
    try:
        with zipfile.ZipFile(CITIES_ZIP) as zf:
            with zf.open("cities1000.txt") as f:
                reader = csv.reader(
                    io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t"
                )

                for row in reader:
                    try:
                        name = row[CITIES_COLUMNS["name"]]
                        lat = float(row[CITIES_COLUMNS["latitude"]])
                        lon = float(row[CITIES_COLUMNS["longitude"]])
                        feature_code = row[CITIES_COLUMNS["feature_code"]]
                        country = row[CITIES_COLUMNS["country"]]
                        admin = row[CITIES_COLUMNS["admin1"]] or None
                        population = int(row[CITIES_COLUMNS["population"]] or 0)
                    except (IndexError, ValueError):
                        logger.warning(f"Malformed row in {CITIES_ZIP}: {row}")
                        continue

                    if not _valid_coords(lat, lon):
                        continue

                    kind = "city" if population >= 100000 else "town"
                    importance = _city_importance(population, feature_code)

                    rows.append((name, country, admin, lat, lon, kind, importance))

    except (FileNotFoundError, zipfile.BadZipFile, KeyError) as e:
        logger.error(f"Error opening {CITIES_ZIP}: {e}")
        raise DatabaseError(f"Failed to open or read {CITIES_ZIP}: {e}")

    if rows:
        conn.executemany(
            """
            INSERT INTO places (name, country, admin, lat, lon, kind, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        logger.info(f"Inserted {len(rows)} cities/towns")
    else:
        logger.info("No cities/towns inserted")


def load_landmarks(conn) -> None:
    """Load landmark data from allCountries.zip

    Args:
        conn (sqlite3.Connection): Database connection

    Raises:
        DatabaseError: If there is an error loading the data
    """
    logger.info("Loading landmarks from allCountries...")

    rows = []
    try:
        with zipfile.ZipFile(ALLCOUNTRIES_ZIP) as zf:
            with zf.open("allCountries.txt") as f:
                reader = csv.reader(
                    io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t"
                )

                for row in reader:
                    try:
                        name = row[LANDMARKS_COLUMNS["name"]]
                        lat = float(row[LANDMARKS_COLUMNS["latitude"]])
                        lon = float(row[LANDMARKS_COLUMNS["longitude"]])
                        country = row[LANDMARKS_COLUMNS["country"]]
                        admin = row[LANDMARKS_COLUMNS["admin1"]] or None
                        feature_code = row[LANDMARKS_COLUMNS["feature_code"]]
                        elevation = row[LANDMARKS_COLUMNS["elevation"]]
                    except (IndexError, ValueError):
                        logger.warning(f"Malformed row in {ALLCOUNTRIES_ZIP}: {row}")
                        continue

                    if not _valid_coords(lat, lon):
                        continue

                    if not _valid_location(name, feature_code, elevation):
                        continue

                    if feature_code == "PRK":
                        importance = _park_importance(name, feature_code)
                    else:
                        importance = FEATURE_CODE_IMPORTANCE.get(feature_code, 3.0)

                    rows.append(
                        (name, country, admin, lat, lon, "landmark", importance)
                    )

    except (FileNotFoundError, zipfile.BadZipFile, KeyError) as e:
        logger.error(f"Error opening {ALLCOUNTRIES_ZIP}: {e}")
        raise DatabaseError(f"Failed to open or read {ALLCOUNTRIES_ZIP}: {e}")

    if rows:
        conn.executemany(
            """
            INSERT INTO places (name, country, admin, lat, lon, kind, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        logger.info(f"Inserted {len(rows)} landmarks")
    else:
        logger.info("No landmarks inserted")


def validate_db(conn) -> None:
    """Validate the database contents

    Args:
        conn (sqlite3.Connection): Database connection
    """
    logger.info("Validating database...")

    try:
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        logger.info(f"Total places: {total}")

        for kind in ["city", "town", "landmark"]:
            count = cur.execute(
                "SELECT COUNT(*) FROM places WHERE kind = ?", (kind,)
            ).fetchone()[0]
            logger.info(f"{kind} total: {count}")

        top = cur.execute(
            "SELECT name, country, importance FROM places ORDER BY importance DESC LIMIT 5"
        ).fetchall()
        logger.info("Top importance entries:")
        for row in top:
            logger.info(f"   {row}")

        duplicates = cur.execute("""
            SELECT name, country, admin, lat, lon, COUNT(*) as cnt
            FROM places
            GROUP BY name, country, admin, lat, lon
            HAVING cnt > 1
        """).fetchall()

        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate entries - removing...")
            cur.execute("""
                DELETE FROM places
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM places
                    GROUP BY name, country, admin, lat, lon
                )
                AND (name, country, admin, lat, lon) IN (
                    SELECT name, country, admin, lat, lon
                    FROM places
                    GROUP BY name, country, admin, lat, lon
                    HAVING COUNT(*) > 1
                )
            """)
            logger.info("Duplicates removed")
        else:
            logger.info("No duplicates found")

        nulls = cur.execute("""
            SELECT COUNT(*) FROM places
            WHERE name IS NULL OR country IS NULL OR lat IS NULL OR lon IS NULL
        """).fetchone()[0]
        if nulls:
            logger.warning(f"Found {nulls} entries with NULL critical fields")
        else:
            logger.info("No NULL critical fields found")

    except sqlite3.DatabaseError as e:
        logger.error(f"Database validation failed: {e}")
        raise DatabaseError(f"Validation failed: {e}")


def main() -> None:
    """Main function to build the places database

    Raises:
        DatabaseError: If there is an error during database operations
    """
    try:
        _ensure_dirs()
        conn = _connect_db()
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        try:
            _create_schema(conn)
        except sqlite3.DatabaseError as e:
            logger.error(f"Database schema creation failed: {e}")
            raise DatabaseError(f"Schema creation failed: {e}")

        try:
            load_cities(conn)
        except sqlite3.DatabaseError as e:
            logger.error(f"Database city loading failed: {e}")
            raise DatabaseError(f"City loading failed: {e}")

        try:
            load_landmarks(conn)
        except sqlite3.DatabaseError as e:
            logger.error(f"Database landmark loading failed: {e}")
            raise DatabaseError(f"Landmark loading failed: {e}")

        try:
            _create_indexes(conn)
        except sqlite3.DatabaseError as e:
            logger.error(f"Database index creation failed: {e}")
            raise DatabaseError(f"Index creation failed: {e}")

        try:
            _write_meta(conn)
        except sqlite3.DatabaseError as e:
            logger.error(f"Database metadata writing failed: {e}")
            raise DatabaseError(f"Metadata writing failed: {e}")

        try:
            validate_db(conn)
        except sqlite3.DatabaseError as e:
            logger.error(f"Database validation failed: {e}")
            raise DatabaseError(f"Validation failed: {e}")

        try:
            conn.commit()
        except sqlite3.DatabaseError as e:
            logger.error(f"Database commit failed: {e}")
            raise DatabaseError(f"Commit failed: {e}")

        finally:
            conn.close()

    except DatabaseError as e:
        logger.error(f"Unexpected error during database build: {e}")
        return

    logger.info(f"Complete - wrote DB to {OUTPUT_DIR}/{OUTPUT_DB}")


if __name__ == "__main__":
    main()
