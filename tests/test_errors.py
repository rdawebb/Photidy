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
        "error_class,message,parent_class",
        [
            (PhotidyError, "Test error message", Exception),
            (PhotoOrganisationError, "Organisation failed", PhotidyError),
            (PhotoMetadataError, "Metadata extraction failed", PhotidyError),
            (InvalidPhotoFormatError, "Unsupported format", PhotidyError),
            (InvalidDirectoryError, "Directory not found", PhotidyError),
        ],
        ids=[
            "PhotidyError",
            "PhotoOrganisationError",
            "PhotoMetadataError",
            "InvalidPhotoFormatError",
            "InvalidDirectoryError",
        ],
    )
    def test_error_instantiation_and_inheritance(
        self, error_class, message, parent_class
    ):
        """Test error instantiation, message handling, and inheritance."""
        # Test instantiation
        error = error_class(message)
        assert str(error) == message

        # Test inheritance
        assert issubclass(error_class, parent_class)

        # Test raising and catching
        with pytest.raises(error_class):
            raise error_class("Test")

        # Test catching as parent class (except for PhotidyError which has no parent with PhotidyError)
        if error_class != PhotidyError:
            with pytest.raises(parent_class):
                raise error_class("Test")


class TestPhotidyErrorBase:
    """Additional tests for base PhotidyError."""

    def test_photidy_error_is_exception(self):
        """Test that PhotidyError is an Exception."""
        assert issubclass(PhotidyError, Exception)
