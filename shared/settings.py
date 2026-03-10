"""Typed runtime settings for API and scripts with strict config/env separation."""

from typing import Any, cast

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.constants import (
    DEFAULT_APP_NAME,
    DEFAULT_EMAIL_ENABLED,
    DEFAULT_GEOFENCE_MAPPING_PATH,
    DEFAULT_LOG_DATE_FORMAT,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOCATION_DB_PATH,
    DEFAULT_NTFY_ENABLED,
    DEFAULT_WHATSAPP_ENABLED,
    DEFAULT_WHATSAPP_TIMEOUT_SECONDS,
)
from shared.local_config import load_local_config

_SECRET_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    env_ignore_empty=True,
    extra="ignore",
)


class LoggingSettings(BaseModel):
    """Logging configuration shared by app and scripts."""

    level: str = DEFAULT_LOG_LEVEL
    format: str = DEFAULT_LOG_FORMAT
    date_format: str = DEFAULT_LOG_DATE_FORMAT
    file: str = DEFAULT_LOG_FILE


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
    timeout_seconds: int = DEFAULT_WHATSAPP_TIMEOUT_SECONDS


class SecretSettings(BaseSettings):
    """Secret values loaded only from environment variables."""

    model_config = _SECRET_SETTINGS_CONFIG

    admin_token: str | None = None
    smtp_app_password: str | None = None
    aws_access_key: str | None = None
    aws_secret_access_key: str | None = None
    vidwiz_db_url: str | None = None
    trackcrow_db_url: str | None = None
    ntfy_token: str | None = None


class RuntimeSettings(BaseModel):
    """Non-secret runtime values loaded only from config.py."""

    log_level: str = DEFAULT_LOG_LEVEL
    log_format: str = DEFAULT_LOG_FORMAT
    log_date_format: str = DEFAULT_LOG_DATE_FORMAT
    log_file: str = DEFAULT_LOG_FILE
    email_enabled: bool = DEFAULT_EMAIL_ENABLED
    ntfy_enabled: bool = DEFAULT_NTFY_ENABLED
    whatsapp_enabled: bool = DEFAULT_WHATSAPP_ENABLED
    whatsapp_ssh_host: str | None = None
    whatsapp_remote_script_path: str | None = None
    whatsapp_target_family: str | None = None
    whatsapp_target_personal: str | None = None
    whatsapp_timeout_seconds: int = DEFAULT_WHATSAPP_TIMEOUT_SECONDS

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

    app_name: str = DEFAULT_APP_NAME
    location_db_path: str = DEFAULT_LOCATION_DB_PATH
    geofence_mapping_path: str = DEFAULT_GEOFENCE_MAPPING_PATH
    admin_token: str
    geofence_subject_template: str
    geofence_email_template: str
    geofence_whatsapp_template: str
    geofence_updates_recipient: str
    geofence_sender_name: str | None = None
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
    vidwiz_db_url: str
    trackcrow_db_url: str
    backup_bucket: str
    vidwiz_s3_prefix: str
    trackcrow_s3_prefix: str
    vidwiz_dump_filename: str
    trackcrow_dump_filename: str


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


def _config_to_model_input(model_cls: type[BaseModel], config: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field_name in model_cls.model_fields:
        env_style_key = field_name.upper()
        if env_style_key in config:
            payload[field_name] = config[env_style_key]
    return payload


def _merge_secret_payload(payload: dict[str, Any], secrets: SecretSettings) -> dict[str, Any]:
    merged = dict(payload)
    secret_map = {
        "ADMIN_TOKEN": "admin_token",
        "SMTP_APP_PASSWORD": "smtp_app_password",
        "AWS_ACCESS_KEY": "aws_access_key",
        "AWS_SECRET_ACCESS_KEY": "aws_secret_access_key",
        "VIDWIZ_DB_URL": "vidwiz_db_url",
        "TRACKCROW_DB_URL": "trackcrow_db_url",
        "NTFY_TOKEN": "ntfy_token",
    }
    for _, field_name in secret_map.items():
        value = getattr(secrets, field_name)
        if value is not None:
            merged[field_name] = value
    return merged


def _build_settings(model_cls: type[BaseModel]) -> BaseModel:
    config = load_local_config(required=True)
    secrets = SecretSettings()
    payload = _config_to_model_input(model_cls, config)
    payload = _merge_secret_payload(payload, secrets)
    return model_cls(**payload)


def get_api_settings() -> ApiSettings:
    """Return API settings."""
    return cast(ApiSettings, _build_settings(ApiSettings))


def get_backup_db_settings() -> BackupDbSettings:
    """Return DB backup settings."""
    return cast(BackupDbSettings, _build_settings(BackupDbSettings))


def get_backup_gdrive_settings() -> BackupGdriveSettings:
    """Return GDrive backup settings."""
    return cast(BackupGdriveSettings, _build_settings(BackupGdriveSettings))
