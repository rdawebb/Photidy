"""Tests for logging setup in src/utils/logger.py"""

import logging
from pathlib import Path

import pytest

from src.utils.logger import configure_logging, get_logger


class TestGetLogger:
    """Test get_logger function."""

    def test_returns_logger_with_correct_name(self):
        """Test that get_logger returns a logger with the correct name."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)

    def test_logger_has_handlers(self):
        """Test that returned logger has handlers configured."""
        logger = get_logger("test_module_handlers")
        assert len(logger.handlers) > 0

    @pytest.mark.parametrize(
        "handler_type,expected_level",
        [
            ("console", logging.ERROR),
            ("file", logging.DEBUG),
        ],
        ids=["console_info", "file_debug"],
    )
    def test_logger_handler_configuration(self, handler_type, expected_level):
        """Test that logger has both console and file handlers with correct levels."""
        logger_name = f"test_{handler_type}_config"
        logger = get_logger(logger_name)

        if handler_type == "console":
            # Test console handler exists
            console_handlers = [
                h
                for h in logger.handlers
                if isinstance(h, logging.StreamHandler)
                and not isinstance(h, logging.FileHandler)
            ]
            assert len(console_handlers) > 0, "Missing console handler"
            if console_handlers:
                assert console_handlers[0].level == expected_level

        elif handler_type == "file":
            # Test file handler exists
            file_handlers = [
                h for h in logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) > 0, "Missing file handler"
            if file_handlers:
                assert file_handlers[0].level == expected_level
                # Verify log directory exists
                log_path = Path(file_handlers[0].baseFilename)
                assert log_path.parent.exists()
                assert log_path.parent.name == "logs"

    def test_logger_level_is_debug(self):
        """Test that logger itself is set to DEBUG level."""
        logger = get_logger("test_logger_level")
        assert logger.level == logging.DEBUG

    def test_idempotency_handlers_not_duplicated(self):
        """Test that calling get_logger twice doesn't duplicate handlers."""
        logger_name = "test_idempotent"
        # Clear any existing loggers with this name
        if logger_name in logging.Logger.manager.loggerDict:
            del logging.Logger.manager.loggerDict[logger_name]

        logger1 = get_logger(logger_name)
        handler_count_first = len(logger1.handlers)

        logger2 = get_logger(logger_name)
        handler_count_second = len(logger2.handlers)

        assert handler_count_first == handler_count_second
        assert logger1 is logger2

    def test_formatter_is_applied(self):
        """Test that formatters are applied to handlers."""
        logger = get_logger("test_formatter")
        for handler in logger.handlers:
            assert handler.formatter is not None
            assert "%(asctime)s" in handler.formatter._fmt
            assert "%(name)s" in handler.formatter._fmt
            assert "%(levelname)s" in handler.formatter._fmt
            assert "%(message)s" in handler.formatter._fmt

    def test_same_logger_instance_returned(self):
        """Test that multiple calls return the same logger instance."""
        logger1 = get_logger("test_same_instance")
        logger2 = get_logger("test_same_instance")
        assert logger1 is logger2


class TestConfigureLogging:
    """Test configure_logging function."""

    def test_configure_logging_with_default_level(self):
        """Test configure_logging sets correct default level."""
        configure_logging()
        root_logger = logging.getLogger("photidy")
        # Should be at least INFO level
        assert root_logger.level >= logging.INFO

    @pytest.mark.parametrize(
        "level",
        [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
        ids=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    def test_configure_logging_levels(self, level):
        """Test configure_logging with various logging levels."""
        configure_logging(level=level)
        photidy_logger = logging.getLogger("photidy")
        assert photidy_logger.level == level

    def test_configure_logging_affects_photidy_logger(self):
        """Test that configure_logging affects the 'photidy' logger."""
        configure_logging(level=logging.CRITICAL)
        logger = logging.getLogger("photidy")
        assert logger.level == logging.CRITICAL
