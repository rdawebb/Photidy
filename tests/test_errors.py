"""Tests for custom exceptions in src/utils/errors.py"""

import pytest

from src.utils.errors import (
    InvalidDirectoryError,
    InvalidPhotoFormatError,
    PhotoMetadataError,
    PhotoOrganisationError,
    PhotidyError,
)


class TestPhotidyError:
    """Test the base PhotidyError exception."""

    def test_photidy_error_instantiation(self):
        """Test that PhotidyError can be instantiated."""
        error = PhotidyError("Test error message")
        assert str(error) == "Test error message"

    def test_photidy_error_can_be_raised(self):
        """Test that PhotidyError can be raised and caught."""
        with pytest.raises(PhotidyError):
            raise PhotidyError("Test error")

    def test_photidy_error_is_exception(self):
        """Test that PhotidyError is an Exception."""
        assert issubclass(PhotidyError, Exception)


class TestPhotoOrganisationError:
    """Test PhotoOrganisationError exception."""

    def test_instantiation(self):
        """Test PhotoOrganisationError instantiation."""
        error = PhotoOrganisationError("Organisation failed")
        assert str(error) == "Organisation failed"

    def test_inherits_from_photidy_error(self):
        """Test that PhotoOrganisationError inherits from PhotidyError."""
        assert issubclass(PhotoOrganisationError, PhotidyError)

    def test_can_be_raised_and_caught(self):
        """Test raising and catching PhotoOrganisationError."""
        with pytest.raises(PhotoOrganisationError):
            raise PhotoOrganisationError("Test")

    def test_caught_as_photidy_error(self):
        """Test that PhotoOrganisationError can be caught as PhotidyError."""
        with pytest.raises(PhotidyError):
            raise PhotoOrganisationError("Test")


class TestPhotoMetadataError:
    """Test PhotoMetadataError exception."""

    def test_instantiation(self):
        """Test PhotoMetadataError instantiation."""
        error = PhotoMetadataError("Metadata extraction failed")
        assert str(error) == "Metadata extraction failed"

    def test_inherits_from_photidy_error(self):
        """Test that PhotoMetadataError inherits from PhotidyError."""
        assert issubclass(PhotoMetadataError, PhotidyError)

    def test_can_be_raised_and_caught(self):
        """Test raising and catching PhotoMetadataError."""
        with pytest.raises(PhotoMetadataError):
            raise PhotoMetadataError("Test")

    def test_caught_as_photidy_error(self):
        """Test that PhotoMetadataError can be caught as PhotidyError."""
        with pytest.raises(PhotidyError):
            raise PhotoMetadataError("Test")


class TestInvalidPhotoFormatError:
    """Test InvalidPhotoFormatError exception."""

    def test_instantiation(self):
        """Test InvalidPhotoFormatError instantiation."""
        error = InvalidPhotoFormatError("Unsupported format")
        assert str(error) == "Unsupported format"

    def test_inherits_from_photidy_error(self):
        """Test that InvalidPhotoFormatError inherits from PhotidyError."""
        assert issubclass(InvalidPhotoFormatError, PhotidyError)

    def test_can_be_raised_and_caught(self):
        """Test raising and catching InvalidPhotoFormatError."""
        with pytest.raises(InvalidPhotoFormatError):
            raise InvalidPhotoFormatError("Test")

    def test_caught_as_photidy_error(self):
        """Test that InvalidPhotoFormatError can be caught as PhotidyError."""
        with pytest.raises(PhotidyError):
            raise InvalidPhotoFormatError("Test")


class TestInvalidDirectoryError:
    """Test InvalidDirectoryError exception."""

    def test_instantiation(self):
        """Test InvalidDirectoryError instantiation."""
        error = InvalidDirectoryError("Directory not found")
        assert str(error) == "Directory not found"

    def test_inherits_from_photidy_error(self):
        """Test that InvalidDirectoryError inherits from PhotidyError."""
        assert issubclass(InvalidDirectoryError, PhotidyError)

    def test_can_be_raised_and_caught(self):
        """Test raising and catching InvalidDirectoryError."""
        with pytest.raises(InvalidDirectoryError):
            raise InvalidDirectoryError("Test")

    def test_caught_as_photidy_error(self):
        """Test that InvalidDirectoryError can be caught as PhotidyError."""
        with pytest.raises(PhotidyError):
            raise InvalidDirectoryError("Test")
