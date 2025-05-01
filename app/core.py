from slowapi import Limiter
from slowapi.util import get_remote_address
from .config import CONFIG
from logging import FileHandler, StreamHandler, basicConfig, root, info

# --- Logging Setup ---


def setup_logging():
    """Sets up logging configuration."""
    log_config = CONFIG.logging
    log_level = log_config.level
    log_format = log_config.format
    log_file = log_config.log_file
    if root.handlers:
        info("Root logger already has handlers configured.")
    else:
        info("Root logger has no handlers, basicConfig should work.")
    basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            FileHandler(log_file),
            StreamHandler(),
        ],
    )
    info(f"Logging initialized with level: {log_level}")


limiter = Limiter(key_func=get_remote_address)
info("Rate limiter initialized.")

logger = root
info("Logger initialized.")
