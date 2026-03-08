"""Logging configuration used by app and scripts."""

import logging
import logging.config
import os

from shared.settings import LoggingSettings


def setup_logging(settings: LoggingSettings | None = None) -> None:
    """Configure logging for the application."""
    resolved_settings = settings or LoggingSettings()
    log_dir = os.path.dirname(resolved_settings.file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": resolved_settings.format,
                "datefmt": resolved_settings.date_format,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": resolved_settings.level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": resolved_settings.level,
                "formatter": "default",
                "filename": resolved_settings.file,
                "encoding": "utf8",
            },
        },
        "root": {
            "level": resolved_settings.level,
            "handlers": ["console", "file"],
        },
        "loggers": {
            "uvicorn.error": {
                "level": resolved_settings.level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": resolved_settings.level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)


logger = logging.getLogger(__name__)
