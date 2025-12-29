"""Module for extracting metadata from image files."""

from datetime import datetime
from pathlib import Path

from runtime.paths import db_path
from photidy import extract_metadata, reverse_geocode
from src.core.image_info import ImageInfo
from src.utils.constants import SUPPORTED_FORMATS
from src.utils.errors import InvalidPhotoFormatError, PhotoMetadataError
from src.utils.logger import get_logger

logger = get_logger(__name__)


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
    if not file_path.lower().endswith(SUPPORTED_FORMATS):
        logger.warning(f"Unsupported file format: {file_path}")
        raise InvalidPhotoFormatError(f"Unsupported file format: {file_path}")

    try:
        metadata = extract_metadata(file_path)

        if metadata is None:
            logger.error(f"Failed to extract metadata from {file_path}")
            raise PhotoMetadataError(f"Failed to extract metadata from {file_path}")

        dt = None
        if metadata.timestamp is not None:
            dt = datetime.fromisoformat(metadata.timestamp)
            logger.info(f"Extracted date info from {file_path}")
        else:
            logger.warning(f"No timestamp found in metadata for {file_path}")

        place_name = "Unknown Location"
        if metadata.lat is not None and metadata.lon is not None:
            place = reverse_geocode(metadata.lat, metadata.lon, str(db_path()))
            if place is not None:
                place_name = place.name
                logger.info(f"Extracted location info from {file_path}")
            else:
                logger.warning(f"Reverse geocoding failed for {file_path}")
        else:
            logger.warning(f"No location found in metadata for {file_path}")

        return ImageInfo(
            path=file_path,
            timestamp=dt,
            lat=metadata.lat,
            lon=metadata.lon,
            location=place_name,
        )

    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}")
        raise PhotoMetadataError(f"Unexpected error processing {file_path}: {e}")
