"""Path utilities for Photidy app"""

from pathlib import Path

from appdirs import user_data_dir

app_name = "Photidy"
app_data_dir = user_data_dir(app_name)
Path(app_data_dir).mkdir(parents=True, exist_ok=True)

state_file = Path(app_data_dir) / "organiser_state.json"
undo_log = Path(app_data_dir) / "organiser_undo.log"
scan_cache = Path(app_data_dir) / "scan_cache.json"
