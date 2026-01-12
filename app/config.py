import os
import yaml
from dotenv import load_dotenv
from typing import Dict, Any
from .models import (
    SharedConfig,
    BaseConfig,
    JWTConfig,
    ProvidersConfig,
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
        error("JWT_SECRET_KEY environment variable not set.")
        raise SystemExit("JWT_SECRET_KEY environment variable not set.")

    openai_api_key = os.getenv("OPENAI_API_KEY", None)
    if not openai_api_key:
        info("OPENAI_API_KEY environment variable not set.")

    google_drive_search_webhook_url = os.getenv("GOOGLE_DRIVE_SEARCH_WEBHOOK_URL", None)
    if not google_drive_search_webhook_url:
        info("GOOGLE_DRIVE_SEARCH_WEBHOOK_URL environment variable not set.")

    ollama_dell_work_endpoint = os.getenv("OLLAMA_DELL_WORK_ENDPOINT", None)
    if not ollama_dell_work_endpoint:
        info("OLLAMA_DELL_WORK_ENDPOINT environment variable not set.")
    ollama_dell_work_api_key = os.getenv("OLLAMA_DELL_WORK_API_KEY", None)
    if not ollama_dell_work_api_key:
        info("OLLAMA_DELL_WORK_API_KEY environment variable not set.")

    gemini_endpoint = os.getenv("GEMINI_ENDPOINT", None)
    if not gemini_endpoint:
        info("GEMINI_ENDPOINT environment variable not set.")
    gemini_api_key = os.getenv("GEMINI_API_KEY", None)
    if not gemini_api_key:
        info("GEMINI_API_KEY environment variable not set.")

    openrouter_endpoint = os.getenv("OPENROUTER_ENDPOINT", None)
    if not openrouter_endpoint:
        info("OPENROUTER_ENDPOINT environment variable not set.")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", None)
    if not openrouter_api_key:
        info("OPENROUTER_API_KEY environment variable not set.")

    static_api_token = os.getenv("STATIC_API_TOKEN", None)
    if not static_api_token:
        info("STATIC_API_TOKEN environment variable not set.")

    ollama_provider = {
        "base_url": ollama_dell_work_endpoint,
        "api_key": ollama_dell_work_api_key,
    }

    gemini_provider = {
        "base_url": gemini_endpoint,
        "api_key": gemini_api_key,
    }

    openrouter_provider = {
        "base_url": openrouter_endpoint,
        "api_key": openrouter_api_key,
    }

    providers_config = ProvidersConfig(
        ollama=ollama_provider, gemini=gemini_provider, openrouter=openrouter_provider
    )

    base_config = BaseConfig(**yaml_config.get("base", {}))
    jwt_config_data = yaml_config.get("jwt", {})
    jwt_config_data["secret_key"] = jwt_secret_key
    jwt_config = JWTConfig(**jwt_config_data)

    ai_service_config_data = yaml_config.get("ai_service", {})
    ai_service_config_data["openai_api_key"] = openai_api_key
    ai_service_config_data["google_drive_search_webhook_url"] = (
        google_drive_search_webhook_url
    )

    ai_service_config_data["providers"] = providers_config
    ai_service_config = AIServiceConfig(**ai_service_config_data)

    return SharedConfig(
        base=base_config,
        jwt=jwt_config,
        ai_service=ai_service_config,
        static_api_token=static_api_token,
    )


config_path = "config.yml"
CONFIG = load_configuration(config_path)

info("Configuration loaded successfully.")
