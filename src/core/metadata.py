"""Module for extracting metadata from image files."""

from datetime import datetime
from logging import Logger
from pathlib import Path

from _photidy import extract_metadata, reverse_geocode  # type: ignore

from runtime.paths import db_path
from src.core.image_info import ImageInfo
from src.utils.constants import SUPPORTED_FORMATS
from src.utils.errors import InvalidPhotoFormatError, PhotoMetadataError
from src.utils.logger import get_logger

logger: Logger = get_logger(name=__name__)


def get_image_info(file_path: Path) -> ImageInfo:
    """Extract metadata from an image file via Rust bridge

    Args:
        file_path (Path): Path to the image file

    Returns:
        ImageInfo: Extracted metadata including date taken and location

    Raises:
        InvalidPhotoFormatError: If the file format is unsupported
        PhotoMetadataError: If metadata extraction fails
    """
    if not str(object=file_path).lower().endswith(SUPPORTED_FORMATS):
        logger.warning(f"Unsupported file format: {file_path}")
        raise InvalidPhotoFormatError(f"Unsupported file format: {file_path}")

    try:
        metadata = extract_metadata(str(object=file_path))

        if metadata is None:
            logger.error(msg=f"Failed to extract metadata from {file_path}")
            raise PhotoMetadataError(f"Failed to extract metadata from {file_path}")

        dt = None
        if metadata.timestamp is not None:
            dt: datetime = datetime.fromisoformat(metadata.timestamp)
            logger.info(msg=f"Extracted date info from {file_path}")
        else:
            logger.warning(msg=f"No timestamp found in metadata for {file_path}")

        place_name = "Unknown Location"
        if metadata.lat is not None and metadata.lon is not None:
            db_file = str(object=db_path())
            logger.info(msg=f"Attempting reverse geocode with DB: {db_file}")

            db_file_path = Path(db_file)
            if not db_file_path.exists():
                logger.warning(
                    msg=f"Database file does not exist: {db_file}, skipping geocoding"
                )
            else:
                try:
                    place = reverse_geocode(metadata.lat, metadata.lon, db_file)
                    if place is not None:
                        place_name: str = place.name
                        logger.info(msg=f"Extracted location info from {file_path}")
                    else:
                        logger.warning(
                            msg=f"Reverse geocoding returned no match for {file_path}"
                        )
                except Exception as e:
                    logger.error(msg=f"Reverse geocoding failed for {file_path}: {e}")
                    raise PhotoMetadataError(
                        f"Unexpected error processing {file_path}: {e}"
                    ) from e
        else:
            logger.warning(msg=f"No location found in metadata for {file_path}")

        return ImageInfo(
            path=file_path,
            timestamp=dt,
            lat=metadata.lat,
            lon=metadata.lon,
            location=place_name,
        )

    except Exception as e:
        logger.error(msg=f"Unexpected error processing {file_path}: {e}")
        raise PhotoMetadataError(f"Unexpected error processing {file_path}: {e}")
