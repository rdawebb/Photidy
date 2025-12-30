"""Path utilities for Photidy app"""

from appdirs import user_data_dir
from pathlib import Path


app_name = "Photidy"
app_data_dir = user_data_dir(app_name)
Path(app_data_dir).mkdir(parents=True, exist_ok=True)

state_file = Path(app_data_dir) / "organiser_state.json"
undo_log = Path(app_data_dir) / "organiser_undo.log"
