import os
import yaml
from dotenv import load_dotenv
from typing import Dict, Any
from .models import (
    SharedConfig,
    BaseConfig,
    JWTConfig,
    AIServiceConfig,
)
from logging import info, error


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, "r") as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config is None:  # Handle empty YAML file
                yaml_config = {}
    except FileNotFoundError:
        error(f"ERROR: Configuration file not found at {config_path}")
        raise SystemExit(1)
    except yaml.YAMLError as e:
        error(f"ERROR: Error parsing configuration file {config_path}: {e}")
        raise SystemExit(1)
    return yaml_config


def load_configuration(yaml_file_path: str) -> SharedConfig:
    """Loads configuration from YAML file and environment variables."""
    yaml_config = load_yaml_config(yaml_file_path)
    load_dotenv()

    # Validate required environment variables
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", None)
    if not jwt_secret_key:
        error("ERROR: JWT_SECRET_KEY environment variable not set.")
        raise SystemExit("JWT_SECRET_KEY environment variable not set.")

    openai_api_key = os.getenv("OPENAI_API_KEY", None)
    if not openai_api_key:
        info("ERROR: OPENAI_API_KEY environment variable not set.")

    google_drive_search_webhook_url = os.getenv("GOOGLE_DRIVE_SEARCH_WEBHOOK_URL", None)
    if not google_drive_search_webhook_url:
        info("ERROR: GOOGLE_DRIVE_SEARCH_WEBHOOK_URL environment variable not set.")

    base_config = BaseConfig(**yaml_config.get("base", {}))
    jwt_config_data = yaml_config.get("jwt", {})
    jwt_config_data["secret_key"] = jwt_secret_key
    jwt_config = JWTConfig(**jwt_config_data)

    ai_service_config_data = yaml_config.get("ai_service", {})
    ai_service_config_data["openai_api_key"] = openai_api_key
    ai_service_config_data["google_drive_search_webhook_url"] = (
        google_drive_search_webhook_url
    )
    ai_service_config = AIServiceConfig(**ai_service_config_data)

    # model_items = yaml_config.get("ai_service", {}).get("models", [])
    # models_config = [ModelConfig(**model) for model in model_items]

    # Build and return the complete SharedConfig
    return SharedConfig(
        base=base_config,
        jwt=jwt_config,
        ai_service=ai_service_config,
    )


config_path = "config.yml"
CONFIG = load_configuration(config_path)

info("Configuration loaded successfully.")

# TODO: handle config path properlly
