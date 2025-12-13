"""Pytest configuration and shared fixtures."""

import logging
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def source_dir(tmp_path):
    """Create a temporary source directory."""
    return tmp_path / "source"


@pytest.fixture
def dest_dir(tmp_path):
    """Create a temporary destination directory."""
    return tmp_path / "destination"


@pytest.fixture
def valid_source_dir(tmp_path):
    """Create a valid source directory."""
    source = tmp_path / "source"
    source.mkdir()
    return source


@pytest.fixture
def valid_dest_dir(tmp_path):
    """Create a valid destination directory."""
    dest = tmp_path / "destination"
    dest.mkdir()
    return dest


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger to avoid file I/O during tests."""
    mock_log = Mock(spec=logging.Logger)
    mock_log.info = Mock()
    mock_log.debug = Mock()
    mock_log.warning = Mock()
    mock_log.error = Mock()
    return mock_log


@pytest.fixture
def mock_exif_tags():
    """Create mock EXIF tags dictionary."""
    return {
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


@pytest.fixture
def mock_image_file(tmp_path):
    """Create a mock image file."""
    image_file = tmp_path / "test_image.jpg"
    image_file.write_bytes(b"fake image data")
    return image_file


@pytest.fixture
def suppress_logging():
    """Suppress logging during tests."""
    logging.getLogger("src.core.metadata").setLevel(logging.CRITICAL)
    logging.getLogger("src.core.organiser").setLevel(logging.CRITICAL)
    logging.getLogger("src.utils.logger").setLevel(logging.CRITICAL)
    yield
    logging.getLogger("src.core.metadata").setLevel(logging.DEBUG)
    logging.getLogger("src.core.organiser").setLevel(logging.DEBUG)
    logging.getLogger("src.utils.logger").setLevel(logging.DEBUG)
