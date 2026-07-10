"""Logging configuration used by app and scripts."""

import logging
import logging.config
import os

from shared.settings import LoggingSettings

DEFAULT_LOGGING_SETTINGS = LoggingSettings(
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    date_format="%Y-%m-%d %H:%M:%S",
    file="logs/app.log",
)


def setup_logging(
    settings: LoggingSettings | None = None,
    include_file: bool = True,
) -> None:
    """Configure logging for the application."""
    resolved_settings = settings or DEFAULT_LOGGING_SETTINGS
    if include_file:
        log_dir = os.path.dirname(resolved_settings.file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": resolved_settings.level,
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    }
    root_handlers = ["console"]
    if include_file:
        handlers["file"] = {
            "class": "logging.FileHandler",
            "level": resolved_settings.level,
            "formatter": "default",
            "filename": resolved_settings.file,
            "encoding": "utf8",
        }
        root_handlers.append("file")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": resolved_settings.format,
                "datefmt": resolved_settings.date_format,
            },
        },
        "handlers": handlers,
        "root": {
            "level": resolved_settings.level,
            "handlers": root_handlers,
        },
        "loggers": {
            "uvicorn.error": {
                "level": resolved_settings.level,
                "handlers": root_handlers,
                "propagate": False,
            },
            "uvicorn.access": {
                "level": resolved_settings.level,
                "handlers": root_handlers,
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)
