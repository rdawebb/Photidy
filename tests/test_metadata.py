"""Tests for metadata extraction in src/core/metadata.py"""

from datetime import datetime
from unittest.mock import Mock, mock_open, patch

import pytest

from src.core.metadata import (
    _convert_to_location_string,
    _get_date_taken,
    _get_image_metadata,
    _get_location,
    get_image_info,
)
from src.utils.errors import InvalidPhotoFormatError, PhotoMetadataError


class TestGetImageMetadata:
    """Test _get_image_metadata function."""

    def test_valid_image_file_with_exif(self, suppress_logging):
        """Test extracting metadata from a valid image file."""
        mock_tags = {
            "EXIF DateTimeOriginal": "2024:01:15 14:30:45",
            "Image Model": "Canon EOS",
        }
        with (
            patch("builtins.open", mock_open()),
            patch("exifread.process_file", return_value=mock_tags),
        ):
            metadata = _get_image_metadata("test.jpg")
            assert "EXIF DateTimeOriginal" in metadata
            assert metadata["EXIF DateTimeOriginal"] == "2024:01:15 14:30:45"

    def test_unsupported_file_format(self, suppress_logging):
        """Test that unsupported file format raises InvalidPhotoFormatError."""
        with pytest.raises(InvalidPhotoFormatError):
            _get_image_metadata("test.txt")

    def test_file_not_found(self, suppress_logging):
        """Test that FileNotFoundError raises PhotoMetadataError."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(PhotoMetadataError):
                _get_image_metadata("nonexistent.jpg")

    def test_io_error(self, suppress_logging):
        """Test that IOError raises PhotoMetadataError."""
        with patch("builtins.open", side_effect=IOError()):
            with pytest.raises(PhotoMetadataError):
                _get_image_metadata("test.jpg")

    def test_os_error(self, suppress_logging):
        """Test that OSError raises PhotoMetadataError."""
        with patch("builtins.open", side_effect=OSError()):
            with pytest.raises(PhotoMetadataError):
                _get_image_metadata("test.jpg")

    def test_general_exception(self, suppress_logging):
        """Test that general exceptions raise PhotoMetadataError."""
        with patch("builtins.open", side_effect=RuntimeError("Some error")):
            with pytest.raises(PhotoMetadataError):
                _get_image_metadata("test.jpg")

    def test_image_file_with_no_exif(self, suppress_logging):
        """Test extracting metadata from image with no EXIF data."""
        with (
            patch("builtins.open", mock_open()),
            patch("exifread.process_file", return_value={}),
        ):
            metadata = _get_image_metadata("test.jpg")
            assert metadata == {}

    def test_supported_formats(self, suppress_logging):
        """Test that various supported formats are accepted."""
        supported = [".jpg", ".jpeg", ".png", ".tiff", ".raw", ".cr2", ".heic"]
        for fmt in supported:
            with (
                patch("builtins.open", mock_open()),
                patch("exifread.process_file", return_value={}),
            ):
                # Should not raise
                metadata = _get_image_metadata(f"test{fmt}")
                assert isinstance(metadata, dict)


class TestGetDateTaken:
    """Test _get_date_taken function."""

    def test_valid_exif_datetime_original(self, suppress_logging):
        """Test extracting date from EXIF DateTimeOriginal."""
        metadata = {"EXIF DateTimeOriginal": "2024:01:15 14:30:45"}
        date = _get_date_taken(metadata, "test.jpg")
        assert date == datetime(2024, 1, 15, 14, 30, 45)

    def test_valid_image_datetime_fallback(self, suppress_logging):
        """Test extracting date from Image DateTime as fallback."""
        metadata = {"Image DateTime": "2024:06:20 10:15:30"}
        date = _get_date_taken(metadata, "test.jpg")
        assert date == datetime(2024, 6, 20, 10, 15, 30)

    def test_exif_datetime_takes_precedence(self, suppress_logging):
        """Test that EXIF DateTimeOriginal takes precedence over Image DateTime."""
        metadata = {
            "EXIF DateTimeOriginal": "2024:01:15 14:30:45",
            "Image DateTime": "2024:06:20 10:15:30",
        }
        date = _get_date_taken(metadata, "test.jpg")
        assert date == datetime(2024, 1, 15, 14, 30, 45)

    def test_invalid_date_format(self, suppress_logging):
        """Test that invalid date format returns None."""
        metadata = {"EXIF DateTimeOriginal": "invalid-date"}
        date = _get_date_taken(metadata, "test.jpg")
        assert date is None

    def test_missing_date_metadata(self, suppress_logging):
        """Test that missing date metadata returns None."""
        metadata = {}
        date = _get_date_taken(metadata, "test.jpg")
        assert date is None

    def test_both_datetime_fields_missing(self, suppress_logging):
        """Test that missing both datetime fields returns None."""
        metadata = {"Image Model": "Canon EOS"}
        date = _get_date_taken(metadata, "test.jpg")
        assert date is None

    def test_partial_datetime_string(self, suppress_logging):
        """Test with partial datetime string."""
        metadata = {"EXIF DateTimeOriginal": "2024:01:15"}
        date = _get_date_taken(metadata, "test.jpg")
        assert date is None


class TestGetLocation:
    """Test _get_location function."""

    def test_valid_gps_coordinates_north_east(self, suppress_logging):
        """Test extracting valid GPS coordinates (North, East)."""
        metadata = {
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLatitudeRef": "N",
            "GPS GPSLongitudeRef": "E",
        }
        location = _get_location(metadata, "test.jpg")
        assert location is not None
        lat, lon = location
        assert lat == pytest.approx(40.5, abs=0.01)
        assert lon == pytest.approx(74.0, abs=0.01)

    def test_gps_coordinates_south_latitude(self, suppress_logging):
        """Test GPS coordinates with South latitude (negative)."""
        metadata = {
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLatitudeRef": "S",
            "GPS GPSLongitudeRef": "E",
        }
        location = _get_location(metadata, "test.jpg")
        assert location is not None
        lat, lon = location
        assert lat == pytest.approx(-40.5, abs=0.01)
        assert lon == pytest.approx(74.0, abs=0.01)

    def test_gps_coordinates_west_longitude(self, suppress_logging):
        """Test GPS coordinates with West longitude (negative)."""
        metadata = {
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLatitudeRef": "N",
            "GPS GPSLongitudeRef": "W",
        }
        location = _get_location(metadata, "test.jpg")
        assert location is not None
        lat, lon = location
        assert lat == pytest.approx(40.5, abs=0.01)
        assert lon == pytest.approx(-74.0, abs=0.01)

    def test_gps_coordinates_with_seconds(self, suppress_logging):
        """Test GPS coordinates with seconds component."""
        metadata = {
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=1), Mock(num=36, den=1)]
            ),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLatitudeRef": "N",
            "GPS GPSLongitudeRef": "E",
        }
        location = _get_location(metadata, "test.jpg")
        assert location is not None
        lat, lon = location
        assert lat == pytest.approx(40.51, abs=0.01)

    def test_missing_gps_metadata(self, suppress_logging):
        """Test that missing GPS metadata returns None."""
        metadata = {}
        location = _get_location(metadata, "test.jpg")
        assert location is None

    def test_missing_gps_latitude(self, suppress_logging):
        """Test that missing GPS latitude returns None."""
        metadata = {
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
        }
        location = _get_location(metadata, "test.jpg")
        assert location is None

    def test_missing_gps_longitude(self, suppress_logging):
        """Test that missing GPS longitude returns None."""
        metadata = {
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=1), Mock(num=0, den=1)]
            ),
        }
        location = _get_location(metadata, "test.jpg")
        assert location is None

    def test_invalid_gps_data_format_no_values_attribute(self, suppress_logging):
        """Test that invalid GPS data format (no values) returns None."""
        metadata = {
            "GPS GPSLatitude": "invalid",
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
        }
        location = _get_location(metadata, "test.jpg")
        assert location is None

    def test_incomplete_gps_data_less_than_three_values(self, suppress_logging):
        """Test that incomplete GPS data returns None."""
        metadata = {
            "GPS GPSLatitude": Mock(values=[Mock(num=40, den=1)]),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
        }
        location = _get_location(metadata, "test.jpg")
        assert location is None

    def test_gps_data_attribute_error(self, suppress_logging):
        """Test that AttributeError in GPS data extraction returns None."""
        metadata = {
            "GPS GPSLatitude": Mock(side_effect=AttributeError()),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
        }
        location = _get_location(metadata, "test.jpg")
        assert location is None

    def test_gps_data_division_by_zero(self, suppress_logging):
        """Test that ZeroDivisionError in GPS calculation returns None."""
        metadata = {
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=0), Mock(num=0, den=1)]
            ),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
        }
        location = _get_location(metadata, "test.jpg")
        assert location is None


class TestConvertToLocationString:
    """Test _convert_to_location_string function."""

    def test_none_location_returns_unknown(self, suppress_logging):
        """Test that None location returns 'Unknown Location'."""
        result = _convert_to_location_string(None, "test.jpg")
        assert result == "Unknown Location"

    def test_valid_location_geocoding(self, suppress_logging):
        """Test converting valid coordinates to location string."""
        with patch("reverse_geocoder.search") as mock_search:
            mock_search.return_value = [
                {
                    "name": "New York",
                    "admin1": "New York",
                    "cc": "US",
                }
            ]
            result = _convert_to_location_string((40.7128, -74.0060), "test.jpg")
            assert result == "New York, New York, US"

    def test_geocoding_empty_results(self, suppress_logging):
        """Test that empty geocoding results return 'Unknown Location'."""
        with patch("reverse_geocoder.search") as mock_search:
            mock_search.return_value = []
            result = _convert_to_location_string((40.7128, -74.0060), "test.jpg")
            assert result == "Unknown Location"

    def test_geocoding_exception(self, suppress_logging):
        """Test that exceptions during geocoding return 'Unknown Location'."""
        with patch("reverse_geocoder.search") as mock_search:
            mock_search.side_effect = Exception("Geocoding failed")
            result = _convert_to_location_string((40.7128, -74.0060), "test.jpg")
            assert result == "Unknown Location"

    def test_valid_location_with_different_regions(self, suppress_logging):
        """Test geocoding with different regions."""
        with patch("reverse_geocoder.search") as mock_search:
            mock_search.return_value = [
                {
                    "name": "Paris",
                    "admin1": "Île-de-France",
                    "cc": "FR",
                }
            ]
            result = _convert_to_location_string((48.8566, 2.3522), "test.jpg")
            assert result == "Paris, Île-de-France, FR"

    def test_southern_hemisphere_location(self, suppress_logging):
        """Test geocoding for southern hemisphere coordinates."""
        with patch("reverse_geocoder.search") as mock_search:
            mock_search.return_value = [
                {
                    "name": "Sydney",
                    "admin1": "New South Wales",
                    "cc": "AU",
                }
            ]
            result = _convert_to_location_string((-33.8688, 151.2093), "test.jpg")
            assert result == "Sydney, New South Wales, AU"


class TestGetImageInfo:
    """Test get_image_info function."""

    def test_complete_valid_image(self, suppress_logging):
        """Test extracting all information from a complete valid image with valid location."""
        mock_tags = {
            "EXIF DateTimeOriginal": "2024:01:15 14:30:45",
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLatitudeRef": "N",
            "GPS GPSLongitudeRef": "E",
        }
        with (
            patch("builtins.open", mock_open()),
            patch("exifread.process_file", return_value=mock_tags),
            patch("src.core.metadata.rg.search") as mock_search,
        ):
            mock_search.return_value = [
                {
                    "name": "New York",
                    "admin1": "New York",
                    "cc": "US",
                }
            ]
            info = get_image_info("test.jpg")
            # Verify both date and location keys are present
            assert "date_taken" in info
            assert "location" in info
            # Verify date is extracted correctly
            assert info["date_taken"] == datetime(2024, 1, 15, 14, 30, 45)
            # Verify location is resolved from geocoding
            assert info["location"] == "New York, New York, US"
            # Verify geocoding was actually called
            assert mock_search.called

    def test_image_with_date_but_no_location(self, suppress_logging):
        """Test image with date metadata but no GPS data."""
        mock_tags = {
            "EXIF DateTimeOriginal": "2024:01:15 14:30:45",
        }
        with (
            patch("builtins.open", mock_open()),
            patch("exifread.process_file", return_value=mock_tags),
        ):
            info = get_image_info("test.jpg")
            assert info["date_taken"] == datetime(2024, 1, 15, 14, 30, 45)
            assert info["location"] == "Unknown Location"

    def test_image_with_location_but_no_date(self, suppress_logging):
        """Test image with GPS data but no date metadata - verifies location geocoding works."""
        mock_tags = {
            "GPS GPSLatitude": Mock(
                values=[Mock(num=40, den=1), Mock(num=30, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLongitude": Mock(
                values=[Mock(num=74, den=1), Mock(num=0, den=1), Mock(num=0, den=1)]
            ),
            "GPS GPSLatitudeRef": "N",
            "GPS GPSLongitudeRef": "E",
        }
        with (
            patch("builtins.open", mock_open()),
            patch("exifread.process_file", return_value=mock_tags),
            patch("src.core.metadata.rg.search") as mock_search,
        ):
            mock_search.return_value = [
                {
                    "name": "New York",
                    "admin1": "New York",
                    "cc": "US",
                }
            ]
            info = get_image_info("test.jpg")
            # Date should be None since no date metadata present
            assert info["date_taken"] is None
            # Location should be resolved from geocoding
            assert info["location"] == "New York, New York, US"
            # Verify geocoding was called
            assert mock_search.called

    def test_image_with_neither_date_nor_location(self, suppress_logging):
        """Test image with no date and no location metadata."""
        mock_tags = {"Image Model": "Canon EOS"}
        with (
            patch("builtins.open", mock_open()),
            patch("exifread.process_file", return_value=mock_tags),
        ):
            info = get_image_info("test.jpg")
            assert info["date_taken"] is None
            assert info["location"] == "Unknown Location"

    def test_returns_dict_with_correct_keys(self, suppress_logging):
        """Test that get_image_info returns dict with correct keys."""
        mock_tags = {}
        with (
            patch("builtins.open", mock_open()),
            patch("exifread.process_file", return_value=mock_tags),
        ):
            info = get_image_info("test.jpg")
            assert "date_taken" in info
            assert "location" in info
            assert len(info) == 2
