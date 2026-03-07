"""Application settings builder."""

from logging import error, info

from app.models import BaseConfig, GeofenceConfig, RateLimitingConfig, SharedConfig
from app.config.config import (
    APP_NAME,
    GEOFENCE_EMAIL_TEMPLATE,
    GEOFENCE_SUBJECT_TEMPLATE,
    RATE_LIMIT_DEFAULT,
)
from shared.config.env import get_env


def _optional_env(name: str) -> str | None:
    """Read an optional environment variable."""
    value = get_env(name, required=False)
    if not value:
        info(f"{name} environment variable not set.")
    return value


def _required_env(name: str) -> str:
    """Get environment variable, logging if missing."""
    value = get_env(name, required=False)
    if not value:
        error(f"{name} environment variable not set.")
        raise SystemExit(f"{name} environment variable not set.")
    return value


def load_configuration() -> SharedConfig:
    """Build configuration from defaults and environment variables."""
    admin_token = _required_env("ADMIN_TOKEN")
    geofence_recipient = _optional_env("GEOFENCE_UPDATES_RECIPIENT")
    geofence_sender_name = _optional_env("GEOFENCE_SENDER_NAME")

    return SharedConfig(
        base=BaseConfig(app_name=APP_NAME),
        rate_limiting=RateLimitingConfig(default_limit=RATE_LIMIT_DEFAULT),
        admin_token=admin_token,
        geofence=GeofenceConfig(
            email_template=GEOFENCE_EMAIL_TEMPLATE,
            subject_template=GEOFENCE_SUBJECT_TEMPLATE,
            recipient=geofence_recipient,
            sender_name=geofence_sender_name,
        ),
    )
