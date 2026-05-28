"""Path utilities for Photidy app"""

from pathlib import Path

from appdirs import user_data_dir

APP_NAME = "Photidy"
APP_DATA_DIR: Path = user_data_dir(appname=APP_NAME)
Path(APP_DATA_DIR).mkdir(parents=True, exist_ok=True)

STATE_FILE: Path = Path(APP_DATA_DIR) / "organiser_state.json"
UNDO_LOG: Path = Path(APP_DATA_DIR) / "organiser_undo.log"
SCAN_CACHE: Path = Path(APP_DATA_DIR) / "scan_cache.json"

LOG_DIR: Path = Path(APP_DATA_DIR) / "logs"
