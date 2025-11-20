"""Custom exceptions for the Photidy application."""


class PhotidyError(Exception):
    """Base exception for Photidy errors."""

    pass


class PhotoOrganisationError(PhotidyError):
    """Custom exception for photo organisation errors."""

    pass


class PhotoMetadataError(PhotidyError):
    """Raised when photo metadata cannot be extracted."""

    pass


class InvalidPhotoFormatError(PhotidyError):
    """Raised when a photo has an unsupported format."""

    pass


class InvalidDirectoryError(PhotidyError):
    """Raised when a specified directory is invalid or inaccessible."""

    pass
