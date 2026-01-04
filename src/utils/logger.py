"""Centralised logging setup for the Photidy application."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str, log_dir: Path = None) -> logging.Logger:
    """Get a configured logger with console and file handlers.

    Log files are rotated when they reach 1 MB, with up to 5 backups.

    Args:
        name (str): The name of the logger.
        log_dir (Path, optional): Directory to store log files, defaults to 'logs' in the project root.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)

        if log_dir is None:
            env_log_dir = os.getenv("PHOTIDY_LOG_DIR")
            if env_log_dir:
                log_dir = Path(env_log_dir)
            else:
                log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_dir / "photidy.log", maxBytes=1 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.propagate = False

    return logger


def configure_logging(level=logging.INFO) -> None:
    """Configure the root logger.

    Args:
        level (int): Logging level.
    """
    logging.getLogger("photidy").setLevel(level)
