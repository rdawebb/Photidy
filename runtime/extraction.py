"""Embedded database extraction logic"""

from importlib import resources
from pathlib import Path
import shutil


def extract_db(dest: Path) -> None:
    """Extract the embedded database to the destination path

    Args:
        dest (Path): The destination path for the database file - must not exist
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    with resources.as_file(resources.files("photidy.resources") / dest.name) as src:
        shutil.copyfile(src, dest)
