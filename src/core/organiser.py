"""Organiser module for organising photos based on metadata."""

import os
import shutil
from pathlib import Path

from src.utils.constants import SUPPORTED_FORMATS
from src.utils.errors import (
    InvalidDirectoryError,
    PhotoMetadataError,
    PhotoOrganisationError,
)
from src.utils.logger import get_logger

from .metadata import get_image_info

logger = get_logger(__name__)


def organise_photos(source_dir, dest_dir) -> dict:
    """Organise photos from source directory to destination directory based on metadata.

    Args:
        source_dir (str): The source directory containing photos.
        dest_dir (str): The destination directory to organise photos into.

    Returns:
        dict: Summary of the organisation process.
    """
    source = Path(source_dir)
    dest = Path(dest_dir)

    _validate_directories(source, dest)

    logger.info(f"Starting photo organisation from {source} to {dest}")

    processed = 0
    failed = []

    for file_path in source.glob("*"):
        try:
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
                logger.debug(f"Processing file: {file_path.name}")

                image_info = get_image_info(str(file_path))
                date = image_info.get("date_taken")
                location = image_info.get("location")

                if not date:
                    logger.warning(
                        f"Missing date metadata for {file_path.name}. Skipping file."
                    )
                    failed.append((file_path.name, "Missing date metadata"))
                    continue

                year = date.strftime("%Y")
                month = date.strftime("%m")
                day = date.strftime("%d")

                if location and location != "Unknown":
                    target_dir = dest / year / month / day / location
                else:
                    target_dir = dest / year / month / day

                target_dir.mkdir(parents=True, exist_ok=True)

                unique_filename = _get_unique_filename(target_dir, file_path.name)

                shutil.move(str(file_path), target_dir / unique_filename)
                logger.debug(
                    f"Moved {file_path.name} to {target_dir / unique_filename}"
                )
                processed += 1

        except PhotoMetadataError as e:
            logger.error(f"Metadata error for {file_path.name}: {e}")
            failed.append((file_path.name, str(e)))
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            failed.append((file_path.name, str(e)))

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


def _validate_directories(source, dest) -> None:
    """Validate source and destination directories.

    Args:
        source (Path): The source directory.
        dest (Path): The destination directory.

    Raises:
        InvalidDirectoryError: If either directory is invalid or inaccessible.
    """
    if not source.exists():
        raise InvalidDirectoryError(f"Source directory does not exist: {source}")
    if not source.is_dir():
        raise InvalidDirectoryError(f"Source path is not a directory: {source}")
    if not os.access(source, os.R_OK):
        raise InvalidDirectoryError(f"Source directory is not readable: {source}")

    try:
        dest.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise InvalidDirectoryError(
            f"Failed to create destination directory: {dest}"
        ) from e

    logger.debug(f"Validated directories - source: {source}, destination: {dest}")


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
