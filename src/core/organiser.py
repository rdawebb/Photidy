"""Organiser module for organising photos based on metadata."""

import json
import os
import shutil
from pathlib import Path
from typing import Optional

from src.utils.constants import SUPPORTED_FORMATS
from src.utils.errors import (
    InvalidDirectoryError,
    PhotoMetadataError,
    PhotoOrganisationError,
)
from src.utils.logger import get_logger
from src.utils.paths import state_file, undo_log

from .metadata import get_image_info

logger = get_logger(__name__)

STAGING_DIR = ".staging"


def _load_state(state_file_path: Optional[Path] = None) -> dict:
    """Load the organiser state from a JSON file.

    Args:
        state_file_path (Path | None): Path to state file. If None, uses default.

    Returns:
        dict: The loaded state or empty dict if file doesn't exist or error occurs.
    """
    if state_file_path is None:
        state_file_path = state_file

    if state_file_path.exists():
        try:
            with open(state_file_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load state from {state_file_path}: {e}")
            return {}
    return {}


def _save_state(state: dict, state_file_path: Optional[Path] = None) -> None:
    """Save the organiser state to a JSON file.

    Args:
        state (dict): The state to save.
        state_file_path (Path | None): Path to state file. If None, uses default.
    """
    if state_file_path is None:
        state_file_path = state_file

    try:
        with open(state_file_path, "w") as f:
            json.dump(state, f)
    except (OSError, TypeError) as e:
        logger.error(f"Failed to save state to {state_file_path}: {e}")


def _log_move(src: Path, dest: Path, undo_log_path: Optional[Path] = None) -> None:
    """Log a file move operation.

    Args:
        src (Path): Source file path.
        dest (Path): Destination file path.
        undo_log_path (Path | None): Path to undo log file. If None, uses default.
    """
    if undo_log_path is None:
        undo_log_path = undo_log

    try:
        with open(undo_log_path, "a") as f:
            f.write(f"{src},{dest}\n")
    except (OSError, TypeError) as e:
        logger.error(f"Failed to log move for {src} to {dest}: {e}")


def scan_directory(source_dir: str) -> dict:
    """Scan the directory for photos and return a summary, including list of photo files.

    Args:
        source_dir (str): The source directory to scan.

    Returns:
        dict: A summary of the scan results
    """
    source = Path(source_dir)

    _validate_directories(source)

    logger.debug(f"Scanning directory: {source}")

    photo_files = []
    other_count = 0
    inaccessible_count = 0

    def _scan(dir: Path) -> None:
        nonlocal other_count, inaccessible_count
        try:
            with os.scandir(dir) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            if entry.name.startswith("."):
                                continue
                            if entry.name.lower().endswith(SUPPORTED_FORMATS):
                                photo_files.append(Path(entry.path))
                            else:
                                other_count += 1
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Error processing file {entry.path}: {e}")
                            inaccessible_count += 1
                    elif entry.is_dir():
                        _scan(Path(entry.path))

        except (OSError, PermissionError) as e:
            logger.error(f"Error scanning directory {dir}: {e}")
            inaccessible_count += 1

    try:
        _scan(source)

    except Exception as e:
        logger.error(f"Error scanning directory {source_dir}: {e}")
        raise PhotoOrganisationError(
            f"Error scanning directory {source_dir}: {e}"
        ) from e

    logger.debug(
        f"Found {len(photo_files)} photos, {other_count} other files, and {inaccessible_count} inaccessible files."
    )

    return {
        "photos_count": len(photo_files),
        "other_count": other_count,
        "total_files": len(photo_files) + other_count + inaccessible_count,
        "photo_files": photo_files,
        "inaccessible_count": inaccessible_count,
    }


def organise_photos(
    source_dir: str,
    dest_dir: str,
    state_file: Optional[Path] = None,
    undo_log: Optional[Path] = None,
    photo_files: list[Path] | None = None,
) -> dict:
    """Organise photos from source directory to destination directory based on metadata.

    Args:
        source_dir (str): The source directory containing photos.
        dest_dir (str): The destination directory to organise photos into.
        state_file (Path | None): Path to state file. If None, uses default.
        undo_log (Path | None): Path to undo log file. If None, uses default.
        photo_files (list[Path] | None): List of photo files to organise. If None, scans source_dir.

    Returns:
        dict: Summary of the organisation process.
    """
    source = Path(source_dir)
    dest = Path(dest_dir)

    _validate_directories(source, dest)

    if photo_files is None:
        files_to_process = scan_directory(source_dir)["photo_files"]
    else:
        files_to_process = photo_files

    staging_dir = dest / STAGING_DIR
    try:
        staging_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to create staging directory: {staging_dir}: {e}")
        raise PhotoOrganisationError(
            f"Failed to create staging directory: {staging_dir}"
        ) from e

    logger.debug(f"Starting photo organisation from {source} to {dest}")

    state = _load_state(state_file)
    processed = 0
    failed = []

    for file_path in files_to_process:
        if not (file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS):
            continue

        if file_path.name in state and state[file_path.name] == "processed":
            logger.debug(f"Skipping already processed file: {file_path.name}")
            continue

        try:
            logger.debug(f"Processing file: {file_path.name}")
            image_info = get_image_info(file_path)
            date = image_info.timestamp
            location = image_info.location

            if not date:
                logger.warning(f"Missing date for {file_path.name}, skipping.")
                failed.append((file_path.name, "Missing date metadata"))
                state[file_path.name] = "failed"
                _save_state(state, state_file)
                continue

            year = date.strftime("%Y")
            month = date.strftime("%m")
            day = date.strftime("%d")

            if location and location != "Unknown Location":
                target_dir = dest / year / month / day / location
            elif not location or location == "Unknown Location":
                target_dir = dest / year / month / day

            target_dir.mkdir(parents=True, exist_ok=True)
            unique_filename = _get_unique_filename(target_dir, file_path.name)

            staged_path = staging_dir / unique_filename
            try:
                shutil.move(str(file_path), staged_path)
            except Exception as e:
                logger.error(f"Failed to move {file_path.name} to {staged_path}: {e}")
                failed.append((file_path.name, f"Staging move failed: {e}"))
                state[file_path.name] = "failed"
                _save_state(state, state_file)
                continue

            final_path = target_dir / unique_filename
            try:
                shutil.move(str(staged_path), final_path)
                logger.debug(f"Moved {file_path.name} to {final_path}")
                _log_move(file_path, final_path, undo_log)
                state[file_path.name] = "processed"
                _save_state(state, state_file)
                processed += 1
            except Exception as e:
                logger.error(
                    f"Failed to move {file_path.name} from staging to final: {e}"
                )
                failed.append((file_path.name, f"Final move failed: {e}"))
                state[file_path.name] = "failed"
                _save_state(state, state_file)
                try:
                    shutil.move(str(staged_path), file_path)
                except Exception as e2:
                    logger.error(
                        f"Failed to restore {file_path.name} from staging: {e2}"
                    )

        except PhotoMetadataError as e:
            logger.error(f"Metadata error for {file_path.name}: {e}")
            failed.append((file_path.name, str(e)))
            state[file_path.name] = "failed"
            _save_state(state, state_file)
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            failed.append((file_path.name, str(e)))
            state[file_path.name] = "failed"
            _save_state(state, state_file)

    summary = {
        "processed": processed,
        "failed": failed,
        "total": processed + len(failed),
    }

    logger.info(
        f"Photo organisation completed: {processed} processed, {len(failed)} failed."
    )
    if failed:
        for fname, reason in failed:
            logger.warning(f"Failed: {fname} - Reason: {reason}")

    return summary


def _remove_empty_dirs(root: Path) -> None:
    """Remove empty directories recursively up to stop (non-inclusive)

    Args:
        path (Path): The directory path to clean
        stop (Path): The directory path to stop at (non-inclusive)
    """
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        path = Path(dirpath)
        for file in path.iterdir():
            if file.is_file() and file.name.startswith("."):
                try:
                    file.unlink()
                    logger.debug(f"Removed hidden file: {file}")
                except Exception as e:
                    logger.debug(f"Could not remove hidden file {file}: {e}")

        try:
            if not any(path.iterdir()):
                path.rmdir()
                logger.debug(f"Removed empty directory: {path}")
        except OSError as e:
            logger.debug(f"Could not remove directory {path}: {e}")


def undo_organisation(undo_log_path: Optional[Path] = None) -> bool:
    """Undo the last organisation operation.

    Args:
        undo_log_path (Path | None): Path to undo log file. If None, uses default.
    """
    if undo_log_path is None:
        undo_log_path = undo_log

    if not undo_log_path.exists():
        logger.warning("No undo log found. Nothing to undo.")
        return False

    try:
        with open(undo_log) as f:
            moves = [line.strip().split(",", 1) for line in f if "," in line]

        dest_paths = [Path(dest) for _, dest in moves]
        if not dest_paths:
            logger.warning("No valid destination paths found for undo.")
            return False

        main_dest_root = os.path.commonpath([p.parent for p in dest_paths])

        for src, dest in reversed(moves):
            try:
                if Path(dest).exists():
                    Path(src).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(dest, src)
                    logger.debug(f"Restored {dest} to {src}")
                else:
                    logger.warning(f"Destination file {dest} does not exist for undo")

            except Exception as e:
                logger.error(f"Failed to restore {dest} to {src}: {e}")
                raise PhotoOrganisationError(f"Failed to restore {dest} to {src}: {e}")

        # Cleanup created directories & staging area
        staging_dir = Path(main_dest_root) / STAGING_DIR
        try:
            staging_dir.rmdir()
            logger.debug(f"Removed empty directory: {staging_dir}")
        except OSError:
            logger.debug(f"Directory not empty or missing: {staging_dir}")

        _remove_empty_dirs(Path(main_dest_root))

        # Clear the state file
        state_file_path = state_file
        try:
            with open(state_file_path, "w") as f:
                json.dump({}, f)
            logger.debug("Cleared state file after undo operation")
        except Exception as e:
            logger.warning(f"Failed to clear state file after undo: {e}")

        # Clear the undo log
        try:
            with open(undo_log_path, "w") as f:
                f.write("")
            logger.debug("Cleared undo log after undo operation")
        except Exception as e:
            logger.warning(f"Failed to clear undo log after undo: {e}")

        logger.info("Undo operation completed.")
        return True

    except Exception as e:
        logger.error(f"Error during undo operation: {e}")
        raise PhotoOrganisationError(f"Error during undo operation: {e}")


def _validate_directories(source: Path, dest: Optional[Path] = None) -> None:
    """Validate source and destination directories.

    Args:
        source (Path): The source directory.
        dest (Path | None): The destination directory. If None, only source is validated.

    Raises:
        InvalidDirectoryError: If either directory is invalid or inaccessible.
    """
    if not source.exists():
        raise InvalidDirectoryError(f"Source directory does not exist: {source}")
    if not source.is_dir():
        raise InvalidDirectoryError(f"Source path is not a directory: {source}")
    if not os.access(source, os.R_OK):
        raise InvalidDirectoryError(f"Source directory is not readable: {source}")

    if dest is not None:
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise InvalidDirectoryError(
                f"Failed to create destination directory: {dest}"
            ) from e

        logger.debug(f"Validated directories - source: {source}, destination: {dest}")
    else:
        logger.debug(f"Validated source directory: {source}")


def _get_unique_filename(directory, filename) -> str:
    """Generate a unique filename in the specified directory.

    Args:
        directory (str): The target directory.
        filename (str): The original filename.

    Returns:
        str: A unique filename.
    """
    try:
        path = Path(directory) / filename
        if not path.exists():
            return filename

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1

        while (Path(directory) / f"{stem}_{counter}{suffix}").exists():
            counter += 1

        unique_name = f"{stem}_{counter}{suffix}"
        logger.debug(f"Generated unique filename: {unique_name} in {directory}")

        return unique_name
    except Exception as e:
        logger.error(
            f"Error generating unique filename for {filename} in {directory}: {e}"
        )
        raise PhotoOrganisationError(
            f"Error generating unique filename for {filename} in {directory}"
        ) from e
