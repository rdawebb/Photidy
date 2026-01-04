"""Pytest configuration and shared fixtures."""

import logging
from datetime import datetime
from unittest.mock import Mock, patch

import pytest


_temp_db_path = None


def pytest_configure(config):
    """Pytest hook to configure test environment before tests run"""
    import tempfile

    global _temp_db_path

    temp_dir = tempfile.mkdtemp()
    db_file_path = f"{temp_dir}/places_v0.1.db"

    with open(db_file_path, "wb") as f:
        f.write(b"mock database content")

    _temp_db_path = db_file_path

    def mock_db_path_func():
        from pathlib import Path

        return Path(_temp_db_path)

    patcher = patch("runtime.paths.db_path", side_effect=mock_db_path_func)
    patcher.start()


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


@pytest.fixture
def mock_db_path(tmp_path):
    """Fixture that mocks the database path to return a temporary file.

    Note: This fixture is for cases where you need a fresh temporary database.
    By default, db_path is already patched globally via pytest_configure hook.
    """
    db_file = tmp_path / "places_v0.1.db"
    db_file.write_bytes(b"mock database content")

    with patch("runtime.paths.db_path", return_value=db_file):
        yield db_file


@pytest.fixture
def mock_rust():
    """Create a configurable mock Rust object."""
    rust = Mock()
    rust.db_filename.return_value = "test.db"
    rust.validate_db.return_value = True
    return rust


@pytest.fixture
def metadata_scenarios():
    """Fixture providing metadata results for different scenarios."""
    return {
        "complete": {
            "path": "test.jpg",
            "timestamp": "2024-01-15T14:30:45+00:00",
            "lat": 40.5,
            "lon": -74.0,
            "location": "New York, New York, US",
        },
        "date_only": {
            "path": "test.jpg",
            "timestamp": "2024-01-15T14:30:45+00:00",
            "lat": None,
            "lon": None,
            "location": "Unknown Location",
        },
        "location_only": {
            "path": "test.jpg",
            "timestamp": None,
            "lat": 40.5,
            "lon": -74.0,
            "location": "New York, New York, US",
        },
        "no_exif": {
            "path": "test.jpg",
            "timestamp": None,
            "lat": None,
            "lon": None,
            "location": "Unknown Location",
        },
    }


@pytest.fixture
def mock_image_info_complete():
    """Fixture providing complete image info for testing."""
    return {
        "path": "test.jpg",
        "timestamp": datetime(2024, 1, 15, 14, 30, 45),
        "location": "New York, New York, US",
    }


@pytest.fixture
def supported_image_formats():
    """List of supported image formats."""
    return (".jpg", ".jpeg", ".png", ".tiff", ".raw", ".cr2", ".heic")


@pytest.fixture
def logging_levels():
    """Dictionary of standard logging levels."""
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }


@pytest.fixture
def error_classes_data():
    """Fixture providing error class test data."""
    from src.utils.errors import (
        InvalidDirectoryError,
        InvalidPhotoFormatError,
        PhotoMetadataError,
        PhotoOrganisationError,
        PhotidyError,
    )

    return [
        (PhotidyError, Exception, "Test error message"),
        (PhotoOrganisationError, PhotidyError, "Organisation failed"),
        (PhotoMetadataError, PhotidyError, "Metadata extraction failed"),
        (InvalidPhotoFormatError, PhotidyError, "Unsupported format"),
        (InvalidDirectoryError, PhotidyError, "Directory not found"),
    ]


@pytest.fixture
def isolate_state(tmp_path):
    """Isolate organiser state to a temporary directory for testing.

    This fixture provides a wrapped organise_photos function that automatically
    uses temporary state and undo log paths, avoiding state pollution.
    """
    from src.core.organiser import organise_photos as _organise_photos

    # Create temporary state files
    temp_state_file = tmp_path / "organiser_state.json"
    temp_undo_log = tmp_path / "organiser_undo.log"

    def organise_photos_isolated(source_dir, dest_dir):
        """Wrapper that calls organise_photos with isolated state files."""
        return _organise_photos(
            source_dir,
            dest_dir,
            state_file=temp_state_file,
            undo_log=temp_undo_log,
        )

    def clear_state():
        """Clear the isolated state files."""
        if temp_state_file.exists():
            temp_state_file.unlink()
        if temp_undo_log.exists():
            temp_undo_log.unlink()

    # Provide both the wrapper function and state file paths
    yield {
        "organise_photos": organise_photos_isolated,
        "state_file": temp_state_file,
        "undo_log": temp_undo_log,
        "clear_state": clear_state,
    }
