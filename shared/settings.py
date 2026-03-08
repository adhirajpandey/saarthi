"""Typed runtime settings for API and scripts."""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

DEFAULT_GEOFENCE_SUBJECT_TEMPLATE = "Adhiraj Location Update: {area}"
DEFAULT_GEOFENCE_EMAIL_TEMPLATE = """Hello Pandey Parivaar,

Adhiraj ki location ka update:

Area - {area}
Update - {event}

Regards
Pandey Bot
"""

_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
)


class LoggingSettings(BaseModel):
    """Logging configuration shared by app and scripts."""

    level: str = "INFO"
    format: str = DEFAULT_LOG_FORMAT
    date_format: str = DEFAULT_LOG_DATE_FORMAT
    file: str = "logs/app.log"


class SmtpSettings(BaseModel):
    """SMTP configuration for email notifications."""

    email: str
    app_password: str
    host: str = "smtp.gmail.com"
    port: int = 465


class NtfySettings(BaseModel):
    """ntfy credentials and defaults."""

    base_url: str
    token: str
    topic: str = "notifs"


class RuntimeSettings(BaseSettings):
    """Base settings with shared logging configuration."""

    model_config = _SETTINGS_CONFIG

    log_level: str = "INFO"
    log_format: str = DEFAULT_LOG_FORMAT
    log_date_format: str = DEFAULT_LOG_DATE_FORMAT
    log_file: str = "logs/app.log"

    def logging_settings(self) -> LoggingSettings:
        return LoggingSettings(
            level=self.log_level,
            format=self.log_format,
            date_format=self.log_date_format,
            file=self.log_file,
        )


class NtfyRuntimeSettings(RuntimeSettings):
    """Runtime settings that include ntfy integration."""

    ntfy_base_url: str
    ntfy_token: str
    ntfy_topic: str = "notifs"

    def ntfy_settings(self) -> NtfySettings:
        return NtfySettings(
            base_url=self.ntfy_base_url,
            token=self.ntfy_token,
            topic=self.ntfy_topic,
        )


class ApiSettings(RuntimeSettings):
    """Settings required by the FastAPI runtime."""

    app_name: str = "SAARTHI"
    admin_token: str
    geofence_subject_template: str = DEFAULT_GEOFENCE_SUBJECT_TEMPLATE
    geofence_email_template: str = DEFAULT_GEOFENCE_EMAIL_TEMPLATE
    geofence_updates_recipient: str
    geofence_sender_name: str | None = None
    smtp_email: str
    smtp_app_password: str
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465

    def smtp_settings(self) -> SmtpSettings:
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
    backup_bucket: str = "dwaar"
    vidwiz_s3_prefix: str = "backups/db/vidwiz"
    trackcrow_s3_prefix: str = "backups/db/trackcrow"
    vidwiz_dump_filename: str = "vidwiz-dump"
    trackcrow_dump_filename: str = "trackcrow-dump"


class BackupGdriveSettings(NtfyRuntimeSettings):
    """Settings required by the Google Drive backup script."""

    gdrive_source: str = "personal-drive"
    gdrive_destination: str = "dwaar-s3:dwaar/backups/gdrive"
    gdrive_folders: list[str] = Field(default_factory=lambda: ["[01] PERSONAL", "[02] PROFESSIONAL"])

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


@lru_cache
def get_api_settings() -> ApiSettings:
    """Return cached API settings."""
    return ApiSettings()


@lru_cache
def get_backup_db_settings() -> BackupDbSettings:
    """Return cached DB backup settings."""
    return BackupDbSettings()


@lru_cache
def get_backup_gdrive_settings() -> BackupGdriveSettings:
    """Return cached GDrive backup settings."""
    return BackupGdriveSettings()


def clear_settings_cache(
    targets: tuple[
        Literal["api", "backup_db", "backup_gdrive"],
        ...,
    ] = ("api", "backup_db", "backup_gdrive"),
) -> None:
    """Clear settings caches for tests."""
    if "api" in targets:
        get_api_settings.cache_clear()
    if "backup_db" in targets:
        get_backup_db_settings.cache_clear()
    if "backup_gdrive" in targets:
        get_backup_gdrive_settings.cache_clear()
