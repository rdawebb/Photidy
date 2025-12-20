"""Runtime path utilities"""

from __future__ import annotations

import sys
from pathlib import Path


def runtime_root() -> Path:
    """Get the root directory of the runtime environment based on execution context

    Returns:
        Path: The root directory path
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def db_path() -> Path:
    """Get the path to the database file

    Returns:
        Path: The database file path
    """
    return runtime_root() / "rust" / "photo_meta" / "data" / "places_v0.1.db"
