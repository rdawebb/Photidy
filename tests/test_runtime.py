"""Tests for src/runtime modules: db_runtime, extraction, paths."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import src.runtime.db_runtime as db_runtime
import src.runtime.extraction as extraction
import src.runtime.paths as paths


class TestDbRuntime:
    """Tests for db_runtime module"""

    def test_runtime_db_path_returns_correct_path(
        self, mock_rust, suppress_logging, tmp_path
    ):
        """Test that runtime_db_path returns the correct path"""
        user_data = tmp_path / "userdata"
        with patch("src.runtime.db_runtime.user_data_path", return_value=user_data):
            result = db_runtime.runtime_db_path(mock_rust)
            assert result == user_data / "test.db"

    @pytest.mark.parametrize(
        "path_exists,is_valid,should_extract,should_unlink",
        [
            (True, True, False, False),
            (True, False, True, True),
            (False, True, True, False),
        ],
        ids=["path_exists_valid", "path_exists_invalid", "path_not_exists"],
    )
    def test_ensure_db(
        self,
        mock_rust,
        suppress_logging,
        path_exists,
        is_valid,
        should_extract,
        should_unlink,
    ):
        """Test ensure_db with different path and validation states."""
        path = MagicMock(spec=Path)
        path.exists.return_value = path_exists

        with (
            patch("src.runtime.db_runtime.runtime_db_path", return_value=path),
            patch("src.runtime.db_runtime.extract_embedded_db") as mock_extract,
        ):
            if is_valid:
                mock_rust.validate_db.return_value = True
            else:
                mock_rust.validate_db.side_effect = [Exception("fail"), True]

            result = db_runtime.ensure_db(mock_rust)

            if should_unlink:
                path.unlink.assert_called_once()
            if should_extract:
                mock_extract.assert_called_once_with(path)

            assert result == path


class TestExtraction:
    """Tests for extraction module"""

    def test_extract_embedded_db_copies_file(self, suppress_logging, tmp_path):
        """Test that extract_embedded_db copies the embedded database file to the destination"""
        from contextlib import contextmanager

        dest = tmp_path / "test.db"
        mock_src = tmp_path / "source.db"

        @contextmanager
        def mock_as_file(_):
            yield mock_src

        with (
            patch("src.runtime.extraction.resources.files") as mock_files,
            patch("src.runtime.extraction.resources.as_file", side_effect=mock_as_file),
            patch("shutil.copyfile") as mock_copyfile,
        ):
            mock_files.return_value.__truediv__.return_value = mock_src
            extraction.extract_embedded_db(dest)
            mock_copyfile.assert_called_once_with(mock_src, dest)


class TestPaths:
    """Tests for paths module"""

    def test_user_data_path_creates_and_returns_path(self, suppress_logging, tmp_path):
        """Test that user_data_path creates the directory and returns the correct path"""
        user_data = tmp_path / "userdata"
        with patch("src.runtime.paths.user_data_dir", return_value=str(user_data)):
            with patch.object(Path, "mkdir") as mock_mkdir:
                result = paths.user_data_path()
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                assert result == user_data
