"""Integration tests for the Photidy application"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.core.organiser import organise_photos
from src.utils.errors import InvalidDirectoryError


class TestPhotidyIntegration:
    """Integration tests for end-to-end workflows."""

    def test_end_to_end_photo_organisation_workflow(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test complete workflow from source to organized destination."""
        photos = [
            ("photo1.jpg", datetime(2024, 1, 15), "New York, New York, US"),
            ("photo2.jpg", datetime(2024, 1, 15), "New York, New York, US"),
            ("photo3.jpg", datetime(2024, 6, 20), "Los Angeles, California, US"),
            ("photo4.jpg", datetime(2024, 12, 25), "Unknown"),
        ]

        for photo_name, _, _ in photos:
            (valid_source_dir / photo_name).write_text("fake image data")

        def mock_get_image_info(path):
            for photo_name, date_taken, location in photos:
                if photo_name in path:
                    return {"date_taken": date_taken, "location": location}
            return {"date_taken": None, "location": "Unknown"}

        with patch(
            "src.core.organiser.get_image_info", side_effect=mock_get_image_info
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        # Verify summary
        assert summary["processed"] == 4
        assert summary["failed"] == []
        assert summary["total"] == 4

        # Verify directory structure
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
            / "New York, New York, US"
            / "photo2.jpg"
        ).exists()
        assert (
            valid_dest_dir
            / "2024"
            / "06"
            / "20"
            / "Los Angeles, California, US"
            / "photo3.jpg"
        ).exists()
        assert (valid_dest_dir / "2024" / "12" / "25" / "photo4.jpg").exists()

    def test_directory_structure_creation_matches_expected_pattern(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that directory structure follows expected pattern: YYYY/MM/DD/Location."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = {
            "date_taken": datetime(2024, 3, 7, 15, 45, 30),
            "location": "Paris, Île-de-France, FR",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            organise_photos(str(valid_source_dir), str(valid_dest_dir))

        # Verify exact directory structure
        expected_path = (
            valid_dest_dir
            / "2024"
            / "03"
            / "07"
            / "Paris, Île-de-France, FR"
            / "photo.jpg"
        )
        assert expected_path.exists()

    def test_file_movement_and_renaming_verification(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test that files are moved (not copied) and renamed correctly."""
        image_file = valid_source_dir / "test_photo.jpg"
        image_file.write_text("fake image")

        assert image_file.exists()

        mock_image_info = {
            "date_taken": datetime(2024, 5, 12),
            "location": "Unknown",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert not image_file.exists()

        organized_path = valid_dest_dir / "2024" / "05" / "12" / "test_photo.jpg"
        assert organized_path.exists()

    def test_summary_accuracy_with_various_photo_sets(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test summary accuracy with mixed scenarios."""
        valid_file = valid_source_dir / "valid.jpg"
        valid_file.write_text("fake image")

        no_metadata_file = valid_source_dir / "no_metadata.jpg"
        no_metadata_file.write_text("fake image")

        error_file = valid_source_dir / "error.jpg"
        error_file.write_text("fake image")

        txt_file = valid_source_dir / "document.txt"
        txt_file.write_text("not an image")

        def mock_get_image_info(path):
            if "valid" in path:
                return {"date_taken": datetime(2024, 1, 1), "location": "Unknown"}
            elif "no_metadata" in path:
                return {"date_taken": None, "location": "Unknown"}
            else:
                raise Exception("Processing error")

        with patch(
            "src.core.organiser.get_image_info", side_effect=mock_get_image_info
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 1
        assert len(summary["failed"]) == 2
        assert summary["total"] == 3

    def test_invalid_source_directory_raises_error(self, temp_dir, suppress_logging):
        """Test that invalid source directory raises appropriate error."""
        nonexistent_source = temp_dir / "nonexistent"
        dest = temp_dir / "dest"
        dest.mkdir()

        with pytest.raises(InvalidDirectoryError):
            organise_photos(str(nonexistent_source), str(dest))

    def test_invalid_destination_directory_raises_error(
        self, valid_source_dir, temp_dir, suppress_logging
    ):
        """Test that invalid destination directory raises appropriate error."""
        bad_dest = temp_dir / "bad_dest"
        bad_dest.write_text("this is a file")

        with pytest.raises(InvalidDirectoryError):
            organise_photos(str(valid_source_dir), str(bad_dest))

    def test_large_batch_photo_organisation(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test organizing a large batch of photos."""
        for i in range(20):
            (valid_source_dir / f"photo_{i}.jpg").write_text("fake image")

        def mock_get_image_info(path):
            filename = path.split("/")[-1]  # Get just the filename
            photo_num = int(filename.split("_")[1].split(".")[0])
            dates = [
                datetime(2024, 1, 15),
                datetime(2024, 6, 20),
                datetime(2024, 12, 25),
            ]
            locations = [
                "New York, New York, US",
                "Los Angeles, California, US",
                "Unknown",
            ]
            return {
                "date_taken": dates[photo_num % 3],
                "location": locations[photo_num % 3],
            }

        with patch(
            "src.core.organiser.get_image_info", side_effect=mock_get_image_info
        ):
            summary = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary["processed"] == 20
        assert summary["failed"] == []
        assert summary["total"] == 20

        # Verify source is empty
        assert len(list(valid_source_dir.glob("*"))) == 0

    def test_organisation_with_duplicate_filenames(
        self, valid_source_dir, valid_dest_dir, suppress_logging
    ):
        """Test organizing photos with duplicate filenames but different content."""
        file1 = valid_source_dir / "vacation.jpg"
        file1.write_text("fake image 1")

        mock_image_info = {
            "date_taken": datetime(2024, 7, 10),
            "location": "Unknown",
        }

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary1 = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary1["processed"] == 1

        # Create another file with same name
        file2 = valid_source_dir / "vacation.jpg"
        file2.write_text("fake image 2")

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary2 = organise_photos(str(valid_source_dir), str(valid_dest_dir))

        assert summary2["processed"] == 1

        # Check that both files exist with unique names
        target_dir = valid_dest_dir / "2024" / "07" / "10"
        assert (target_dir / "vacation.jpg").exists()
        assert (target_dir / "vacation_1.jpg").exists()
