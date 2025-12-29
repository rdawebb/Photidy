"""Constants for building the 'places' database"""

import re
from pathlib import Path

DB_VERSION = "0.1"
OUTPUT_DIR = "rust/photidy/data"
OUTPUT_DB = f"places_v{DB_VERSION}.db"
DATA_SOURCES = "scripts/data"

CITIES_ZIP = Path(DATA_SOURCES) / "cities1000.zip"
ALLCOUNTRIES_ZIP = Path(DATA_SOURCES) / "allCountries.zip"

CITIES_COLUMNS = {
    "name": 1,
    "latitude": 4,
    "longitude": 5,
    "feature_code": 7,
    "country": 8,
    "admin1": 10,
    "population": 14,
}

LANDMARKS_COLUMNS = {
    "name": 1,
    "latitude": 4,
    "longitude": 5,
    "feature_code": 7,
    "country": 8,
    "admin1": 10,
    "elevation": 15,
}

ALLOWED_FEATURE_CODES = {
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

EXCLUDED_FEATURE_PREFIXES = {
    "S.BLDG",  # buildings
    "S.SHOP",  # shops
    "S.OFF",  # offices
    "S.TRANS",  # transportation
}

FEATURE_CODE_IMPORTANCE = {
    "MNMT": 4.8,
    "CATH": 4.8,
    "CAST": 4.7,
    "PAL": 4.7,
    "ZOO": 4.6,
    "STDM": 4.6,
    "NPRK": 4.6,
    "MUS": 4.5,
    "TMPL": 4.5,
    "MOSQ": 4.5,
    "MT": 4.5,
    "CANY": 4.6,
    "ARCH": 4.5,
    "VOLC": 4.5,
    "BRDG": 4.3,
    "DAM": 4.2,
    "HSTS": 4.2,
    "RUIN": 4.0,
    "PRK": 3.8,
}

CLASS_REGEXES = {
    "CH": r"^(Church|St\.?|Saint|San|Santa|Notre Dame|Église|Kirche)\b",
    "MT": r"^Mount\s+\w+$",
    "PRK": r"\b(Park|Playground|Recreation Ground|Recreation Area)$",
    "RUIN": r"^(Ruins of|Site of)\b",
}

MISC_REGEXES = {
    r"\b(District|Sector|Zone|Ward|Block|Lot|Parcel)\b",
    r"\b(North|South|East|West)$",
    r"\b(No\.?\s*\d+|\d+(st|nd|rd|th))\b",
    r"^[^aeiouAEIOU\s]*$",
    r"^(ADM\d+|Area\s+\d+|Block\s+\w+)$",
    r"\b(Substation|Transformer|Reservoir|Tank|Plant|Depot)\b",
    r"\b(Site|Facility|Complex)\b",
}

COMPILED_CLASS_REGEXES = {
    k: re.compile(pattern, re.IGNORECASE) for k, pattern in CLASS_REGEXES.items()
}

COMPILED_MISC_REGEXES = [re.compile(r, re.IGNORECASE) for r in MISC_REGEXES]

PARK_REGEX = re.compile(r"^(City|Town|Municipal|Public)\s+Park$", re.IGNORECASE)

FAMOUS_PARK_KEYWORDS = {
    "central",
    "hyde",
    "golden gate",
    "yosemite",
    "grand canyon",
    "yellowstone",
    "regents",
    "tiergarten",
    "ueno",
    "yoyogi",
    "chapultepec",
    "ibirapuera",
    "banff",
    "kruger",
    "serengeti",
    "everglades",
    "zion",
    "rocky mountain",
    "olympic",
    "sequoia",
    "plitvice",
    "torres del paine",
    "fiordland",
    "table mountain",
    "kakadu",
    "daintree",
    "great barrier reef",
    "galapagos",
    "patagonia",
    "niagara",
    "victoria falls",
    "angel falls",
    "yala",
    "chobe",
    "masai mara",
    "sundarbans",
    "taman negara",
    "komodo",
    "cairngorms",
    "loch ness",
    "snowdonia",
    "peak district",
    "lake district",
    "new forest",
    "dartmoor",
    "grand teton",
    "arches",
    "bryce canyon",
    "shenandoah",
    "badlands",
    "canyonlands",
    "death valley",
    "glacier",
    "great smoky",
    "mount rainier",
    "redwood",
    "saguaro",
    "voyageurs",
    "wind cave",
}
