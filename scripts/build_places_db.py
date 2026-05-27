"""Script to build reverse geocoding database"""

import csv
import io
import os
import sqlite3
import sys
import zipfile
from _csv import Reader
from datetime import date
from logging import Logger
from pathlib import Path
from typing import Literal

from _photidy import (
    build_compute_scores,
    build_export_app_db,
    build_pageview_month,
    build_wikidata_enrichment,
)

from scripts.constants import (
    ALLCOUNTRIES_ZIP,
    ALLOWED_FEATURE_CODES,
    CITIES_COLUMNS,
    CITIES_ZIP,
    DB_VERSION,
    EXCLUDED_FEATURE_PREFIXES,
    LANDMARKS_COLUMNS,
)
from src.utils.errors import DatabaseError
from src.utils.logger import get_logger

sys.path.append(str(object=Path(__file__).resolve().parent.parent))

logger: Logger = get_logger(name=__name__)

# Wikidata JSON dump source, URL (streamed directly) or a local fil path.
# https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz
WIKIDATA_DUMP: str | None = os.getenv("WIKIDATA_DUMP")


# Wikipedia project to use for pageview data.
PAGEVIEW_PROJECT = "en.wikipedia"

# Number of recent months to look back for pageview data.
PAGEVIEW_MONTHS_TOTAL = 12
PAGEVIEW_MONTHS_RECENT = 3

# Importance weights. Must sum to 1.0. Tunable once scoring is validated.
W_VIEWS_12M = 0.5
W_VIEWS_3M = 0.3
W_SITELINKS = 0.2

# Regional pruning cap applied at export time, build DB retains all scored entries.
REGIONAL_CAP = 200

# Database Paths
BUILD_DB_DIR: Path = Path("rust/_photidy/data/build")
BUILD_DB: str = str(BUILD_DB_DIR / "places_build.db")
APP_DB: str = str(Path("rust/_photidy/data") / f"places_v{DB_VERSION}.db")


def _ensure_dir() -> None:
    """Ensure output directory exists"""
    BUILD_DB_DIR.mkdir(parents=True, exist_ok=True)


def _connect_db() -> sqlite3.Connection:
    """Connect to the SQLite database

    Returns:
        sqlite3.Connection: Database connection
    """
    db: Path = Path(BUILD_DB)
    if db.exists():
        db.unlink()

    return sqlite3.connect(database=db)


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create the database schema

    Args:
        conn (sqlite3.Connection): Database connection
    """
    conn.executescript("""
        DROP TABLE IF EXISTS places;
        CREATE TABLE places (
            id              INTEGER PRIMARY KEY,
            geonames_id     INTEGER NOT NULL,
            name            TEXT    NOT NULL,
            country         TEXT    NOT NULL,
            admin           TEXT,
            lat             REAL    NOT NULL,
            lon             REAL    NOT NULL,
            kind            TEXT    NOT NULL,
            score_sitelinks REAL,
            score_views_3m  REAL,
            score_views_12m REAL,
            importance      REAL
        );

        DROP TABLE IF EXISTS meta;
        CREATE TABLE meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    logger.info("Schema created")


def _create_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes for the database

    Args:
        conn (sqlite3.Connection): Database connection
    """
    conn.executescript("""
        CREATE INDEX idx_places_lat_lon      ON places (lat, lon);
        CREATE INDEX idx_places_kind         ON places (kind);
        CREATE INDEX idx_places_importance   ON places (importance DESC);
        CREATE INDEX idx_places_geonames_id  ON places (geonames_id);
        CREATE INDEX idx_lat_lon_importance  ON places (lat, lon, importance DESC);
    """)
    logger.info("Indexes created")


def _write_meta(conn: sqlite3.Connection) -> None:
    """Write metadata to the database

    Args:
        conn (sqlite3.Connection): Database connection
    """
    today: str = date.today().isoformat()
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [
            ("db_version", DB_VERSION),
            ("source", "GeoNames+Wikidata+WikipediaPageviews"),
            ("generated", today),
            ("pageview_project", PAGEVIEW_PROJECT),
            ("pageview_months_total", str(PAGEVIEW_MONTHS_TOTAL)),
            ("pageview_months_recent", str(PAGEVIEW_MONTHS_RECENT)),
            ("weight_views_12m", str(W_VIEWS_12M)),
            ("weight_views_3m", str(W_VIEWS_3M)),
            ("weight_sitelinks", str(W_SITELINKS)),
        ],
    )
    logger.info("Meta data written")


def _valid_coords(lat: float, lon: float) -> bool:
    """Check if coordinates are valid

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        bool: True if coordinates are valid, False otherwise
    """
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _valid_location(name: str, feature_code: str) -> bool:
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
    return True


def load_cities(conn: sqlite3.Connection) -> None:
    """Load city data from cities1000.zip

    Args:
        conn (sqlite3.Connection): Database connection

    Raises:
        DatabaseError: If there is an error loading the data
    """
    logger.info(msg="Loading cities1000...")
    rows: list[tuple] = []

    try:
        with zipfile.ZipFile(file=CITIES_ZIP) as zf:
            with zf.open(name="cities1000.txt") as f:
                reader: Reader = csv.reader(
                    io.TextIOWrapper(buffer=f, encoding="utf-8"), delimiter="\t"
                )
                for row in reader:
                    try:
                        geonames_id: int = int(row[0])
                        name: str = row[CITIES_COLUMNS["name"]]
                        lat: float = float(row[CITIES_COLUMNS["latitude"]])
                        lon: float = float(row[CITIES_COLUMNS["longitude"]])
                        country: str = row[CITIES_COLUMNS["country"]]
                        admin: str | None = row[CITIES_COLUMNS["admin1"]] or None
                        population: int = int(row[CITIES_COLUMNS["population"]] or 0)
                    except (IndexError, ValueError):
                        logger.warning(msg=f"Malformed row in cities1000: {row}")
                        continue

                    if not _valid_coords(lat, lon):
                        continue

                    kind: Literal["city", "town"] = (
                        "city" if population >= 100_000 else "town"
                    )
                    rows.append((geonames_id, name, country, admin, lat, lon, kind))

    except (FileNotFoundError, zipfile.BadZipFile, KeyError) as e:
        raise DatabaseError(f"Failed to open or read {CITIES_ZIP}: {e}")

    if rows:
        conn.executemany(
            "INSERT INTO places (geonames_id, name, country, admin, lat, lon, kind) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        logger.info(msg=f"Inserted {len(rows):,} cities/towns")
    else:
        logger.info(msg="No cities/towns inserted")


def load_landmarks(conn: sqlite3.Connection) -> None:
    """Load landmark data from allCountries.zip

    Args:
        conn (sqlite3.Connection): Database connection

    Raises:
        DatabaseError: If there is an error loading the data
    """
    logger.info(msg="Loading landmarks from allCountries...")
    rows: list[tuple] = []

    try:
        with zipfile.ZipFile(file=ALLCOUNTRIES_ZIP) as zf:
            with zf.open(name="allCountries.txt") as f:
                reader: Reader = csv.reader(
                    io.TextIOWrapper(buffer=f, encoding="utf-8"), delimiter="\t"
                )
                for row in reader:
                    try:
                        geonames_id: int = int(row[0])
                        name: str = row[LANDMARKS_COLUMNS["name"]]
                        lat: float = float(row[LANDMARKS_COLUMNS["latitude"]])
                        lon: float = float(row[LANDMARKS_COLUMNS["longitude"]])
                        country: str = row[LANDMARKS_COLUMNS["country"]]
                        admin: str | None = row[LANDMARKS_COLUMNS["admin1"]] or None
                        feature_code: str = row[LANDMARKS_COLUMNS["feature_code"]]
                    except (IndexError, ValueError):
                        logger.warning(msg=f"Malformed row in allCountries: {row}")
                        continue

                    if not _valid_coords(lat, lon):
                        continue
                    if not _valid_location(name, feature_code):
                        continue

                    rows.append(
                        (geonames_id, name, country, admin, lat, lon, "landmark")
                    )

    except (FileNotFoundError, zipfile.BadZipFile, KeyError) as e:
        raise DatabaseError(f"Failed to open or read {ALLCOUNTRIES_ZIP}: {e}")

    if rows:
        conn.executemany(
            "INSERT INTO places (geonames_id, name, country, admin, lat, lon, kind) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        logger.info(msg=f"Inserted {len(rows):,} landmarks")
    else:
        logger.info(msg="No landmarks inserted")


def validate_db(conn: sqlite3.Connection) -> None:
    """Log a summary of the final database contents.

    Args:
        conn: Database connection

    Raises:
        DatabaseError: If the database validation fails
    """
    logger.info(msg="Validating database...")

    try:
        cur = conn.cursor()

        total: int = cur.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        logger.info(msg=f"Total places: {total:,}")

        for kind in ["city", "town", "landmark"]:
            count: int = cur.execute(
                "SELECT COUNT(*) FROM places WHERE kind = ?", (kind,)
            ).fetchone()[0]
            logger.info(msg=f"  {kind}: {count:,}")

        for col in (
            "importance",
            "score_sitelinks",
            "score_views_12m",
            "score_views_3m",
        ):
            null_count: int = cur.execute(
                f"SELECT COUNT(*) FROM places WHERE {col} IS NULL"
            ).fetchone()[0]
            if null_count:
                logger.warning(msg=f"  {null_count:,} entries have NULL {col}")

        top = cur.execute(
            "SELECT name, country, importance FROM places ORDER BY importance DESC LIMIT 10"
        ).fetchall()
        logger.info(msg="Top 10 by importance:")
        for row in top:
            logger.info(msg=f"  {row}")

        nulls: int = cur.execute(
            "SELECT COUNT(*) FROM places "
            "WHERE name IS NULL OR country IS NULL OR lat IS NULL OR lon IS NULL"
        ).fetchone()[0]
        if nulls:
            logger.warning(msg=f"  {nulls:,} entries have NULL critical fields")
        else:
            logger.info(msg="No NULL critical fields")

    except sqlite3.DatabaseError as e:
        raise DatabaseError(f"Validation failed: {e}")


def _pageview_months(total: int) -> list[str]:
    """Return the last `total` months as a list of strings, chronologically ordered.

    Args:
        total: The number of months to return.

    Returns:
        A list of strings representing the last `total` months, chronologically ordered.
    """
    today = date.today()
    end_month = today.month - 1 or 12
    end_year = today.year if today.month > 1 else today.year - 1

    months = []
    y, m = end_year, end_month

    for _ in range(total):
        months.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    months.reverse()

    return months


def main() -> None:
    """Build the places database."""
    try:
        _ensure_dir()
        conn: sqlite3.Connection = _connect_db()
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        try:
            _create_schema(conn)
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"Schema creation failed: {e}")

        try:
            load_cities(conn)
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"City loading failed: {e}")

        try:
            load_landmarks(conn)
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"Landmark loading failed: {e}")

        # Create geonames_id index before enrichment so UPDATE lookups are fast
        try:
            _create_indexes(conn)
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"Index creation failed: {e}")

        conn.commit()
        conn.close()

        if WIKIDATA_DUMP is None:
            logger.warning(
                msg="WIKIDATA_DUMP not set, skipping Wikidata enrichment. "
                "Set WIKIDATA_DUMP env var and re-run to produce a usable database."
            )
            return

        result = build_wikidata_enrichment(BUILD_DB, WIKIDATA_DUMP)
        logger.info(
            msg=f"Wikidata: {result.entities_matched:,} matched "
            f"from {result.entities_streamed:,} streamed, "
            f"{result.titles_mapped:,} enwiki titles mapped"
        )

        all_months = _pageview_months(PAGEVIEW_MONTHS_TOTAL)
        for ym in all_months:
            result = build_pageview_month(BUILD_DB, ym, PAGEVIEW_PROJECT)
            logger.info(
                msg=f"Pageviews: {result.year_month}: "
                f"{result.places_matched:,} matched from {result.lines_parsed:,} lines"
            )

        result = build_compute_scores(
            BUILD_DB,
            PAGEVIEW_MONTHS_TOTAL,
            PAGEVIEW_MONTHS_RECENT,
            W_VIEWS_12M,
            W_VIEWS_3M,
            W_SITELINKS,
        )
        logger.info(
            msg=f"Scoring: {result.places_scored:,} scored, "
            f"{result.places_unscored:,} unscored (will be pruned at export)"
        )

        build_conn = sqlite3.connect(BUILD_DB)
        try:
            _write_meta(build_conn)
            build_conn.commit()
            validate_db(build_conn)
        finally:
            build_conn.close()

        result = build_export_app_db(BUILD_DB, APP_DB, REGIONAL_CAP)
        logger.info(
            msg=f"Export: {result.places_exported:,} places -> {result.output_path}"
        )

    except DatabaseError as e:
        logger.error(msg=f"Database build failed: {e}")
        return


if __name__ == "__main__":
    main()
