"""Tests for custom exceptions in src/utils/errors.py"""

import pytest

from src.utils.errors import (
    InvalidDirectoryError,
    InvalidPhotoFormatError,
    PhotoMetadataError,
    PhotoOrganisationError,
    PhotidyError,
)


class TestCustomErrors:
    """Test custom exception behavior."""

    @pytest.mark.parametrize(
        "error_class,message",
        [
            (PhotidyError, "Test error message"),
            (PhotoOrganisationError, "Organisation failed"),
            (PhotoMetadataError, "Metadata extraction failed"),
            (InvalidPhotoFormatError, "Unsupported format"),
            (InvalidDirectoryError, "Directory not found"),
        ],
        ids=[
            "PhotidyError",
            "PhotoOrganisationError",
            "PhotoMetadataError",
            "InvalidPhotoFormatError",
            "InvalidDirectoryError",
        ],
    )
    def test_error_instantiation(self, error_class, message):
        """Test that custom errors can be instantiated with messages."""
        error = error_class(message)
        assert str(error) == message

    @pytest.mark.parametrize(
        "error_class,parent_class",
        [
            (PhotidyError, Exception),
            (PhotoOrganisationError, PhotidyError),
            (PhotoMetadataError, PhotidyError),
            (InvalidPhotoFormatError, PhotidyError),
            (InvalidDirectoryError, PhotidyError),
        ],
        ids=[
            "PhotidyError",
            "PhotoOrganisationError",
            "PhotoMetadataError",
            "InvalidPhotoFormatError",
            "InvalidDirectoryError",
        ],
    )
    def test_error_inheritance(self, error_class, parent_class):
        """Test that custom errors inherit correctly."""
        assert issubclass(error_class, parent_class)

    @pytest.mark.parametrize(
        "error_class",
        [
            PhotidyError,
            PhotoOrganisationError,
            PhotoMetadataError,
            InvalidPhotoFormatError,
            InvalidDirectoryError,
        ],
        ids=[
            "PhotidyError",
            "PhotoOrganisationError",
            "PhotoMetadataError",
            "InvalidPhotoFormatError",
            "InvalidDirectoryError",
        ],
    )
    def test_error_can_be_raised_and_caught(self, error_class):
        """Test that custom errors can be raised and caught."""
        with pytest.raises(error_class):
            raise error_class("Test")

    @pytest.mark.parametrize(
        "error_class,parent_class",
        [
            (PhotoOrganisationError, PhotidyError),
            (PhotoMetadataError, PhotidyError),
            (InvalidPhotoFormatError, PhotidyError),
            (InvalidDirectoryError, PhotidyError),
        ],
        ids=[
            "PhotoOrganisationError",
            "PhotoMetadataError",
            "InvalidPhotoFormatError",
            "InvalidDirectoryError",
        ],
    )
    def test_error_caught_as_parent_class(self, error_class, parent_class):
        """Test that custom errors can be caught as parent class."""
        with pytest.raises(parent_class):
            raise error_class("Test")


class TestPhotidyErrorBase:
    """Additional tests for base PhotidyError."""

    def test_photidy_error_is_exception(self):
        """Test that PhotidyError is an Exception."""
        assert issubclass(PhotidyError, Exception)
