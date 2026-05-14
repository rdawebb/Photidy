"""Clean up build artifacts and cache files"""

import shutil
import sys
from pathlib import Path


def remove_path(path: Path):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.is_file():
        path.unlink()


def clean_caches():
    for pattern in [
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "src/.ruff_cache",
        "src/__pycache__",
        "tests/__pycache__",
        "*.egg-info",
        "*.dist-info",
    ]:
        for path in Path(".").rglob(pattern):
            remove_path(path)

    for path in Path(".").rglob(pattern="*"):
        if path.is_dir() and path.name == "__pycache__":
            remove_path(path)

    for pyc in Path(".").rglob(pattern="*.pyc"):
        remove_path(path=pyc)


def clean_build_artifacts():
    for rust_dir in [Path("rust/photidy"), Path("rust/metadata")]:
        cargo_target: Path = rust_dir / "target"
        remove_path(path=cargo_target)


def clean_site_packages():
    venv = Path(sys.prefix)
    candidates: list[Path] = list(venv.glob(pattern="lib/python*/site-packages"))
    if not candidates:
        return
    site_packages: Path = candidates[0]
    patterns: list[str] = [
        "photo_meta*",
        "photidy*",
        "*.so",
        "*.pyd",
        "*.egg-info",
        "*.dist-info",
    ]
    for pattern in patterns:
        for path in site_packages.rglob(pattern):
            remove_path(path)


if __name__ == "__main__":
    clean_caches()
    clean_build_artifacts()
    clean_site_packages()
