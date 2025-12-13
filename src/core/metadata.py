"""Module for extracting metadata from image files."""

from datetime import datetime

import exifread
import reverse_geocoder as rg

from src.utils.constants import SUPPORTED_FORMATS
from src.utils.errors import InvalidPhotoFormatError, PhotoMetadataError
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_image_info(file_path):
    """Get comprehensive image information including date taken and location.

    Args:
        file_path (str): The path to the image file.

    Returns:
        dict: A dictionary containing date taken and location string.
    """
    metadata = _get_image_metadata(file_path)
    date_taken = _get_date_taken(metadata, file_path)
    location = _get_location(metadata, file_path)
    location_string = _convert_to_location_string(location, file_path)
    return {"date_taken": date_taken, "location": location_string}


def _get_image_metadata(file_path):
    """Extract metadata from an image file.

    Args:
        file_path (str): The path to the image file.

    Returns:
        dict: A dictionary containing the extracted metadata.
    """
    metadata = {}
    if not file_path.lower().endswith(SUPPORTED_FORMATS):
        logger.warning(f"Unsupported file format: {file_path}")
        raise InvalidPhotoFormatError(f"Unsupported file format: {file_path}")
    try:
        with open(file_path, "rb") as f:
            tags = exifread.process_file(f)
            for tag in tags.keys():
                metadata[tag] = str(tags[tag])
        logger.debug(f"Extracted metadata from {file_path}: {metadata}")
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise PhotoMetadataError(f"File not found: {file_path}")
    except (IOError, OSError) as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise PhotoMetadataError(f"Error reading file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {e}")
        raise PhotoMetadataError(f"Unexpected error processing file {file_path}: {e}")
    return metadata


def _get_date_taken(metadata, file_path):
    """Extract the date the photo was taken from metadata.

    Args:
        metadata (dict): The metadata dictionary.
        file_path (str): The path to the image file.

    Returns:
        datetime or None: The date the photo was taken, or None if not found.
    """
    date_str = metadata.get("EXIF DateTimeOriginal") or metadata.get("Image DateTime")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            logger.warning(f"Invalid date format in {file_path}: {date_str}")
            return None
    return None


def _get_location(metadata, file_path):
    """Extract GPS location from metadata.

    Args:
        metadata (dict): The metadata dictionary.

    Returns:
        tuple or None: A tuple of (latitude, longitude) or None if not found.
    """
    try:
        if "GPS GPSLatitude" not in metadata or "GPS GPSLongitude" not in metadata:
            logger.debug(f"No GPS metadata found in {file_path}")
            return None

        lat_ref = metadata.get("GPS GPSLatitudeRef", "N")
        lon_ref = metadata.get("GPS GPSLongitudeRef", "E")

        lat_data = metadata["GPS GPSLatitude"]
        lon_data = metadata["GPS GPSLongitude"]

        if not hasattr(lat_data, "values") or not hasattr(lon_data, "values"):
            logger.warning(f"Invalid GPS data format in {file_path}")
            return None

        lat_values = [float(x.num) / float(x.den) for x in lat_data.values]
        lon_values = [float(x.num) / float(x.den) for x in lon_data.values]

        if len(lat_values) < 3 or len(lon_values) < 3:
            logger.warning(f"Incomplete GPS data in {file_path}")
            return None

        lat = lat_values[0] + lat_values[1] / 60 + lat_values[2] / 3600
        lon = lon_values[0] + lon_values[1] / 60 + lon_values[2] / 3600

        if lat_ref == "S":
            lat = -lat
        if lon_ref == "W":
            lon = -lon

        logger.debug(f"Extracted GPS location from {file_path}: {lat}, {lon}")
        return lat, lon
    except (AttributeError, IndexError, TypeError, ZeroDivisionError):
        logger.warning(f"Error extracting GPS data from {file_path}")
        return None


def _convert_to_location_string(location, file_path):
    """Convert a location tuple to a string.

    Args:
        location (tuple): A tuple of (latitude, longitude).

    Returns:
        str: A string representation of the location.
    """
    if location is None:
        return "Unknown Location"
    try:
        results = rg.search(location)
        if results:
            place = results[0]
            logger.debug(f"Location resolved for {file_path}: {place}")
            return f"{place['name']}, {place['admin1']}, {place['cc']}"
        logger.warning(f"No location found for coordinates in {file_path}: {location}")
        return "Unknown Location"
    except Exception as e:
        logger.warning(f"Error converting location to string for {file_path}: {e}")
        return "Unknown Location"
