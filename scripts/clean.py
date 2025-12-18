"""Clean up build artifacts and cache files"""

import shutil
from pathlib import Path


def remove_path(path: Path):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.is_file():
        path.unlink()


for pattern in [
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    "src/.ruff_cache",
    "src/__pycache__",
    "tests/__pycache__",
]:
    for path in Path(".").rglob(pattern):
        remove_path(path)

for path in Path(".").rglob("*"):
    if path.is_dir() and path.name == "__pycache__":
        remove_path(path)

for pyc in Path(".").rglob("*.pyc"):
    remove_path(pyc)

for rust_dir in [Path("rust/photo_meta"), Path("rust/metadata")]:
    cargo_target = rust_dir / "target"
    remove_path(cargo_target)
