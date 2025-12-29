"""Tests for src/runtime modules: db_runtime, extraction, paths."""

from unittest.mock import patch

import runtime.extraction as extraction
import runtime.paths as paths


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
            patch("runtime.extraction.resources.files") as mock_files,
            patch("runtime.extraction.resources.as_file", side_effect=mock_as_file),
            patch("shutil.copyfile") as mock_copyfile,
        ):
            mock_files.return_value.__truediv__.return_value = mock_src
            extraction.extract_db(dest)
            mock_copyfile.assert_called_once_with(mock_src, dest)


class TestPaths:
    """Tests for paths module"""

    def test_runtime_root(self):
        """Test that runtime_root returns the correct path"""
        root = paths.runtime_root()
        assert root.exists()
        assert root.is_dir()
