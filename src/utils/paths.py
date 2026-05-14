"""Path utilities for Photidy app"""

from pathlib import Path

from appdirs import user_data_dir

app_name = "Photidy"
app_data_dir: Path = user_data_dir(appname=app_name)
Path(app_data_dir).mkdir(parents=True, exist_ok=True)

state_file: Path = Path(app_data_dir) / "organiser_state.json"
undo_log: Path = Path(app_data_dir) / "organiser_undo.log"
scan_cache: Path = Path(app_data_dir) / "scan_cache.json"
