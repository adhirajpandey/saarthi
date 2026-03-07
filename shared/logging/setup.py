"""Logging configuration used by app and scripts."""

import logging
import logging.config
import os

from app.config.config import LOG_DATE_FORMAT, LOG_FILE, LOG_FORMAT, LOG_LEVEL


def setup_logging() -> None:
    """Configure logging for the application."""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": LOG_FORMAT,
                "datefmt": LOG_DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": LOG_LEVEL,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": LOG_LEVEL,
                "formatter": "default",
                "filename": LOG_FILE,
                "encoding": "utf8",
            },
        },
        "root": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
        },
        "loggers": {
            "uvicorn.error": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)


logger = logging.getLogger(__name__)
