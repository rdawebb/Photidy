"""Tests for photo organisation in src/core/organiser.py"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.core.organiser import (
    _get_unique_filename,
    _validate_directories,
    organise_photos,
)
from src.utils.errors import (
    InvalidDirectoryError,
    PhotoMetadataError,
    PhotoOrganisationError,
)


class TestValidateDirectories:
    """Test _validate_directories function."""

    def test_valid_source_and_destination(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test validation with valid source and destination directories."""
        _validate_directories(valid_source_dir, valid_dest_dir)

    def test_source_directory_does_not_exist(self, temp_dir, suppress_logging):
        """Test that non-existent source directory raises InvalidDirectoryError."""
        source = temp_dir / "nonexistent"
        dest = temp_dir / "dest"
        dest.mkdir()
        with pytest.raises(InvalidDirectoryError):
            _validate_directories(source, dest)

    def test_source_is_not_directory(self, temp_dir, suppress_logging):
        """Test that file source raises InvalidDirectoryError."""
        source = temp_dir / "file.txt"
        source.write_text("test")
        dest = temp_dir / "dest"
        dest.mkdir()
        with pytest.raises(InvalidDirectoryError):
            _validate_directories(source, dest)

    def test_source_not_readable(self, temp_dir, suppress_logging):
        """Test that unreadable source directory raises InvalidDirectoryError."""
        import os

        source = temp_dir / "source"
        source.mkdir()
        dest = temp_dir / "dest"
        dest.mkdir()
        # Remove read permissions from source
        os.chmod(source, 0o000)
        try:
            with pytest.raises(InvalidDirectoryError):
                _validate_directories(source, dest)
        finally:
            # Restore permissions for cleanup
            os.chmod(source, 0o755)

    def test_destination_directory_creation_failure(
        self, valid_source_dir, temp_dir, suppress_logging
    ):
        """Test that destination creation failure raises InvalidDirectoryError."""
        source = valid_source_dir
        dest = temp_dir / "dest"

        (temp_dir / "dest").write_text("this is a file, not a directory")
        with pytest.raises(InvalidDirectoryError):
            _validate_directories(source, dest)

    def test_destination_directory_permission_error(
        self, valid_source_dir, temp_dir, suppress_logging
    ):
        """Test that destination permission error raises InvalidDirectoryError."""
        source = valid_source_dir
        dest = temp_dir / "dest"

        (temp_dir / "dest").write_text("this is a file, not a directory")
        with pytest.raises(InvalidDirectoryError):
            _validate_directories(source, dest)

    def test_destination_directory_is_created_if_not_exists(
        self, valid_source_dir, temp_dir, suppress_logging
    ):
        """Test that destination directory is created if it doesn't exist."""
        source = valid_source_dir
        dest = temp_dir / "new_dest"
        assert not dest.exists()
        _validate_directories(source, dest)
        assert dest.exists()


class TestGetUniqueFilename:
    """Test _get_unique_filename function."""

    def test_file_does_not_exist(self, temp_dir, suppress_logging):
        """Test that original filename is returned if file doesn't exist."""
        directory = temp_dir / "dir"
        directory.mkdir()
        result = _get_unique_filename(directory, "photo.jpg")
        assert result == "photo.jpg"

    def test_file_exists_generates_counter(self, temp_dir, suppress_logging):
        """Test that counter is added when file exists."""
        directory = temp_dir / "dir"
        directory.mkdir()

        (directory / "photo.jpg").write_text("test")
        result = _get_unique_filename(directory, "photo.jpg")
        assert result == "photo_1.jpg"

    def test_multiple_conflicts_finds_next_counter(self, temp_dir, suppress_logging):
        """Test finding next available counter with multiple conflicts."""
        directory = temp_dir / "dir"
        directory.mkdir()

        (directory / "photo.jpg").write_text("test")
        (directory / "photo_1.jpg").write_text("test")
        (directory / "photo_2.jpg").write_text("test")
        result = _get_unique_filename(directory, "photo.jpg")
        assert result == "photo_3.jpg"

    def test_unique_filename_with_different_extension(self, temp_dir, suppress_logging):
        """Test unique filename generation with different extensions."""
        directory = temp_dir / "dir"
        directory.mkdir()
        (directory / "image.png").write_text("test")
        result = _get_unique_filename(directory, "image.png")
        assert result == "image_1.png"

    def test_unique_filename_with_multiple_dots(self, temp_dir, suppress_logging):
        """Test unique filename with multiple dots in name."""
        directory = temp_dir / "dir"
        directory.mkdir()
        (directory / "photo.backup.jpg").write_text("test")
        result = _get_unique_filename(directory, "photo.backup.jpg")
        assert result == "photo.backup_1.jpg"

    def test_exception_during_filename_generation(self, temp_dir, suppress_logging):
        """Test that exception during filename generation raises PhotoOrganisationError."""
        directory = temp_dir / "dir"
        directory.mkdir()

        with patch("pathlib.Path.exists", side_effect=Exception("Some error")):
            with pytest.raises(PhotoOrganisationError):
                _get_unique_filename(directory, "photo.jpg")


class TestOrganisePhotos:
    """Test organise_photos function."""

    def test_valid_photo_organisation_with_complete_metadata(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test organising photos with complete metadata."""
        # Create a mock image file
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = {
            "date_taken": datetime(2024, 1, 15, 14, 30, 45),
            "location": "New York, New York, US",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 1
        assert summary["failed"] == []
        assert summary["total"] == 1

        organized_path = (
            valid_dest_dir
            / "2024"
            / "01"
            / "15"
            / "New York, New York, US"
            / "photo.jpg"
        )
        assert organized_path.exists()

    def test_photos_organized_with_only_date_no_location(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test organising photos with date but without location."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = {
            "date_taken": datetime(2024, 6, 20, 10, 15, 30),
            "location": "Unknown",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 1
        assert summary["failed"] == []
        # Check directory structure without location
        organized_path = valid_dest_dir / "2024" / "06" / "20" / "photo.jpg"
        assert organized_path.exists()

    def test_mixed_valid_and_invalid_photos(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test processing mixture of valid and invalid photos."""
        # Create mock files
        valid_file = valid_source_dir / "good_photo.jpg"
        valid_file.write_text("fake image")
        bad_file = valid_source_dir / "broken.jpg"
        bad_file.write_text("fake image")

        def mock_get_image_info(path):
            if "good" in path:
                return {
                    "date_taken": datetime(2024, 1, 15),
                    "location": "New York, New York, US",
                }
            else:
                raise PhotoMetadataError("Invalid metadata")

        with patch(
            "src.core.organiser.get_image_info", side_effect=mock_get_image_info
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 1
        assert len(summary["failed"]) == 1
        assert summary["total"] == 2

    def test_photo_with_missing_date_metadata(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that photo with missing date is skipped."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = {
            "date_taken": None,
            "location": "New York, New York, US",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 0
        assert len(summary["failed"]) == 1
        assert summary["failed"][0][1] == "Missing date metadata"

    def test_photo_metadata_error_handling(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test handling of PhotoMetadataError during processing."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        with patch(
            "src.core.organiser.get_image_info",
            side_effect=PhotoMetadataError("Metadata error"),
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 0
        assert len(summary["failed"]) == 1

    def test_general_exception_during_processing(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test handling of general exceptions during processing."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        with patch(
            "src.core.organiser.get_image_info",
            side_effect=Exception("Unexpected error"),
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 0
        assert len(summary["failed"]) == 1

    def test_non_photo_files_ignored(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that non-photo files are ignored."""
        # Create various file types
        (valid_source_dir / "document.txt").write_text("text")
        (valid_source_dir / "archive.zip").write_text("zip")
        (valid_source_dir / "readme.md").write_text("markdown")

        summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 0
        assert summary["failed"] == []
        assert summary["total"] == 0

    def test_empty_source_directory(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test processing empty source directory."""
        summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 0
        assert summary["failed"] == []
        assert summary["total"] == 0

    def test_file_conflict_handling_generates_unique_name(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that file conflicts are handled with unique naming."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image 1")

        target_dir = valid_dest_dir / "2024" / "01" / "15"
        target_dir.mkdir(parents=True)
        (target_dir / "photo.jpg").write_text("existing file")

        mock_image_info = {
            "date_taken": datetime(2024, 1, 15),
            "location": "Unknown",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 1
        assert (target_dir / "photo_1.jpg").exists()

    def test_return_summary_format(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that summary has correct format."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = {
            "date_taken": datetime(2024, 1, 15),
            "location": "Unknown",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert isinstance(summary, dict)
        assert "processed" in summary
        assert "failed" in summary
        assert "total" in summary
        assert isinstance(summary["processed"], int)
        assert isinstance(summary["failed"], list)
        assert isinstance(summary["total"], int)

    def test_multiple_photos_same_date_different_locations(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test organising multiple photos with same date but different locations."""
        file1 = valid_source_dir / "photo1.jpg"
        file1.write_text("fake image 1")
        file2 = valid_source_dir / "photo2.jpg"
        file2.write_text("fake image 2")

        def mock_get_image_info(path):
            if "photo1" in path:
                return {
                    "date_taken": datetime(2024, 1, 15),
                    "location": "New York, New York, US",
                }
            else:
                return {
                    "date_taken": datetime(2024, 1, 15),
                    "location": "Los Angeles, California, US",
                }

        with patch(
            "src.core.organiser.get_image_info", side_effect=mock_get_image_info
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 2
        assert summary["failed"] == []

        assert (
            valid_dest_dir
            / "2024"
            / "01"
            / "15"
            / "New York, New York, US"
            / "photo1.jpg"
        ).exists()
        assert (
            valid_dest_dir
            / "2024"
            / "01"
            / "15"
            / "Los Angeles, California, US"
            / "photo2.jpg"
        ).exists()

    def test_multiple_photos_different_dates(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test organising multiple photos with different dates."""
        file1 = valid_source_dir / "photo1.jpg"
        file1.write_text("fake image 1")
        file2 = valid_source_dir / "photo2.jpg"
        file2.write_text("fake image 2")

        def mock_get_image_info(path):
            if "photo1" in path:
                return {
                    "date_taken": datetime(2024, 1, 15),
                    "location": "Unknown",
                }
            else:
                return {
                    "date_taken": datetime(2024, 12, 25),
                    "location": "Unknown",
                }

        with patch(
            "src.core.organiser.get_image_info", side_effect=mock_get_image_info
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 2
        assert summary["failed"] == []

        assert (valid_dest_dir / "2024" / "01" / "15" / "photo1.jpg").exists()
        assert (valid_dest_dir / "2024" / "12" / "25" / "photo2.jpg").exists()

    def test_subdirectories_in_source_ignored(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that subdirectories in source are ignored."""
        subdir = valid_source_dir / "subdir"
        subdir.mkdir()
        (subdir / "photo.jpg").write_text("fake image")

        summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        # Should only process files directly in source, not in subdirectories
        assert summary["processed"] == 0
        assert summary["failed"] == []

    def test_case_insensitive_file_extension(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that file extensions are case-insensitive."""
        # Note: On case-insensitive filesystems (like macOS), .JPG and .jpg may be the same file
        file1 = valid_source_dir / "photo1.JPG"
        file1.write_text("fake image")
        file2 = valid_source_dir / "photo2.jpg"
        file2.write_text("fake image")

        mock_image_info = {
            "date_taken": datetime(2024, 1, 15),
            "location": "Unknown",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 2
        assert summary["failed"] == []
