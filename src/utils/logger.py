"""Centralised logging setup for the Photidy application."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, TextIO

from src.utils.paths import LOG_DIR


class CustomRotatingFileHandler(RotatingFileHandler):
    """Custom rotating file handler that closes and reopens the stream after rollover."""

    def doRollover(self) -> None:
        """Close the current stream and reopen it after rollover."""
        if self.stream:
            self.stream.close()
            self.stream = None

        # Rename current log file and rotate backups
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}"
                dfn = f"{self.baseFilename}.{i + 1}"
                if os.path.exists(sfn):
                    os.rename(sfn, dfn)
            os.rename(self.baseFilename, f"{self.baseFilename}.1")

        # Reopen the stream after rollover
        self.mode = "a"
        self.stream = self._open()


def get_logger(name: str, log_dir: Optional[Path] = None) -> logging.Logger:
    """Get a configured logger with console and file handlers.

    Log files are rotated when they reach 1 MB, with up to 5 backups.

    Args:
        name (str): The name of the logger.
        log_dir (Path, optional): Directory to store log files, defaults to 'logs' in the project root.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger: logging.Logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level=logging.DEBUG)

        console_handler: logging.StreamHandler[TextIO] = logging.StreamHandler()
        console_handler.setLevel(level=logging.ERROR)

        if log_dir is None:
            env_log_dir: str | None = os.getenv(key="PHOTIDY_LOG_DIR")
            if env_log_dir:
                log_dir = Path(env_log_dir)
            else:
                log_dir: Path = LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = CustomRotatingFileHandler(
            filename=log_dir / "photidy.log", maxBytes=1 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler.setFormatter(fmt=formatter)
        file_handler.setFormatter(fmt=formatter)

        logger.addHandler(hdlr=console_handler)
        logger.addHandler(hdlr=file_handler)
        logger.propagate = False

    return logger


def configure_logging(level=logging.INFO) -> None:
    """Configure the root logger.

    Args:
        level (int): Logging level.
    """
    logging.getLogger(name="photidy").setLevel(level)
