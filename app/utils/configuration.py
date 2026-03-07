"""Configuration loader for the application.

Combines static config from config.py with secrets from environment variables.
"""

import os
from dotenv import load_dotenv
from logging import info, error

from ..models import (
    SharedConfig,
    BaseConfig,
    RateLimitingConfig,
    GeofenceConfig,
)
from config import (
    APP_NAME,
    RATE_LIMIT_DEFAULT,
    GEOFENCE_EMAIL_TEMPLATE,
    GEOFENCE_SUBJECT_TEMPLATE,
)


def _get_env(name: str, required: bool = False) -> str | None:
    """Get environment variable, logging if missing."""
    value = os.getenv(name)
    if not value:
        if required:
            error(f"{name} environment variable not set.")
            raise SystemExit(f"{name} environment variable not set.")
        info(f"{name} environment variable not set.")
    return value


def load_configuration() -> SharedConfig:
    """Load configuration from Python config and environment variables."""
    load_dotenv()

    # Required secrets
    admin_token = _get_env("ADMIN_TOKEN", required=True)

    # Optional secrets
    geofence_recipient = _get_env("GEOFENCE_UPDATES_RECIPIENT")
    geofence_sender_name = _get_env("GEOFENCE_SENDER_NAME")

    return SharedConfig(
        base=BaseConfig(app_name=APP_NAME),
        rate_limiting=RateLimitingConfig(
            default_limit=RATE_LIMIT_DEFAULT,
        ),
        admin_token=admin_token,
        geofence=GeofenceConfig(
            email_template=GEOFENCE_EMAIL_TEMPLATE,
            subject_template=GEOFENCE_SUBJECT_TEMPLATE,
            recipient=geofence_recipient,
            sender_name=geofence_sender_name,
        ),
    )


# Initialize configuration at module import
CONFIG = load_configuration()
