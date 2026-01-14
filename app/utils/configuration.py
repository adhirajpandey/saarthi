"""Configuration loader for the application.

Combines static config from config.py with secrets from environment variables.
"""

import os
from dotenv import load_dotenv
from logging import info, error

from ..models import (
    SharedConfig,
    BaseConfig,
    JWTConfig,
    RateLimitingConfig,
    ProvidersConfig,
    AIServiceConfig,
    GeofenceConfig,
)
from config import (
    APP_NAME,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_CHAT,
    AI_MODELS,
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


def _build_provider(endpoint: str | None, api_key: str | None) -> dict | None:
    """Build provider config dict, or None if missing."""
    if endpoint and api_key:
        return {"base_url": endpoint, "api_key": api_key}
    return None


def load_configuration() -> SharedConfig:
    """Load configuration from Python config and environment variables."""
    load_dotenv()

    # Required secrets
    jwt_secret_key = _get_env("JWT_SECRET_KEY", required=True)

    # Optional secrets
    openai_api_key = _get_env("OPENAI_API_KEY")
    google_drive_search_webhook_url = _get_env("GOOGLE_DRIVE_SEARCH_WEBHOOK_URL")
    admin_token = _get_env("ADMIN_TOKEN")
    geofence_recipient = _get_env("GEOFENCE_UPDATES_RECIPIENT")
    geofence_sender_name = _get_env("GEOFENCE_SENDER_NAME")

    # Provider credentials
    providers_config = ProvidersConfig(
        ollama=_build_provider(
            _get_env("OLLAMA_DELL_WORK_ENDPOINT"),
            _get_env("OLLAMA_DELL_WORK_API_KEY"),
        ),
        gemini=_build_provider(
            _get_env("GEMINI_ENDPOINT"),
            _get_env("GEMINI_API_KEY"),
        ),
        openrouter=_build_provider(
            _get_env("OPENROUTER_ENDPOINT"),
            _get_env("OPENROUTER_API_KEY"),
        ),
    )

    return SharedConfig(
        base=BaseConfig(app_name=APP_NAME),
        jwt=JWTConfig(
            secret_key=jwt_secret_key,
            algorithm=JWT_ALGORITHM,
            access_token_expire_minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        ),
        rate_limiting=RateLimitingConfig(
            default_limit=RATE_LIMIT_DEFAULT,
            login_limit=RATE_LIMIT_LOGIN,
            chat_limit=RATE_LIMIT_CHAT,
        ),
        ai_service=AIServiceConfig(
            models=AI_MODELS,
            providers=providers_config,
            openai_api_key=openai_api_key,
            google_drive_search_webhook_url=google_drive_search_webhook_url,
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
