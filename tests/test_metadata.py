"""Tests for metadata extraction wrapper in src/core/metadata.py

This module tests the integration between the Python wrapper and Rust backend.
Rust implementation details (EXIF parsing, GPS coordinate conversion, geocoding) are tested in the Rust test suites.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.metadata import get_image_info
from src.utils.errors import InvalidPhotoFormatError, PhotoMetadataError


def create_mock_extracted_metadata(timestamp=None, lat=None, lon=None):
    """Create a mock Rust ExtractedMetadata object."""
    mock = MagicMock()
    mock.timestamp = timestamp
    mock.lat = lat
    mock.lon = lon
    return mock


def create_mock_place(name="Unknown Location"):
    """Create a mock Rust Place object."""
    mock = MagicMock()
    mock.name = name
    return mock


@pytest.fixture
def db_path():
    """Fixture that provides the embedded database path for tests."""
    from runtime.paths import db_path

    return db_path()


class TestGetImageInfo:
    """Integration tests for get_image_info wrapper function."""

    @pytest.fixture(autouse=True, scope="class")
    def enable_metadata_logger_propagation(self, request):
        import logging

        logger = logging.getLogger("src.core.metadata")
        old_propagate = logger.propagate
        logger.propagate = True

        def fin():
            logger.propagate = old_propagate

        request.addfinalizer(fin)

    @pytest.mark.parametrize(
        "scenario",
        ["complete", "date_only", "location_only", "no_exif"],
        ids=["all_fields", "date_only", "location_only", "no_exif"],
    )
    def test_valid_metadata_extraction(
        self, metadata_scenarios, scenario, suppress_logging
    ):
        """Test metadata extraction with various EXIF combinations."""
        scenario_data = metadata_scenarios[scenario]

        # Create mock Rust ExtractedMetadata (without location field)
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )

        # Create mock Place object for reverse_geocode
        mock_place = None
        if scenario_data["location"] != "Unknown Location":
            mock_place = create_mock_place(scenario_data["location"])

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode", return_value=mock_place):
                info = get_image_info("test.jpg")
                assert info.location == scenario_data["location"]
                if scenario == "complete":
                    assert info.timestamp is not None
                    assert info.location is not None

    def test_unsupported_file_format_raises_error(self, suppress_logging):
        """Test that unsupported file format raises InvalidPhotoFormatError."""
        with pytest.raises(InvalidPhotoFormatError) as exc_info:
            get_image_info("test.txt")
        assert "Unsupported file format" in str(exc_info.value)

    def test_rust_extraction_returns_none_raises_error(self, suppress_logging):
        """Test that Rust function returning None raises PhotoMetadataError."""
        with patch("src.core.metadata.extract_metadata", return_value=None):
            with pytest.raises(PhotoMetadataError) as exc_info:
                get_image_info("test.jpg")
            assert "Failed to extract metadata" in str(exc_info.value)

    def test_rust_extraction_raises_exception(self, suppress_logging):
        """Test that exceptions from Rust are caught and re-raised as PhotoMetadataError."""
        with patch(
            "src.core.metadata.extract_metadata",
            side_effect=RuntimeError("Rust error"),
        ):
            with pytest.raises(PhotoMetadataError) as exc_info:
                get_image_info("test.jpg")
            assert "Unexpected error processing" in str(exc_info.value)

    @pytest.mark.parametrize(
        "file_format",
        [".jpg", ".jpeg", ".png", ".tiff", ".raw", ".cr2", ".heic"],
        ids=["jpg", "jpeg", "png", "tiff", "raw", "cr2", "heic"],
    )
    def test_supported_format_accepted(
        self, metadata_scenarios, file_format, suppress_logging
    ):
        """Test that each supported image format is accepted."""
        scenario_data = metadata_scenarios["no_exif"]
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )
        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode", return_value=None):
                info = get_image_info(f"test{file_format}")
                assert info is not None

    def test_case_insensitive_format_validation(
        self, metadata_scenarios, suppress_logging
    ):
        """Test that format validation is case-insensitive."""
        scenario_data = metadata_scenarios["no_exif"]
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )
        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode", return_value=None):
                info = get_image_info("test.JPG")
                assert info is not None

    def test_logging_error_invalid_format(self, caplog):
        """Test that invalid file format is logged as error."""
        with pytest.raises(InvalidPhotoFormatError):
            get_image_info("test.txt")
        assert "Unsupported file format" in caplog.text

    @pytest.mark.parametrize(
        "scenario,expected_log_message,should_contain",
        [
            ("complete", "Extracted date info", True),
            ("complete", "Extracted location info", True),
            ("date_only", "Extracted date info", True),
            ("date_only", "No location found", True),
            ("location_only", "Extracted location info", True),
            ("location_only", "No timestamp found", True),
            ("no_exif", "No timestamp found", True),
        ],
        ids=[
            "date_logged",
            "location_logged",
            "date_only_has_date",
            "date_only_no_location",
            "location_only_has_location",
            "location_only_no_date",
            "no_exif_warning",
        ],
    )
    def test_logging_messages_for_metadata_scenarios(
        self, metadata_scenarios, scenario, expected_log_message, should_contain, caplog
    ):
        """Test that metadata extraction logs appropriate messages for various scenarios."""
        scenario_data = metadata_scenarios[scenario]

        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )

        mock_place = None
        if scenario_data["location"] != "Unknown Location":
            mock_place = create_mock_place(scenario_data["location"])

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode", return_value=mock_place):
                get_image_info("test.jpg")
                if should_contain:
                    assert expected_log_message in caplog.text

    def test_returns_rust_result_unchanged(self, suppress_logging):
        """Test that the function correctly constructs ImageInfo from Rust data."""
        # Create mock Rust ExtractedMetadata
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp="2024-01-15T14:30:45+00:00",
            lat=40.7128,
            lon=-74.006,
        )
        # Create mock Place for reverse_geocode
        mock_place = create_mock_place("New York, New York, US")

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode", return_value=mock_place):
                result = get_image_info("test.jpg")
                assert result.path == "test.jpg"
                assert result.timestamp is not None
                assert result.lat == 40.7128
                assert result.lon == -74.006
                assert result.location == "New York, New York, US"


class TestReverseGeocodeIntegration:
    """Tests for reverse_geocode integration in get_image_info."""

    def test_reverse_geocode_called_with_valid_coordinates(
        self, metadata_scenarios, suppress_logging
    ):
        """Test that reverse_geocode is called when GPS coordinates are available."""
        scenario_data = metadata_scenarios["location_only"]
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )
        mock_place = create_mock_place(scenario_data["location"])

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch(
                "src.core.metadata.reverse_geocode", return_value=mock_place
            ) as mock_geocode:
                get_image_info("test.jpg")
                # Verify reverse_geocode was called with the correct coordinates
                mock_geocode.assert_called_once()
                call_args = mock_geocode.call_args
                assert call_args[0][0] == scenario_data["lat"]
                assert call_args[0][1] == scenario_data["lon"]

    def test_reverse_geocode_not_called_without_coordinates(
        self, metadata_scenarios, suppress_logging
    ):
        """Test that reverse_geocode is not called when GPS coordinates are missing."""
        scenario_data = metadata_scenarios["date_only"]
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode") as mock_geocode:
                get_image_info("test.jpg")
                # Verify reverse_geocode was NOT called
                mock_geocode.assert_not_called()

    def test_reverse_geocode_returns_none_defaults_to_unknown_location(
        self, metadata_scenarios, suppress_logging
    ):
        """Test that missing location defaults to 'Unknown Location' when reverse_geocode returns None."""
        scenario_data = metadata_scenarios["location_only"]
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode", return_value=None):
                info = get_image_info("test.jpg")
                assert info.location == "Unknown Location"

    def test_reverse_geocode_returns_place_name_correctly(
        self, metadata_scenarios, suppress_logging
    ):
        """Test that the location is correctly extracted from reverse_geocode Place object."""
        scenario_data = metadata_scenarios["complete"]
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )
        mock_place = create_mock_place("San Francisco, California, US")

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch("src.core.metadata.reverse_geocode", return_value=mock_place):
                info = get_image_info("test.jpg")
                assert info.location == "San Francisco, California, US"

    def test_reverse_geocode_exception_handling(
        self, metadata_scenarios, suppress_logging
    ):
        """Test that exceptions from reverse_geocode are caught and re-raised as PhotoMetadataError."""
        scenario_data = metadata_scenarios["location_only"]
        mock_rust_metadata = create_mock_extracted_metadata(
            timestamp=scenario_data["timestamp"],
            lat=scenario_data["lat"],
            lon=scenario_data["lon"],
        )

        with patch(
            "src.core.metadata.extract_metadata", return_value=mock_rust_metadata
        ):
            with patch(
                "src.core.metadata.reverse_geocode",
                side_effect=RuntimeError("Geocoding failed"),
            ):
                with pytest.raises(PhotoMetadataError) as exc_info:
                    get_image_info("test.jpg")
                assert "Unexpected error processing" in str(exc_info.value)


class TestRustExtractMetadataIntegration:
    """Integration tests for the Rust extract_metadata function.

    These tests verify the output format and correctness of the Rust metadata extraction.
    """

    def test_extract_metadata_with_complete_exif(self):
        """Test extract_metadata with complete EXIF data (date and GPS)."""
        from photidy import extract_metadata

        result = extract_metadata("rust/photidy/tests/fixtures/complete_exif.jpg")

        # Verify all required attributes exist
        assert hasattr(result, "timestamp")
        assert hasattr(result, "lat")
        assert hasattr(result, "lon")

        # Verify timestamp is valid RFC3339
        if result.timestamp is not None:
            # Should be parseable as ISO format datetime
            from datetime import datetime

            datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))

        # Verify lat/lon are valid floats in correct range
        if result.lat is not None and result.lon is not None:
            assert isinstance(result.lat, float)
            assert isinstance(result.lon, float)
            assert -90.0 <= result.lat <= 90.0
            assert -180.0 <= result.lon <= 180.0

    def test_extract_metadata_without_exif(self):
        """Test extract_metadata with an image that has no EXIF data."""
        from photidy import extract_metadata

        result = extract_metadata("rust/photidy/tests/fixtures/no_exif.jpg")

        # Should have all attributes but with None/default values for missing EXIF
        assert hasattr(result, "timestamp")
        assert hasattr(result, "lat")
        assert hasattr(result, "lon")

        # No timestamp or GPS data
        assert result.timestamp is None
        assert result.lat is None
        assert result.lon is None

    def test_extract_metadata_with_gps_only(self):
        """Test extract_metadata with GPS data but no date."""
        from photidy import extract_metadata

        result = extract_metadata("rust/photidy/tests/fixtures/only_gps.jpg")

        # Should have GPS but no date
        assert result.timestamp is None
        assert result.lat is not None
        assert result.lon is not None

        # Verify GPS coordinates are valid
        assert isinstance(result.lat, float)
        assert isinstance(result.lon, float)
        assert -90.0 <= result.lat <= 90.0
        assert -180.0 <= result.lon <= 180.0

    def test_extract_metadata_with_date_only(self):
        """Test extract_metadata with date but no GPS data."""
        from photidy import extract_metadata

        result = extract_metadata("rust/photidy/tests/fixtures/only_date.jpg")

        # Should have date but no GPS
        assert result.timestamp is not None
        assert result.lat is None
        assert result.lon is None

        # Verify date format is valid RFC3339
        from datetime import datetime

        datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))
