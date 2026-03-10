"""Tests for configuration loading split between config.py and env secrets."""

import pytest

from shared.settings import get_api_settings


BASE_CONFIG = {
    "APP_NAME": "SAARTHI",
    "EMAIL_ENABLED": True,
    "NTFY_ENABLED": False,
    "WHATSAPP_ENABLED": False,
    "GEOFENCE_SUBJECT_TEMPLATE": "Subject {area} {event}",
    "GEOFENCE_EMAIL_TEMPLATE": "Email {area} {event}",
    "GEOFENCE_WHATSAPP_TEMPLATE": "WA {area} {event}",
    "GEOFENCE_UPDATES_RECIPIENT": "alerts@example.com",
    "SMTP_EMAIL": "smtp@example.com",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": 587,
}


class TestConfig:
    def test_base_config(self, monkeypatch):
        monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: BASE_CONFIG)
        settings = get_api_settings()
        assert settings.app_name == "SAARTHI"

    def test_admin_token_is_set_from_environment(self, monkeypatch):
        monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: BASE_CONFIG)
        monkeypatch.setenv("ADMIN_TOKEN", "env-admin-token")

        settings = get_api_settings()
        assert settings.admin_token == "env-admin-token"

    def test_settings_getter_returns_fresh_secret_values(self, monkeypatch):
        monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: BASE_CONFIG)
        monkeypatch.setenv("ADMIN_TOKEN", "first-token")
        first = get_api_settings()

        monkeypatch.setenv("ADMIN_TOKEN", "second-token")
        second = get_api_settings()

        assert first.admin_token == "first-token"
        assert second.admin_token == "second-token"

    def test_fails_when_all_notification_channels_disabled(self, monkeypatch):
        config = dict(BASE_CONFIG)
        config["EMAIL_ENABLED"] = False
        config["WHATSAPP_ENABLED"] = False
        monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: config)

        with pytest.raises(ValueError, match="At least one geofence notification channel must be enabled"):
            get_api_settings()

    def test_fails_when_whatsapp_enabled_without_required_values(self, monkeypatch):
        config = dict(BASE_CONFIG)
        config["EMAIL_ENABLED"] = False
        config["WHATSAPP_ENABLED"] = True
        monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: config)

        with pytest.raises(ValueError, match="WHATSAPP_"):
            get_api_settings()

    def test_whatsapp_only_config_does_not_require_smtp(self, monkeypatch):
        config = dict(BASE_CONFIG)
        config["EMAIL_ENABLED"] = False
        config["WHATSAPP_ENABLED"] = True
        config["WHATSAPP_SSH_HOST"] = "ssh.example.com"
        config["WHATSAPP_REMOTE_SCRIPT_PATH"] = "/opt/send_whatsapp.sh"
        config["WHATSAPP_TARGET_FAMILY"] = "+911234567890"
        config.pop("SMTP_EMAIL", None)
        config.pop("SMTP_HOST", None)
        config.pop("SMTP_PORT", None)
        monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: config)

        settings = get_api_settings()
        assert settings.email_enabled is False
        assert settings.whatsapp_enabled is True

    def test_email_enabled_requires_smtp_host_and_port_from_config(self, monkeypatch):
        config = dict(BASE_CONFIG)
        config.pop("SMTP_HOST", None)
        config.pop("SMTP_PORT", None)
        monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: config)

        with pytest.raises(ValueError, match="SMTP_HOST"):
            get_api_settings()

    def test_local_config_supplies_non_secret_fields(self, monkeypatch):
        monkeypatch.setattr(
            "shared.settings.load_local_config",
            lambda required=True: {**BASE_CONFIG, "APP_NAME": "SAARTHI-LOCAL"},
        )
        settings = get_api_settings()
        assert settings.app_name == "SAARTHI-LOCAL"

    def test_env_non_secret_does_not_override_config(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "SAARTHI-ENV")
        monkeypatch.setattr(
            "shared.settings.load_local_config",
            lambda required=True: {**BASE_CONFIG, "APP_NAME": "SAARTHI-LOCAL"},
        )

        settings = get_api_settings()
        assert settings.app_name == "SAARTHI-LOCAL"
