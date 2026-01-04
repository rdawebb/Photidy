"""Tests for photo organisation in src/core/organiser.py"""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.image_info import ImageInfo
from src.core.organiser import (
    _get_unique_filename,
    _validate_directories,
)
from src.utils.errors import (
    InvalidDirectoryError,
    PhotoMetadataError,
    PhotoOrganisationError,
)


class TestValidateDirectories:
    """Test _validate_directories function."""

    def test_valid_source_and_destination(
        self, valid_source_dir, valid_dest_dir, suppress_logging, isolate_state
    ):
        """Test validation with valid source and destination directories."""
        _validate_directories(valid_source_dir, valid_dest_dir)

    @pytest.mark.parametrize(
        "error_scenario",
        ["nonexistent", "not_directory", "not_readable"],
        ids=["missing", "is_file", "no_access"],
    )
    def test_source_validation_errors(self, temp_dir, suppress_logging, error_scenario):
        """Test various source directory validation errors."""
        source = temp_dir / "source"
        dest = temp_dir / "dest"
        dest.mkdir()

        if error_scenario == "nonexistent":
            # Source doesn't exist - don't create it
            pass
        elif error_scenario == "not_directory":
            source.write_text("not a directory")
        elif error_scenario == "not_readable":
            source.mkdir()
            with patch("os.access", return_value=False):
                with pytest.raises(InvalidDirectoryError):
                    _validate_directories(source, dest)
                return

        with pytest.raises(InvalidDirectoryError):
            _validate_directories(source, dest)

    def test_destination_directory_creation_failure(
        self, valid_source_dir, temp_dir, suppress_logging
    ):
        """Test that destination creation failure raises InvalidDirectoryError."""
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

    @pytest.mark.parametrize(
        "existing_files,filename,expected",
        [
            ([], "photo.jpg", "photo.jpg"),
            (["photo.jpg"], "photo.jpg", "photo_1.jpg"),
            (
                ["photo.jpg", "photo_1.jpg", "photo_2.jpg"],
                "photo.jpg",
                "photo_3.jpg",
            ),
            (["image.png"], "image.png", "image_1.png"),
            (["photo.backup.jpg"], "photo.backup.jpg", "photo.backup_1.jpg"),
        ],
        ids=[
            "no_conflict",
            "one_conflict",
            "multiple_conflicts",
            "different_ext",
            "multiple_dots",
        ],
    )
    def test_unique_filename_generation(
        self, temp_dir, suppress_logging, existing_files, filename, expected
    ):
        """Test unique filename generation with various conflict scenarios."""
        directory = temp_dir / "dir"
        directory.mkdir()
        for f in existing_files:
            (directory / f).write_text("test")

        result = _get_unique_filename(directory, filename)
        assert result == expected

    def test_exception_during_filename_generation(self, temp_dir, suppress_logging):
        """Test that exception during filename generation raises PhotoOrganisationError."""
        directory = temp_dir / "dir"
        directory.mkdir()

        with patch("pathlib.Path.exists", side_effect=Exception("Some error")):
            with pytest.raises(PhotoOrganisationError):
                _get_unique_filename(directory, "photo.jpg")


class TestOrganisePhotos:
    """Test organise_photos function."""

    @pytest.mark.parametrize(
        "date_taken,location,expected_path",
        [
            (
                datetime(2024, 1, 15, 14, 30, 45),
                "New York, New York, US",
                Path("2024") / "01" / "15" / "New York, New York, US" / "photo.jpg",
            ),
            (
                datetime(2024, 6, 20, 10, 15, 30),
                "Unknown Location",
                Path("2024") / "06" / "20" / "photo.jpg",
            ),
        ],
        ids=["with_location", "without_location"],
    )
    def test_photo_organisation_with_various_metadata(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        date_taken,
        location,
        expected_path,
    ):
        """Test organising photos with various metadata combinations."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = ImageInfo(
            path=image_file,
            timestamp=date_taken,
            lat=None,
            lon=None,
            location=location,
        )

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = isolate_state["organise_photos"](
                str(valid_source_dir), str(valid_dest_dir)
            )

        assert summary["processed"] == 1
        assert summary["failed"] == []
        assert summary["total"] == 1

        organised_path = valid_dest_dir / expected_path
        assert organised_path.exists()

    def test_mixed_valid_and_invalid_photos(
        self, valid_source_dir, valid_dest_dir, suppress_logging, isolate_state
    ):
        """Test processing mixture of valid and invalid photos."""
        # Create mock files
        valid_file = valid_source_dir / "good_photo.jpg"
        valid_file.write_text("fake image")
        bad_file = valid_source_dir / "broken.jpg"
        bad_file.write_text("fake image")

        from pathlib import Path

        from src.core.image_info import ImageInfo

        def mock_get_image_info(path):
            if "good" in str(path):
                return ImageInfo(
                    path=Path(path),
                    timestamp=datetime(2024, 1, 15),
                    lat=None,
                    lon=None,
                    location="New York, New York, US",
                )
            else:
                raise PhotoMetadataError("Invalid metadata")

        with patch(
            "src.core.organiser.get_image_info", side_effect=mock_get_image_info
        ):
            summary = isolate_state["organise_photos"](
                str(valid_source_dir), str(valid_dest_dir)
            )

        assert summary["processed"] == 1
        assert len(summary["failed"]) == 1
        assert summary["total"] == 2

    @pytest.mark.parametrize(
        "error_type,error_message,expected_error_match",
        [
            ("missing_date", None, "Missing date metadata"),
            (
                "metadata_error",
                PhotoMetadataError("Cannot read EXIF data"),
                "Cannot read EXIF data",
            ),
            ("general_exception", Exception("Unexpected error"), "Unexpected error"),
        ],
        ids=["missing_date", "metadata_error", "general_exception"],
    )
    def test_error_handling_during_processing(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        error_type,
        error_message,
        expected_error_match,
    ):
        """Test handling of various errors during photo processing."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        if error_type == "missing_date":
            from src.core.image_info import ImageInfo

            mock_image_info = ImageInfo(
                path=image_file,
                timestamp=None,
                lat=None,
                lon=None,
                location="New York, New York, US",
            )
            with patch(
                "src.core.organiser.get_image_info", return_value=mock_image_info
            ):
                summary = isolate_state["organise_photos"](
                    str(valid_source_dir), str(valid_dest_dir)
                )
        elif error_type == "metadata_error":
            with patch(
                "src.core.organiser.get_image_info",
                side_effect=error_message,
            ):
                summary = isolate_state["organise_photos"](
                    str(valid_source_dir), str(valid_dest_dir)
                )
        else:  # general_exception
            with patch(
                "src.core.organiser.get_image_info",
                side_effect=error_message,
            ):
                summary = isolate_state["organise_photos"](
                    str(valid_source_dir), str(valid_dest_dir)
                )

        assert summary["processed"] == 0
        assert len(summary["failed"]) == 1
        assert expected_error_match in summary["failed"][0][1]

    @pytest.mark.parametrize(
        "setup_type",
        ["empty_directory", "non_photo_files"],
    )
    def test_empty_and_invalid_source_handling(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        setup_type,
    ):
        """Test processing directories with no valid photos."""
        # Setup source based on parameter
        if setup_type == "non_photo_files":
            (valid_source_dir / "document.txt").write_text("text")
            (valid_source_dir / "archive.zip").write_text("zip")
            (valid_source_dir / "readme.md").write_text("markdown")
        # else: empty_directory - no setup needed

        summary = isolate_state["organise_photos"](
            str(valid_source_dir), str(valid_dest_dir)
        )

        assert summary["processed"] == 0
        assert summary["failed"] == []
        assert summary["total"] == 0

    def test_subdirectories_in_source_ignored(
        self, valid_source_dir, valid_dest_dir, suppress_logging, isolate_state
    ):
        """Test that files in subdirectories are also processed recursively."""
        subdir = valid_source_dir / "subdir"
        subdir.mkdir(exist_ok=True)
        image_file = subdir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = ImageInfo(
            path=image_file,
            timestamp=datetime(2024, 1, 15),
            lat=None,
            lon=None,
            location="Unknown Location",
        )

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = isolate_state["organise_photos"](
                str(valid_source_dir), str(valid_dest_dir)
            )

        # Files in subdirectories are also scanned and processed recursively
        assert summary["processed"] == 1
        assert summary["failed"] == []
        assert summary["total"] == 1

        organised_path = valid_dest_dir / "2024" / "01" / "15" / "photo.jpg"
        assert organised_path.exists()

    @pytest.mark.parametrize(
        "setup_photos,get_info_func,expected_checks",
        [
            (
                [("photo1.jpg", "fake image 1"), ("photo2.jpg", "fake image 2")],
                lambda path: __import__(
                    "src.core.image_info"
                ).core.image_info.ImageInfo(
                    path=Path(path),
                    timestamp=datetime(2024, 1, 15),
                    lat=None,
                    lon=None,
                    location="New York, New York, US"
                    if "photo1" in str(path)
                    else "Los Angeles, California, US",
                ),
                [
                    (
                        Path("2024")
                        / "01"
                        / "15"
                        / "New York, New York, US"
                        / "photo1.jpg",
                    ),
                    (
                        Path("2024")
                        / "01"
                        / "15"
                        / "Los Angeles, California, US"
                        / "photo2.jpg",
                    ),
                ],
            ),
            (
                [("photo1.jpg", "fake image 1"), ("photo2.jpg", "fake image 2")],
                lambda path: __import__(
                    "src.core.image_info"
                ).core.image_info.ImageInfo(
                    path=Path(path),
                    timestamp=datetime(2024, 1, 15)
                    if "photo1" in str(path)
                    else datetime(2024, 12, 25),
                    lat=None,
                    lon=None,
                    location="Unknown Location",
                ),
                [
                    (Path("2024") / "01" / "15" / "photo1.jpg",),
                    (Path("2024") / "12" / "25" / "photo2.jpg",),
                ],
            ),
        ],
        ids=["same_date_different_locations", "different_dates"],
    )
    def test_multiple_photos_organisation(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        setup_photos,
        get_info_func,
        expected_checks,
    ):
        """Test organising multiple photos with various metadata combinations."""
        for filename, content in setup_photos:
            (valid_source_dir / filename).write_text(content)

        with patch("src.core.organiser.get_image_info", side_effect=get_info_func):
            summary = isolate_state["organise_photos"](
                str(valid_source_dir), str(valid_dest_dir)
            )

        assert summary["processed"] == 2
        assert summary["failed"] == []

        for expected_path_parts in expected_checks:
            organised_path = valid_dest_dir / expected_path_parts[0]
            assert organised_path.exists()

    def test_file_conflict_handling_generates_unique_name(
        self, valid_source_dir, valid_dest_dir, suppress_logging, isolate_state
    ):
        """Test that file conflicts are handled with unique naming."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image 1")

        target_dir = valid_dest_dir / "2024" / "01" / "15"
        target_dir.mkdir(parents=True)
        (target_dir / "photo.jpg").write_text("existing file")

        mock_image_info = ImageInfo(
            path=image_file,
            timestamp=datetime(2024, 1, 15),
            lat=None,
            lon=None,
            location="Unknown Location",
        )

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = isolate_state["organise_photos"](
                str(valid_source_dir), str(valid_dest_dir)
            )

        assert summary["processed"] == 1
        assert (target_dir / "photo_1.jpg").exists()

    def test_case_insensitive_file_extension(
        self, valid_source_dir, valid_dest_dir, suppress_logging, isolate_state
    ):
        """Test that file extensions are case-insensitive."""
        # Note: On case-insensitive filesystems (like macOS), this test may not behave as expected
        file1 = valid_source_dir / "photo1.JPG"
        file1.write_text("fake image")
        file2 = valid_source_dir / "photo2.jpg"
        file2.write_text("fake image")

        mock_image_info = ImageInfo(
            path=file1,
            timestamp=datetime(2024, 1, 15),
            lat=None,
            lon=None,
            location="Unknown Location",
        )

        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            summary = isolate_state["organise_photos"](
                str(valid_source_dir), str(valid_dest_dir)
            )

        assert summary["processed"] == 2
        assert summary["failed"] == []


class TestOrganisePhotosDefaultPaths:
    """Test organise_photos with default paths (no parameters provided)."""

    def test_organise_photos_uses_default_paths(
        self, valid_source_dir, valid_dest_dir, suppress_logging, tmp_path
    ):
        """Test that organise_photos works with default state/undo paths."""
        from src.core.organiser import organise_photos

        state_file = tmp_path / "organiser_state.json"
        undo_log = tmp_path / "organiser_undo.log"

        with (
            patch("src.core.organiser.state_file", state_file),
            patch("src.core.organiser.undo_log", undo_log),
        ):
            # Create a test image
            image_file = valid_source_dir / "photo.jpg"
            image_file.write_text("fake image")

            mock_image_info = ImageInfo(
                path=image_file,
                timestamp=datetime(2024, 1, 15, 14, 30, 45),
                lat=None,
                lon=None,
                location="New York, New York, US",
            )

            # Change to temp directory so default paths write there
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(str(tmp_path))

                with patch(
                    "src.core.organiser.get_image_info", return_value=mock_image_info
                ):
                    summary = organise_photos(
                        str(valid_source_dir), str(valid_dest_dir)
                    )

                assert summary["processed"] == 1
                assert summary["failed"] == []

                # Verify default state file was created
                assert state_file.exists()
                assert undo_log.exists()
            finally:
                os.chdir(original_cwd)

    def test_undo_organisation_with_default_path(
        self, valid_source_dir, valid_dest_dir, suppress_logging, tmp_path
    ):
        """Test undo_organisation with default undo log path."""
        from src.core.organiser import organise_photos, undo_organisation

        state_file = tmp_path / "organiser_state.json"
        undo_log = tmp_path / "organiser_undo.log"

        with (
            patch("src.core.organiser.state_file", state_file),
            patch("src.core.organiser.undo_log", undo_log),
        ):
            # Create a test image
            image_file = valid_source_dir / "photo.jpg"
            image_file.write_text("fake image")

            from pathlib import Path

            mock_image_info = ImageInfo(
                path=image_file,
                timestamp=datetime(2024, 1, 15, 14, 30, 45),
                lat=None,
                lon=None,
                location="New York, New York, US",
            )

            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(str(tmp_path))

                # organise photos
                with patch(
                    "src.core.organiser.get_image_info", return_value=mock_image_info
                ):
                    summary = organise_photos(
                        str(valid_source_dir), str(valid_dest_dir)
                    )

                assert summary["processed"] == 1

                # Verify the file was moved
                organised_path = (
                    Path(valid_dest_dir)
                    / "2024"
                    / "01"
                    / "15"
                    / "New York, New York, US"
                    / "photo.jpg"
                )
                assert organised_path.exists()
                assert not image_file.exists()

                # Undo the operation
                undo_organisation()

                # Verify the file was restored
                assert image_file.exists()
                assert not organised_path.exists()
            finally:
                os.chdir(original_cwd)

    @pytest.mark.parametrize(
        "move_failure_type",
        ["staging_move_fails", "final_move_fails"],
        ids=["staging_move_failure", "final_move_failure"],
    )
    def test_move_operation_failures(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        move_failure_type,
    ):
        """Test handling of file move failures during organisation."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = ImageInfo(
            path=image_file,
            timestamp=datetime(2024, 1, 15, 14, 30, 45),
            lat=None,
            lon=None,
            location="New York, New York, US",
        )

        if move_failure_type == "staging_move_fails":
            # Mock shutil.move to fail on first call (staging)
            with patch(
                "src.core.organiser.get_image_info", return_value=mock_image_info
            ):
                with patch(
                    "src.core.organiser.shutil.move", side_effect=OSError("Move failed")
                ):
                    summary = isolate_state["organise_photos"](
                        str(valid_source_dir), str(valid_dest_dir)
                    )

            assert summary["processed"] == 0
            assert len(summary["failed"]) == 1
            assert "Staging move failed" in summary["failed"][0][1]

        else:  # final_move_fails
            # Mock shutil.move to succeed on first call, fail on second
            call_count = [0]

            def move_side_effect(src, dst):
                call_count[0] += 1
                if call_count[0] == 2:  # Final move
                    raise OSError("Final move failed")
                # First call (staging) succeeds by actually moving
                from pathlib import Path as P

                P(dst).parent.mkdir(parents=True, exist_ok=True)
                P(src).rename(dst)

            with patch(
                "src.core.organiser.get_image_info", return_value=mock_image_info
            ):
                with patch(
                    "src.core.organiser.shutil.move", side_effect=move_side_effect
                ):
                    summary = isolate_state["organise_photos"](
                        str(valid_source_dir), str(valid_dest_dir)
                    )

            assert summary["processed"] == 0
            assert len(summary["failed"]) == 1
            assert "Final move failed" in summary["failed"][0][1]

    def test_staging_directory_creation_failure(
        self, valid_source_dir, valid_dest_dir, suppress_logging, isolate_state
    ):
        """Test handling when staging directory creation fails."""
        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        mock_image_info = ImageInfo(
            path=image_file,
            timestamp=datetime(2024, 1, 15, 14, 30, 45),
            lat=None,
            lon=None,
            location="New York, New York, US",
        )

        # Mock Path.mkdir to raise Error when called
        with patch("src.core.organiser.get_image_info", return_value=mock_image_info):
            with patch(
                "pathlib.Path.mkdir", side_effect=PermissionError("No permission")
            ):
                with pytest.raises(
                    InvalidDirectoryError,
                    match="Failed to create destination directory",
                ):
                    isolate_state["organise_photos"](
                        str(valid_source_dir), str(valid_dest_dir)
                    )

    def test_undo_no_log_file(self, tmp_path, suppress_logging):
        """Test undo_organisation when no log file exists."""
        from src.core.organiser import undo_organisation

        original_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            # Should not raise, just log a warning
            undo_organisation()
        finally:
            os.chdir(original_cwd)

    def test_successful_undo_operation(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        tmp_path,
    ):
        """Test a complete successful undo operation."""
        from src.core.organiser import undo_organisation

        state_file = tmp_path / "organiser_state.json"
        undo_log = tmp_path / "organiser_undo.log"

        with (
            patch("src.core.organiser.state_file", state_file),
            patch("src.core.organiser.undo_log", undo_log),
        ):
            image_file = valid_source_dir / "photo.jpg"
            image_file.write_text("fake image")

            mock_image_info = ImageInfo(
                path=image_file,
                timestamp=datetime(2024, 1, 15, 14, 30, 45),
                lat=None,
                lon=None,
                location="New York, New York, US",
            )

            original_cwd = os.getcwd()
            try:
                os.chdir(str(tmp_path))

                # organise the photo
                with patch(
                    "src.core.organiser.get_image_info", return_value=mock_image_info
                ):
                    summary = isolate_state["organise_photos"](
                        str(valid_source_dir), str(valid_dest_dir)
                    )

                assert summary["processed"] == 1

                # Verify file is in organised location
                organised_path = (
                    Path(valid_dest_dir)
                    / "2024"
                    / "01"
                    / "15"
                    / "New York, New York, US"
                    / "photo.jpg"
                )
                assert organised_path.exists()
                assert not image_file.exists()

                # Perform undo
                undo_organisation(isolate_state["undo_log"])

                # Verify file is restored
                assert image_file.exists()
                assert not organised_path.exists()
            finally:
                os.chdir(original_cwd)

    @pytest.mark.parametrize(
        "undo_scenario",
        ["missing_destination", "missing_log", "log_parse_error"],
        ids=["missing_destination_file", "missing_log_file", "malformed_log_entry"],
    )
    def test_undo_error_scenarios(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        tmp_path,
        undo_scenario,
    ):
        """Test undo_organisation with various error conditions."""
        from src.core.organiser import undo_organisation

        original_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            if undo_scenario == "missing_destination":
                # organise a photo first
                image_file = valid_source_dir / "photo.jpg"
                image_file.write_text("fake image")
                mock_image_info = ImageInfo(
                    path=image_file,
                    timestamp=datetime(2024, 1, 15, 14, 30, 45),
                    lat=None,
                    lon=None,
                    location="New York, New York, US",
                )
                with patch(
                    "src.core.organiser.get_image_info", return_value=mock_image_info
                ):
                    summary = isolate_state["organise_photos"](
                        str(valid_source_dir), str(valid_dest_dir)
                    )
                assert summary["processed"] == 1

                # Delete the organised file
                organised_path = (
                    Path(valid_dest_dir)
                    / "2024"
                    / "01"
                    / "15"
                    / "New York, New York, US"
                    / "photo.jpg"
                )
                organised_path.unlink()

                # Undo should handle missing file gracefully
                undo_organisation()

            elif undo_scenario == "missing_log":
                # Log file doesn't exist - should not raise
                undo_organisation()

            elif undo_scenario == "log_parse_error":
                # Create a malformed log file
                undo_log = tmp_path / "organiser_undo.log"
                undo_log.write_text("not_a_valid_entry\n")

                # Should not raise, just skip invalid entries
                undo_organisation()

        finally:
            os.chdir(original_cwd)

    def test_undo_move_restore_error(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        tmp_path,
    ):
        """Test undo when file restoration fails."""
        from src.core.organiser import undo_organisation

        image_file = valid_source_dir / "photo.jpg"
        image_file.write_text("fake image")

        # mock_image_info1 and mock_image_info2 are not used in this test, remove them

        original_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            # organise the photo

            mock_image_info = ImageInfo(
                path=image_file,
                timestamp=datetime(2024, 1, 15, 14, 30, 45),
                lat=None,
                lon=None,
                location="New York, New York, US",
            )
            with patch(
                "src.core.organiser.get_image_info", return_value=mock_image_info
            ):
                summary = isolate_state["organise_photos"](
                    str(valid_source_dir), str(valid_dest_dir)
                )

            assert summary["processed"] == 1

            # Make source directory read-only to prevent restoration
            os.chmod(str(valid_source_dir), 0o444)

            # Undo should handle move error gracefully
            try:
                undo_organisation()
            finally:
                os.chmod(str(valid_source_dir), 0o755)
        finally:
            os.chdir(original_cwd)

    @pytest.mark.parametrize(
        "permission_error_type",
        ["save_state", "log_move"],
        ids=["save_state_permission", "log_move_permission"],
    )
    def test_permission_error_handling(
        self, suppress_logging, tmp_path, permission_error_type
    ):
        """Test handling of permission errors in state/log operations."""
        from src.core.organiser import _log_move, _save_state

        if permission_error_type == "save_state":
            state_file = tmp_path / "state.json"
            # Mock open to raise PermissionError
            with patch("builtins.open", side_effect=PermissionError("No permission")):
                _save_state({"test": "data"}, state_file)
            # File should not exist
            assert not state_file.exists()
        else:
            undo_log = tmp_path / "undo.log"
            # Mock open to raise PermissionError
            with patch("builtins.open", side_effect=PermissionError("No permission")):
                _log_move(Path("src.txt"), Path("dst.txt"), undo_log)
            # File should not exist
            assert not undo_log.exists()

    @pytest.mark.parametrize(
        "error_type,mock_patch",
        [
            (
                "state_file_corruption",
                lambda tmp_path: (
                    "builtins.open",
                    OSError("Access denied"),
                ),
            ),
            (
                "state_json_error",
                lambda tmp_path: (
                    "src.core.organiser.json.dump",
                    TypeError("Not serializable"),
                ),
            ),
            (
                "log_write_error",
                lambda tmp_path: (
                    "builtins.open",
                    TypeError("Cannot write"),
                ),
            ),
        ],
        ids=["load_state_oserror", "save_state_typeerror", "log_move_typeerror"],
    )
    def test_state_and_log_error_handling(
        self, suppress_logging, tmp_path, error_type, mock_patch
    ):
        """Test error handling in state and log operations."""
        from src.core.organiser import _load_state, _log_move, _save_state

        patch_target, error = mock_patch(tmp_path)

        if error_type == "state_file_corruption":
            state_file = tmp_path / "state.json"
            state_file.write_text('{"key": "value"}')
            with patch("builtins.open", side_effect=error):
                result = _load_state(state_file)
                assert result == {}

        elif error_type == "state_json_error":
            state_file = tmp_path / "state.json"
            with patch(patch_target, side_effect=error):
                # _save_state should handle TypeError gracefully and not raise
                _save_state({"test": "data"}, state_file)

        elif error_type == "log_write_error":
            undo_log = tmp_path / "undo.log"
            with patch(patch_target, side_effect=error):
                # _log_move should handle TypeError gracefully
                _log_move(Path("src.txt"), Path("dst.txt"), undo_log)

    def test_multiple_undo_entries(
        self,
        valid_source_dir,
        valid_dest_dir,
        suppress_logging,
        isolate_state,
        tmp_path,
    ):
        """Test undo with multiple entries in log."""
        from src.core.organiser import undo_organisation

        state_file = tmp_path / "organiser_state.json"
        undo_log = tmp_path / "organiser_undo.log"

        with (
            patch("src.core.organiser.state_file", state_file),
            patch("src.core.organiser.undo_log", undo_log),
        ):
            # Create multiple test images

            image1 = valid_source_dir / "photo1.jpg"
            image2 = valid_source_dir / "photo2.jpg"
            image1.write_text("fake image 1")
            image2.write_text("fake image 2")

            mock_image_info1 = ImageInfo(
                path=image1,
                timestamp=datetime(2024, 1, 15, 14, 30, 45),
                lat=None,
                lon=None,
                location="New York, New York, US",
            )
            mock_image_info2 = ImageInfo(
                path=image2,
                timestamp=datetime(2024, 1, 15, 14, 30, 45),
                lat=None,
                lon=None,
                location="New York, New York, US",
            )

            original_cwd = os.getcwd()
            try:
                os.chdir(str(tmp_path))

                # organise photos

                with patch(
                    "src.core.organiser.get_image_info",
                    side_effect=[mock_image_info1, mock_image_info2],
                ):
                    summary = isolate_state["organise_photos"](
                        str(valid_source_dir), str(valid_dest_dir)
                    )

                assert summary["processed"] == 2

                # Verify files are moved
                organised_dir = (
                    Path(valid_dest_dir)
                    / "2024"
                    / "01"
                    / "15"
                    / "New York, New York, US"
                )
                assert len(list(organised_dir.glob("*.jpg"))) == 2

                # Undo the operation
                undo_organisation(isolate_state["undo_log"])

                # Verify files are restored
                assert image1.exists()
                assert image2.exists()
                # Verify files are no longer in organised location
                assert len(list(organised_dir.glob("*.jpg"))) == 0
            finally:
                os.chdir(original_cwd)
