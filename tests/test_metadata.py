"""Tests for metadata extraction wrapper in src/core/metadata.py

This module tests the integration between the Python wrapper and Rust backend.
Rust implementation details (EXIF parsing, GPS coordinate conversion, geocoding) are tested in the Rust test suites.
"""

from unittest.mock import patch

import pytest

from src.core.metadata import get_image_info
from src.utils.errors import InvalidPhotoFormatError, PhotoMetadataError


@pytest.fixture
def db_path():
    """Fixture that provides the embedded database path for tests."""
    from pathlib import Path
    import photo_meta

    db_dir = Path(__file__).parent.parent / "rust/photo_meta/data"
    return str(db_dir / photo_meta.db_filename())


class TestGetImageInfo:
    """Integration tests for get_image_info wrapper function."""

    @pytest.mark.parametrize(
        "scenario",
        ["complete", "date_only", "location_only", "no_exif"],
        ids=["all_fields", "date_only", "location_only", "no_exif"],
    )
    def test_valid_metadata_extraction(
        self, metadata_scenarios, scenario, suppress_logging
    ):
        """Test metadata extraction with various EXIF combinations."""
        mock_result = metadata_scenarios[scenario]
        with patch("src.core.metadata.extract_metadata", return_value=mock_result):
            info = get_image_info("test.jpg")
            assert info == mock_result
            if scenario == "complete":
                assert "date_taken" in info
                assert "location" in info

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
        mock_result = metadata_scenarios["no_exif"]
        with patch("src.core.metadata.extract_metadata", return_value=mock_result):
            info = get_image_info(f"test{file_format}")
            assert info is not None

    def test_case_insensitive_format_validation(
        self, metadata_scenarios, suppress_logging
    ):
        """Test that format validation is case-insensitive."""
        mock_result = metadata_scenarios["no_exif"]
        with patch("src.core.metadata.extract_metadata", return_value=mock_result):
            info = get_image_info("test.JPG")
            assert info is not None

    def test_logging_success_with_date(self, metadata_scenarios, caplog):
        """Test that successful extraction with date is logged."""
        mock_result = metadata_scenarios["date_only"]
        with patch("src.core.metadata.extract_metadata", return_value=mock_result):
            get_image_info("test.jpg")
            assert "Extracted date info" in caplog.text

    def test_logging_success_with_location(self, metadata_scenarios, caplog):
        """Test that successful location extraction is logged."""
        mock_result = metadata_scenarios["location_only"]
        with patch("src.core.metadata.extract_metadata", return_value=mock_result):
            get_image_info("test.jpg")
            assert "Extracted location info" in caplog.text

    def test_logging_warning_no_date(self, metadata_scenarios, caplog):
        """Test that missing date is logged as warning."""
        mock_result = metadata_scenarios["no_exif"]
        with patch("src.core.metadata.extract_metadata", return_value=mock_result):
            get_image_info("test.jpg")
            assert "No date info found" in caplog.text

    def test_logging_warning_no_location(self, metadata_scenarios, caplog):
        """Test that missing location is logged."""
        mock_result = metadata_scenarios["date_only"]
        with patch("src.core.metadata.extract_metadata", return_value=mock_result):
            get_image_info("test.jpg")
            assert "location" in caplog.text.lower()

    def test_logging_error_invalid_format(self, caplog):
        """Test that invalid file format is logged as error."""
        with pytest.raises(InvalidPhotoFormatError):
            get_image_info("test.txt")
        assert "Unsupported file format" in caplog.text

    def test_returns_rust_result_unchanged(self, suppress_logging):
        """Test that the function returns the Rust result without modification."""
        expected_result = {
            "date_taken": "2024-01-15T14:30:45+00:00",
            "lat": 40.7128,
            "lon": -74.006,
            "location": "New York, New York, US",
        }
        with patch("src.core.metadata.extract_metadata", return_value=expected_result):
            result = get_image_info("test.jpg")
            assert result == expected_result


class TestRustExtractMetadataIntegration:
    """Integration tests for the Rust extract_metadata function.

    These tests verify the output format and correctness of the Rust metadata extraction.
    """

    def test_extract_metadata_with_complete_exif(self, db_path):
        """Test extract_metadata with complete EXIF data (date and location)."""
        from photo_meta import extract_metadata

        result = extract_metadata(
            "rust/photo_meta/tests/fixtures/complete_exif.jpg", db_path
        )

        # Verify all required keys exist
        assert "date_taken" in result
        assert "lat" in result
        assert "lon" in result
        assert "location" in result

        # Verify date_taken is valid RFC3339
        if result["date_taken"] is not None:
            # Should be parseable as ISO format datetime
            from datetime import datetime

            datetime.fromisoformat(result["date_taken"].replace("Z", "+00:00"))

        # Verify lat/lon are valid floats in correct range
        if result["lat"] is not None and result["lon"] is not None:
            assert isinstance(result["lat"], float)
            assert isinstance(result["lon"], float)
            assert -90.0 <= result["lat"] <= 90.0
            assert -180.0 <= result["lon"] <= 180.0

            # Verify location has proper structure or "Unknown Location"
            location = result["location"]
            if location != "Unknown Location":
                parts = [p.strip() for p in location.split(",")]
                assert len(parts) in (2, 3), (
                    f"Location should have 2-3 parts, got {len(parts)}: {location}"
                )
                for part in parts:
                    assert len(part) > 0, "Location parts should not be empty"

    def test_extract_metadata_without_exif(self, db_path):
        """Test extract_metadata with an image that has no EXIF data."""
        from photo_meta import extract_metadata

        result = extract_metadata("rust/photo_meta/tests/fixtures/no_exif.jpg", db_path)

        # Should have all keys but with None/default values for missing EXIF
        assert "date_taken" in result
        assert "lat" in result
        assert "lon" in result
        assert "location" in result

        # No date or GPS data
        assert result["date_taken"] is None
        assert result["lat"] is None
        assert result["lon"] is None
        assert result["location"] == "Unknown Location"

    def test_extract_metadata_with_gps_only(self, db_path):
        """Test extract_metadata with GPS data but no date."""
        from photo_meta import extract_metadata

        result = extract_metadata(
            "rust/photo_meta/tests/fixtures/only_gps.jpg", db_path
        )

        # Should have GPS but no date
        assert result["date_taken"] is None
        assert result["lat"] is not None
        assert result["lon"] is not None

        # Verify GPS coordinates are valid
        assert isinstance(result["lat"], float)
        assert isinstance(result["lon"], float)
        assert -90.0 <= result["lat"] <= 90.0
        assert -180.0 <= result["lon"] <= 180.0

    def test_extract_metadata_with_date_only(self, db_path):
        """Test extract_metadata with date but no GPS data."""
        from photo_meta import extract_metadata

        result = extract_metadata(
            "rust/photo_meta/tests/fixtures/only_date.jpg", db_path
        )

        # Should have date but no GPS
        assert result["date_taken"] is not None
        assert result["lat"] is None
        assert result["lon"] is None
        assert result["location"] == "Unknown Location"

        # Verify date format is valid RFC3339
        from datetime import datetime

        datetime.fromisoformat(result["date_taken"].replace("Z", "+00:00"))
