"""Application settings builder."""

from logging import error, info

from app.models import BaseConfig, GeofenceConfig, RateLimitingConfig, SharedConfig
from config import APP_NAME, GEOFENCE_EMAIL_TEMPLATE, GEOFENCE_SUBJECT_TEMPLATE, RATE_LIMIT_DEFAULT
from shared.config.env import get_env, load_environment


def _get_env(name: str, required: bool = False) -> str | None:
    """Get environment variable, logging if missing."""
    value = get_env(name, required=False)
    if not value:
        if required:
            error(f"{name} environment variable not set.")
            raise SystemExit(f"{name} environment variable not set.")
        info(f"{name} environment variable not set.")
    return value


def load_configuration() -> SharedConfig:
    """Load configuration from static config and environment variables."""
    load_environment()

    admin_token = _get_env("ADMIN_TOKEN", required=True)
    geofence_recipient = _get_env("GEOFENCE_UPDATES_RECIPIENT")
    geofence_sender_name = _get_env("GEOFENCE_SENDER_NAME")

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


CONFIG = load_configuration()

