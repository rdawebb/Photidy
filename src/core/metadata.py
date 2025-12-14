"""Module for extracting metadata from image files."""

from photo_meta import extract_metadata

from src.utils.constants import SUPPORTED_FORMATS
from src.utils.errors import InvalidPhotoFormatError, PhotoMetadataError
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_image_info(file_path):
    """Extract metadata from an image file via Rust bridge

    Args:
        file_path (str): Path to the image file

    Returns:
        dict: Extracted metadata including date taken and location

    Raises:
        InvalidPhotoFormatError: If the file format is unsupported
        PhotoMetadataError: If metadata extraction fails
    """
    if not file_path.lower().endswith(SUPPORTED_FORMATS):
        logger.warning(f"Unsupported file format: {file_path}")
        raise InvalidPhotoFormatError(f"Unsupported file format: {file_path}")

    try:
        result = extract_metadata(file_path)

        if result is None:
            logger.error(f"Failed to extract metadata from: {file_path}")
            raise PhotoMetadataError(f"Failed to extract metadata from: {file_path}")

        if result.get("date_taken"):
            logger.debug(
                f"Extracted date info from {file_path}: {result['date_taken']}"
            )
        else:
            logger.warning(f"No date info found for {file_path}")

        if result.get("location") != "Unknown Location":
            logger.debug(
                f"Extracted location info from {file_path}: {result['location']}"
            )
        else:
            logger.warning(f"No location info found for {file_path}")

        logger.debug(f"Extracted metadata for {file_path}: {result}")
        return result

    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}")
        raise PhotoMetadataError(f"Unexpected error processing {file_path}: {e}")
