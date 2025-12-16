"""Runtime path utilities"""

from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "photidy"


def user_data_path() -> Path:
    """Per-user application data directory"""
    path = Path(user_data_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path
