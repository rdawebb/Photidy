"""Organiser module for organising photos based on metadata."""

import json
import os
import shutil
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Optional

from src.core.image_info import ImageInfo
from src.utils.constants import SUPPORTED_FORMATS
from src.utils.errors import (
    InvalidDirectoryError,
    PhotoMetadataError,
    PhotoOrganisationError,
)
from src.utils.logger import get_logger
from src.utils.paths import STATE_FILE, UNDO_LOG

from .metadata import get_image_info

logger: Logger = get_logger(name=__name__)

STAGING_DIR = ".staging"

state_file: Path = STATE_FILE
undo_log: Path = UNDO_LOG


def _load_state(state_file_path: Optional[Path] = None) -> dict:
    """Load the organiser state from a JSON file

    Args:
        state_file_path (Path | None): Path to state file. If None, uses default

    Returns:
        dict: The loaded state or empty dict if file doesn't exist or error occurs
    """
    if state_file_path is None:
        state_file_path: Path = state_file

    if state_file_path.exists():
        try:
            with open(file=state_file_path) as f:
                return json.load(fp=f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(msg=f"Failed to load state from {state_file_path}: {e}")
            return {}
    return {}


def _save_state(state: dict, state_file_path: Optional[Path] = None) -> None:
    """Save the organiser state to a JSON file

    Args:
        state (dict): The state to save
        state_file_path (Path | None): Path to state file. If None, uses default
    """
    if state_file_path is None:
        state_file_path = state_file

    tmp_path = state_file_path.with_suffix(".tmp")

    try:
        with open(tmp_path, "w") as f:
            json.dump(state, f)
        os.replace(tmp_path, state_file_path)  # atomic on POSIX and Windows

    except (OSError, TypeError) as e:
        logger.error(f"Failed to save state: {e}")
        tmp_path.unlink(missing_ok=True)


def _log_move(src: Path, dest: Path, undo_log_path: Optional[Path] = None) -> None:
    """Log a file move operation

    Args:
        src (Path): Source file path
        dest (Path): Destination file path
        undo_log_path (Path | None): Path to undo log file. If None, uses default
    """
    if undo_log_path is None:
        undo_log_path: Path = undo_log

    try:
        with open(file=undo_log_path, mode="a") as f:
            f.write(f"{src},{dest}\n")
    except (OSError, TypeError) as e:
        logger.error(msg=f"Failed to log move for {src} to {dest}: {e}")


def scan_directory(source_dir: str, progress_callback=None) -> dict:
    """Scan the directory for photos and return a summary, including list of photo files

    Args:
        source_dir (str): The source directory to scan
        progress_callback (callable | None): Optional callback for progress updates

    Returns:
        dict: A summary of the scan results
    """
    import math

    source = Path(source_dir)

    _validate_directories(source)

    logger.debug(msg=f"Scanning directory: {source}")

    image_files: list[Path] = []
    other_count: int = 0
    inaccessible_count: int = 0
    count: int = 0  # For UI reporting

    def _scan(dir: Path) -> None:
        nonlocal other_count, inaccessible_count, count
        try:
            with os.scandir(path=dir) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            if entry.name.startswith("."):
                                continue
                            if entry.name.lower().endswith(SUPPORTED_FORMATS):
                                image_files.append(Path(entry.path))
                                count += 1
                                if progress_callback:
                                    progress_callback(count, entry.name)
                            else:
                                other_count += 1
                        except (OSError, PermissionError) as e:
                            logger.warning(
                                msg=f"Error processing file {entry.path}: {e}"
                            )
                            inaccessible_count += 1
                    elif entry.is_dir():
                        _scan(dir=Path(entry.path))

        except (OSError, PermissionError) as e:
            logger.error(msg=f"Error scanning directory {dir}: {e}")
            inaccessible_count += 1

    try:
        _scan(dir=source)

    except Exception as e:
        logger.error(msg=f"Error scanning directory {source_dir}: {e}")
        raise PhotoOrganisationError(
            f"Error scanning directory {source_dir}: {e}"
        ) from e

    logger.debug(
        msg=f"Found {len(image_files)} photos, {other_count} other files, and {inaccessible_count} inaccessible files."
    )

    estimated_time: int = math.ceil(
        len(image_files) * 0.005
    )  # seconds per image estimate (placeholder)

    return {
        "images_count": len(image_files),
        "other_count": other_count,
        "total_files": len(image_files) + other_count + inaccessible_count,
        "image_files": image_files,
        "inaccessible_count": inaccessible_count,
        "estimated_time": f"{estimated_time} s",
    }


def organise_photos(
    source_dir: str,
    dest_dir: str,
    state_file: Optional[Path] = None,
    undo_log: Optional[Path] = None,
    image_files: list[Path] | None = None,
    progress_callback=None,
) -> dict:
    """Organise photos from source directory to destination directory based on metadata

    Args:
        source_dir (str): The source directory containing photos
        dest_dir (str): The destination directory to organise photos into
        state_file (Path | None): Path to state file - if None, uses default
        undo_log (Path | None): Path to undo log file - if None, uses default
        image_files (list[Path] | None): List of photo files to organise - if None, scans source_dir

    Returns:
        dict: Summary of the organisation process
    """
    source = Path(source_dir)
    dest = Path(dest_dir)

    _validate_directories(source, dest)

    if image_files is None:
        files_to_process: list[Path] = scan_directory(source_dir)["image_files"]
    else:
        files_to_process: list[Path] = image_files

    staging_dir: Path = dest / STAGING_DIR
    try:
        staging_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        logger.error(msg=f"Failed to create staging directory: {staging_dir}: {e}")
        raise PhotoOrganisationError(
            f"Failed to create staging directory: {staging_dir}"
        ) from e

    logger.debug(msg=f"Starting photo organisation from {source} to {dest}")

    state: dict[str, str] = _load_state(state_file_path=state_file)
    processed: int = 0
    failed: list[tuple[str, str]] = []

    for file_path in files_to_process:
        if not file_path.is_file():
            continue

        if file_path.name in state and state[file_path.name] == "processed":
            logger.debug(msg=f"Skipping already processed file: {file_path.name}")
            continue

        try:
            logger.debug(msg=f"Processing file: {file_path.name}")
            image_info: ImageInfo = get_image_info(file_path)
            date: datetime | None = image_info.timestamp
            location: str | None = image_info.location

            if not date:
                logger.warning(msg=f"Missing date for {file_path.name}, skipping.")
                failed.append((file_path.name, "Missing date metadata"))
                state[file_path.name] = "failed"
                _save_state(state, state_file_path=state_file)
                continue

            year: str = date.strftime("%Y")
            month: str = date.strftime("%m")
            day: str = date.strftime("%d")

            if location and location != "Unknown Location":
                target_dir: Path = dest / year / month / day / location
            elif not location or location == "Unknown Location":
                target_dir: Path = dest / year / month / day

            target_dir.mkdir(parents=True, exist_ok=True)
            unique_filename: str = _get_unique_filename(
                directory=target_dir, filename=file_path.name
            )

            staged_path: Path = staging_dir / unique_filename
            try:
                shutil.move(src=str(object=file_path), dst=staged_path)
            except Exception as e:
                logger.error(
                    msg=f"Failed to move {file_path.name} to {staged_path}: {e}"
                )
                failed.append((file_path.name, f"Staging move failed: {e}"))
                state[file_path.name] = "failed"
                _save_state(state, state_file_path=state_file)
                continue

            final_path: Path = target_dir / unique_filename
            try:
                shutil.move(src=str(object=staged_path), dst=final_path)
                logger.debug(msg=f"Moved {file_path.name} to {final_path}")
                _log_move(src=file_path, dest=final_path, undo_log_path=undo_log)
                state[file_path.name] = "processed"
                _save_state(state, state_file_path=state_file)
                processed += 1
                if progress_callback:
                    progress_callback(processed, file_path.name)

            except Exception as e:
                logger.error(
                    msg=f"Failed to move {file_path.name} from staging to final: {e}"
                )
                failed.append((file_path.name, f"Final move failed: {e}"))
                state[file_path.name] = "failed"
                _save_state(state, state_file_path=state_file)
                try:
                    shutil.move(src=str(object=staged_path), dst=file_path)
                except Exception as e2:
                    logger.error(
                        msg=f"Failed to restore {file_path.name} from staging: {e2}"
                    )

        except PhotoMetadataError as e:
            logger.error(msg=f"Metadata error for {file_path.name}: {e}")
            failed.append((file_path.name, str(object=e)))
            state[file_path.name] = "failed"
            _save_state(state, state_file_path=state_file)
        except Exception as e:
            logger.error(msg=f"Failed to process {file_path.name}: {e}")
            failed.append((file_path.name, str(object=e)))
            state[file_path.name] = "failed"
            _save_state(state, state_file_path=state_file)

    try:
        staging_dir.rmdir()
        logger.info(msg=f"Staging directory removed: {staging_dir}")
    except OSError as e:
        logger.error(msg=f"Failed to remove staging directory: {e}")
        pass

    summary: dict[str, int | list[tuple[str, str]]] = {
        "processed": processed,
        "failed": failed,
        "total": processed + len(failed),
    }

    logger.info(
        msg=f"Photo organisation completed: {processed} processed, {len(failed)} failed."
    )
    if failed:
        for fname, reason in failed:
            logger.warning(msg=f"Failed: {fname} - Reason: {reason}")

    return summary


def _remove_empty_dirs(root: Path) -> None:
    """Remove empty directories recursively

    Args:
        path (Path): The directory path to clean
    """
    for dirpath, _, _ in os.walk(top=root, topdown=False):
        path = Path(dirpath)
        for file in path.iterdir():
            if file.is_file() and file.name.startswith("."):
                try:
                    file.unlink()
                    logger.debug(msg=f"Removed hidden file: {file}")
                except Exception as e:
                    logger.debug(msg=f"Could not remove hidden file {file}: {e}")

        try:
            if not any(path.iterdir()):
                path.rmdir()
                logger.debug(msg=f"Removed empty directory: {path}")
        except OSError as e:
            logger.debug(msg=f"Could not remove directory {path}: {e}")


def undo_organisation(undo_log_path: Optional[Path] = None) -> bool:
    """Undo the last organisation operation

    Args:
        undo_log_path (Path | None): Path to undo log file - if None, uses default
    """
    if undo_log_path is None:
        undo_log_path: Path = undo_log

    if not undo_log_path.exists():
        logger.warning(msg="No undo log found. Nothing to undo.")
        return False

    try:
        with open(file=undo_log_path) as f:
            moves: list[list[str]] = [
                line.strip().split(sep=",", maxsplit=1) for line in f if "," in line
            ]

        dest_paths: list[Path] = [Path(dest) for _, dest in moves]
        if not dest_paths:
            logger.warning(msg="No valid destination paths found for undo.")
            return False

        main_dest_root: str = os.path.commonpath(paths=[p.parent for p in dest_paths])

        for src, dest in reversed(moves):
            try:
                if Path(dest).exists():
                    Path(src).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(src=dest, dst=src)
                    logger.debug(msg=f"Restored {dest} to {src}")
                else:
                    logger.warning(
                        msg=f"Destination file {dest} does not exist for undo"
                    )

            except Exception as e:
                logger.error(msg=f"Failed to restore {dest} to {src}: {e}")
                raise PhotoOrganisationError(f"Failed to restore {dest} to {src}: {e}")

        # Cleanup created directories & staging area
        staging_dir: Path = Path(main_dest_root) / STAGING_DIR
        try:
            staging_dir.rmdir()
            logger.debug(msg=f"Removed empty directory: {staging_dir}")
        except OSError:
            logger.debug(msg=f"Directory not empty or missing: {staging_dir}")

        _remove_empty_dirs(root=Path(main_dest_root))

        # Clear the state file
        state_file_path: Path = state_file
        try:
            with open(file=state_file_path, mode="w") as f:
                json.dump(obj={}, fp=f)
            logger.debug(msg="Cleared state file after undo operation")
        except Exception as e:
            logger.warning(msg=f"Failed to clear state file after undo: {e}")

        # Clear the undo log
        try:
            with open(file=undo_log_path, mode="w") as f:
                f.write("")
            logger.debug(msg="Cleared undo log after undo operation")
        except Exception as e:
            logger.warning(msg=f"Failed to clear undo log after undo: {e}")

        logger.info(msg="Undo operation completed.")
        return True

    except Exception as e:
        logger.error(msg=f"Error during undo operation: {e}")
        raise PhotoOrganisationError(f"Error during undo operation: {e}")


def _validate_directories(source: Path, dest: Optional[Path] = None) -> None:
    """Validate source and destination directories

    Args:
        source (Path): The source directory
        dest (Path | None): The destination directory - if None, only source is validated

    Raises:
        InvalidDirectoryError: If either directory is invalid or inaccessible
    """
    if not source.exists():
        raise InvalidDirectoryError(f"Source directory does not exist: {source}")
    if not source.is_dir():
        raise InvalidDirectoryError(f"Source path is not a directory: {source}")
    if not os.access(path=source, mode=os.R_OK):
        raise InvalidDirectoryError(f"Source directory is not readable: {source}")

    if dest is not None:
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise InvalidDirectoryError(
                f"Failed to create destination directory: {dest}"
            ) from e

        logger.debug(
            msg=f"Validated directories - source: {source}, destination: {dest}"
        )
    else:
        logger.debug(msg=f"Validated source directory: {source}")


def _get_unique_filename(directory, filename) -> str:
    """Generate a unique filename in the specified directory

    Args:
        directory (str): The target directory
        filename (str): The original filename

    Returns:
        str: A unique filename
    """
    try:
        path: Path = Path(directory) / filename
        if not path.exists():
            return filename

        stem: str = Path(filename).stem
        suffix: str = Path(filename).suffix
        counter: int = 1

        while (Path(directory) / f"{stem}_{counter}{suffix}").exists():
            counter += 1

        unique_name: str = f"{stem}_{counter}{suffix}"
        logger.debug(msg=f"Generated unique filename: {unique_name} in {directory}")

        return unique_name
    except Exception as e:
        logger.error(
            msg=f"Error generating unique filename for {filename} in {directory}: {e}"
        )
        raise PhotoOrganisationError(
            f"Error generating unique filename for {filename} in {directory}"
        ) from e
