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


class DatabaseError(PhotidyError):
    """Raised when there is a database-related error."""

    pass


class DataSourceError(PhotidyError):
    """Raised when there is an error with the data source."""

    pass


class CSVParsingError(PhotidyError):
    """Raised when there is an error parsing a CSV file."""

    pass
