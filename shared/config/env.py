"""Environment variable loading and access helpers."""

import os

from dotenv import load_dotenv

_ENV_LOADED = False


def load_environment() -> None:
    """Load .env values once per process."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv()
    _ENV_LOADED = True


def get_env(name: str, required: bool = False) -> str | None:
    """Read an environment variable."""
    value = os.getenv(name)
    if required and not value:
        raise ValueError(f"{name} environment variable not set.")
    return value

