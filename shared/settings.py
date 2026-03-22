"""Typed runtime settings for API and scripts."""

import importlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from dotenv import dotenv_values
from pydantic import BaseModel, model_validator

ENV_OWNED_KEYS = frozenset(
    {
        "ADMIN_TOKEN",
        "SMTP_EMAIL",
        "SMTP_APP_PASSWORD",
        "SMTP_HOST",
        "SMTP_PORT",
        "AWS_ACCESS_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "VIDWIZ_DB_URL",
        "TRACKCROW_DB_URL",
        "SMASHDIARY_DB_URL",
        "NTFY_BASE_URL",
        "NTFY_TOKEN",
    }
)

CONFIG_OWNED_KEYS = frozenset(
    {
        "APP_NAME",
        "LOCATION_DB_PATH",
        "GEOFENCE_MAPPING_PATH",
        "DELL_TAILSCALE_IP",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "LOG_DATE_FORMAT",
        "LOG_FILE",
        "EMAIL_ENABLED",
        "NTFY_ENABLED",
        "WHATSAPP_ENABLED",
        "WHATSAPP_SSH_HOST",
        "WHATSAPP_REMOTE_SCRIPT_PATH",
        "WHATSAPP_TARGET_FAMILY",
        "WHATSAPP_TARGET_PERSONAL",
        "WHATSAPP_TIMEOUT_SECONDS",
        "GEOFENCE_SUBJECT_TEMPLATE",
        "GEOFENCE_EMAIL_TEMPLATE",
        "GEOFENCE_WHATSAPP_TEMPLATE",
        "GEOFENCE_UPDATES_RECIPIENT",
        "GEOFENCE_SENDER_NAME",
        "NTFY_TOPIC",
        "BACKUP_BUCKET",
        "VIDWIZ_S3_PREFIX",
        "TRACKCROW_S3_PREFIX",
        "SMASHDIARY_S3_PREFIX",
        "VIDWIZ_DUMP_FILENAME",
        "TRACKCROW_DUMP_FILENAME",
        "SMASHDIARY_DUMP_FILENAME",
        "GDRIVE_SOURCE",
        "GDRIVE_DESTINATION",
        "GDRIVE_FOLDERS",
        "SHIKARI_SESSIONS_PATH",
        "SHIKARI_OUTPUTS_PATH",
        "SHIKARI_DEFAULT_THEME",
        "SHIKARI_DEFAULT_OUTPUT_FORMAT",
    }
)

ALL_SETTINGS_KEYS = ENV_OWNED_KEYS | CONFIG_OWNED_KEYS
CONFIG_MODULE_PATH = "app.config.config"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


def _import_repo_config() -> Mapping[str, Any]:
    try:
        module = importlib.import_module(CONFIG_MODULE_PATH)
    except ModuleNotFoundError as exc:
        if exc.name == CONFIG_MODULE_PATH:
            raise ValueError(
                "Missing app/config/config.py. Create it from app/config/config.example.py"
            ) from exc
        raise

    config = getattr(module, "CONFIG", None)
    if not isinstance(config, Mapping):
        raise ValueError("app/config/config.py must define CONFIG as a dictionary")
    return config


def _validate_repo_config(config: Mapping[str, Any]) -> None:
    wrong_keys = sorted(key for key in config if key in ENV_OWNED_KEYS)
    if wrong_keys:
        raise ValueError(f"app/config/config.py contains env-owned keys: {', '.join(wrong_keys)}")

    missing_keys = sorted(key for key in CONFIG_OWNED_KEYS if key not in config)
    if missing_keys:
        raise ValueError(f"app/config/config.py is missing required keys: {', '.join(missing_keys)}")


def _load_repo_config_values() -> dict[str, Any]:
    config = _import_repo_config()
    _validate_repo_config(config)
    return {key: config[key] for key in CONFIG_OWNED_KEYS}


def _collect_env_values() -> dict[str, str]:
    values: dict[str, str] = {}

    for key, value in dotenv_values(ENV_FILE).items():
        if key in ALL_SETTINGS_KEYS and isinstance(value, str) and value.strip():
            values[key] = value

    for key in ALL_SETTINGS_KEYS:
        value = os.environ.get(key)
        if value is not None and value.strip():
            values[key] = value

    return values


def _validate_env_values(values: Mapping[str, str]) -> None:
    wrong_keys = sorted(key for key in values if key in CONFIG_OWNED_KEYS)
    if wrong_keys:
        raise ValueError(
            ".env/environment contains app/config/config.py-owned keys: "
            f"{', '.join(wrong_keys)}"
        )


def _load_env_values() -> dict[str, str]:
    values = _collect_env_values()
    _validate_env_values(values)
    return {key: value for key, value in values.items() if key in ENV_OWNED_KEYS}


def _build_payload() -> dict[str, Any]:
    payload = {**_load_repo_config_values(), **_load_env_values()}
    return {key.lower(): value for key, value in payload.items()}


class LoggingSettings(BaseModel):
    """Logging configuration shared by app and scripts."""

    level: str
    format: str
    date_format: str
    file: str


class SmtpSettings(BaseModel):
    """SMTP configuration for email notifications."""

    email: str
    app_password: str
    host: str
    port: int


class NtfySettings(BaseModel):
    """ntfy credentials and defaults."""

    base_url: str
    token: str
    topic: str


class WhatsAppSettings(BaseModel):
    """WhatsApp sender configuration."""

    ssh_host: str
    remote_script_path: str
    target: str
    timeout_seconds: int


class RuntimeSettings(BaseModel):
    """Base settings with shared logging configuration."""

    log_level: str
    log_format: str
    log_date_format: str
    log_file: str
    email_enabled: bool
    ntfy_enabled: bool
    whatsapp_enabled: bool
    whatsapp_ssh_host: str | None = None
    whatsapp_remote_script_path: str | None = None
    whatsapp_target_family: str | None = None
    whatsapp_target_personal: str | None = None
    whatsapp_timeout_seconds: int

    def logging_settings(self) -> LoggingSettings:
        return LoggingSettings(
            level=self.log_level,
            format=self.log_format,
            date_format=self.log_date_format,
            file=self.log_file,
        )

    def _validate_whatsapp_transport(self) -> None:
        if self.whatsapp_enabled:
            if not self.whatsapp_ssh_host:
                raise ValueError("WHATSAPP_SSH_HOST is required when WHATSAPP_ENABLED is true")
            if not self.whatsapp_remote_script_path:
                raise ValueError(
                    "WHATSAPP_REMOTE_SCRIPT_PATH is required when WHATSAPP_ENABLED is true"
                )

    def _build_whatsapp_settings(self, target: str | None) -> WhatsAppSettings:
        if not self.whatsapp_ssh_host or not self.whatsapp_remote_script_path or not target:
            raise ValueError("WhatsApp settings are not configured")
        return WhatsAppSettings(
            ssh_host=self.whatsapp_ssh_host,
            remote_script_path=self.whatsapp_remote_script_path,
            target=target,
            timeout_seconds=self.whatsapp_timeout_seconds,
        )

    def whatsapp_settings_for_geofence(self) -> WhatsAppSettings:
        return self._build_whatsapp_settings(self.whatsapp_target_family)

    def whatsapp_settings_for_scripts(self) -> WhatsAppSettings:
        return self._build_whatsapp_settings(self.whatsapp_target_personal)


class NtfyRuntimeSettings(RuntimeSettings):
    """Runtime settings that include ntfy integration."""

    ntfy_base_url: str | None = None
    ntfy_token: str | None = None
    ntfy_topic: str

    @model_validator(mode="after")
    def _validate_ntfy_config(self) -> "NtfyRuntimeSettings":
        if not (self.ntfy_enabled or self.whatsapp_enabled):
            raise ValueError(
                "At least one script notification channel must be enabled: "
                "NTFY_ENABLED or WHATSAPP_ENABLED"
            )
        if self.ntfy_enabled:
            if not self.ntfy_base_url:
                raise ValueError("NTFY_BASE_URL is required when NTFY_ENABLED is true")
            if not self.ntfy_token:
                raise ValueError("NTFY_TOKEN is required when NTFY_ENABLED is true")
        self._validate_whatsapp_transport()
        if self.whatsapp_enabled and not self.whatsapp_target_personal:
            raise ValueError("WHATSAPP_TARGET_PERSONAL is required when WHATSAPP_ENABLED is true")
        return self

    def ntfy_settings(self) -> NtfySettings:
        return NtfySettings(
            base_url=cast(str, self.ntfy_base_url),
            token=cast(str, self.ntfy_token),
            topic=self.ntfy_topic,
        )


class ApiSettings(RuntimeSettings):
    """Settings required by the FastAPI runtime."""

    app_name: str
    location_db_path: str
    geofence_mapping_path: str
    dell_tailscale_ip: str
    admin_token: str
    geofence_subject_template: str
    geofence_email_template: str
    geofence_whatsapp_template: str
    geofence_updates_recipient: str
    geofence_sender_name: str | None
    smtp_email: str | None = None
    smtp_app_password: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None

    @model_validator(mode="after")
    def _validate_api_notification_channels(self) -> "ApiSettings":
        if not (self.email_enabled or self.whatsapp_enabled):
            raise ValueError(
                "At least one geofence notification channel must be enabled: "
                "EMAIL_ENABLED or WHATSAPP_ENABLED"
            )
        if self.email_enabled:
            if not self.smtp_email:
                raise ValueError("SMTP_EMAIL is required when EMAIL_ENABLED is true")
            if not self.smtp_app_password:
                raise ValueError("SMTP_APP_PASSWORD is required when EMAIL_ENABLED is true")
            if not self.smtp_host:
                raise ValueError("SMTP_HOST is required when EMAIL_ENABLED is true")
            if self.smtp_port is None:
                raise ValueError("SMTP_PORT is required when EMAIL_ENABLED is true")
        self._validate_whatsapp_transport()
        if self.whatsapp_enabled and not self.whatsapp_target_family:
            raise ValueError("WHATSAPP_TARGET_FAMILY is required when WHATSAPP_ENABLED is true")
        return self

    def smtp_settings(self) -> SmtpSettings:
        if (
            not self.smtp_email
            or not self.smtp_app_password
            or not self.smtp_host
            or self.smtp_port is None
        ):
            raise ValueError("SMTP settings are not configured")
        return SmtpSettings(
            email=self.smtp_email,
            app_password=self.smtp_app_password,
            host=self.smtp_host,
            port=self.smtp_port,
        )


class BackupDbSettings(NtfyRuntimeSettings):
    """Settings required by the database backup script."""

    aws_access_key: str
    aws_secret_access_key: str
    backup_bucket: str
    vidwiz_db_url: str
    trackcrow_db_url: str
    smashdiary_db_url: str
    vidwiz_s3_prefix: str
    trackcrow_s3_prefix: str
    smashdiary_s3_prefix: str
    vidwiz_dump_filename: str
    trackcrow_dump_filename: str
    smashdiary_dump_filename: str


class BackupGdriveSettings(NtfyRuntimeSettings):
    """Settings required by the Google Drive backup script."""

    gdrive_source: str
    gdrive_destination: str
    gdrive_folders: list[str]

    @model_validator(mode="before")
    @classmethod
    def _normalize_folders(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        folders = value.get("gdrive_folders")
        if isinstance(folders, str):
            value["gdrive_folders"] = [item.strip() for item in folders.split(",") if item.strip()]
        return value


class SchedulerScriptSettings(BaseModel):
    """Systemd scheduling settings loaded from JSON."""

    name: str
    command: str
    time: str
    description: str


class SchedulerSettings(BaseModel):
    """Scheduler script configuration model."""

    systemd_path: str
    uv_bin: str
    working_dir: str
    home_dir: str
    scripts: list[SchedulerScriptSettings]

    @model_validator(mode="after")
    def _validate_times(self) -> "SchedulerSettings":
        for script in self.scripts:
            parts = script.time.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid time format for {script.name}: {script.time}")
            hour, minute = parts
            if not hour.isdigit() or not minute.isdigit():
                raise ValueError(f"Invalid time format for {script.name}: {script.time}")
            if int(hour) not in range(0, 24) or int(minute) not in range(0, 60):
                raise ValueError(f"Invalid time value for {script.name}: {script.time}")
        return self


class ShikariSettings(RuntimeSettings):
    """Settings required by the Shikari visualization script."""

    shikari_sessions_path: str
    shikari_outputs_path: str
    shikari_default_theme: str
    shikari_default_output_format: str


def get_api_settings() -> ApiSettings:
    """Return API settings."""
    return ApiSettings.model_validate(_build_payload())


def get_backup_db_settings() -> BackupDbSettings:
    """Return DB backup settings."""
    return BackupDbSettings.model_validate(_build_payload())


def get_backup_gdrive_settings() -> BackupGdriveSettings:
    """Return GDrive backup settings."""
    return BackupGdriveSettings.model_validate(_build_payload())


def get_shikari_settings() -> ShikariSettings:
    """Return Shikari visualization settings."""
    return ShikariSettings.model_validate(_build_payload())
