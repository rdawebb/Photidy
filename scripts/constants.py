"""Constants for building the 'places' database"""

from pathlib import Path

DB_VERSION = "0.1"
OUTPUT_DIR = "rust/_photidy/data"
OUTPUT_DB = f"places_v{DB_VERSION}.db"
DATA_SOURCES = "scripts/data"

CITIES_ZIP: Path = Path(DATA_SOURCES) / "cities1000.zip"
ALLCOUNTRIES_ZIP: Path = Path(DATA_SOURCES) / "allCountries.zip"

CITIES_COLUMNS: dict[str, int] = {
    "geonameid": 0,
    "name": 1,
    "latitude": 4,
    "longitude": 5,
    "feature_code": 7,
    "country": 8,
    "admin1": 10,
    "population": 14,
}

LANDMARKS_COLUMNS: dict[str, int] = {
    "geonameid": 0,
    "name": 1,
    "latitude": 4,
    "longitude": 5,
    "feature_code": 7,
    "country": 8,
    "admin1": 10,
    "elevation": 15,
}

ALLOWED_FEATURE_CODES: set[str] = {
    # Major landmarks
    "MNMT",  # monuments
    "MUS",  # museums
    "ZOO",  # zoos
    "STDM",  # stadiums
    "CAST",  # castles
    "PAL",  # palaces
    "CH",  # churches
    "CATH",  # cathedrals
    "MOSQ",  # mosques
    "TMPL",  # temples
    "BRDG",  # bridges
    "DAM",  # dams
    # Natural landmarks
    "MT",  # mountains
    "CANY",  # canyons
    "VOLC",  # volcanoes
    "ARCH",  # arches
    # Parks and protected areas
    "NPRK",  # national parks
    "PARK",  # parks
    # Historic sites
    "RUIN",  # ruins
    "HSTS",  # historic sites
}

EXCLUDED_FEATURE_PREFIXES: set[str] = {
    "S.BLDG",  # buildings
    "S.SHOP",  # shops
    "S.OFF",  # offices
    "S.TRANS",  # transportation
}
