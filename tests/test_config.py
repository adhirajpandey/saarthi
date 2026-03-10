"""Tests for configuration loading."""

import copy

import pytest

import shared.settings as settings_module
from shared.settings import get_api_settings


class TestConfig:
    """Test configuration values match expected settings."""

    def test_base_config(self):
        settings = get_api_settings()
        assert settings.app_name == "SAARTHI"

    def test_admin_token_is_set(self):
        settings = get_api_settings()
        assert settings.admin_token is not None
        assert len(settings.admin_token) > 0

    def test_smtp_config_is_set(self):
        settings = get_api_settings()
        smtp = settings.smtp_settings()
        assert smtp.email
        assert smtp.app_password

    def test_settings_getter_returns_fresh_values(self, monkeypatch):
        monkeypatch.setenv("ADMIN_TOKEN", "first-token")
        first = get_api_settings()

        monkeypatch.setenv("ADMIN_TOKEN", "second-token")
        second = get_api_settings()

        assert first.admin_token == "first-token"
        assert second.admin_token == "second-token"

    def test_fails_when_all_notification_channels_disabled(self, monkeypatch):
        cfg = copy.deepcopy(settings_module.runtime_config.CONFIG)
        cfg["EMAIL_ENABLED"] = False
        cfg["WHATSAPP_ENABLED"] = False
        monkeypatch.setattr(settings_module.runtime_config, "CONFIG", cfg)

        with pytest.raises(
            ValueError,
            match="At least one geofence notification channel must be enabled",
        ):
            get_api_settings()

    def test_fails_when_whatsapp_enabled_without_required_values(self, monkeypatch):
        cfg = copy.deepcopy(settings_module.runtime_config.CONFIG)
        cfg["EMAIL_ENABLED"] = False
        cfg["WHATSAPP_ENABLED"] = True
        cfg["WHATSAPP_SSH_HOST"] = None
        cfg["WHATSAPP_REMOTE_SCRIPT_PATH"] = None
        cfg["WHATSAPP_TARGET_FAMILY"] = None
        monkeypatch.setattr(settings_module.runtime_config, "CONFIG", cfg)

        with pytest.raises(ValueError, match="WHATSAPP_"):
            get_api_settings()

    def test_whatsapp_only_config_does_not_require_smtp(self, monkeypatch):
        cfg = copy.deepcopy(settings_module.runtime_config.CONFIG)
        cfg["EMAIL_ENABLED"] = False
        cfg["WHATSAPP_ENABLED"] = True
        cfg["WHATSAPP_SSH_HOST"] = "ssh.example.com"
        cfg["WHATSAPP_REMOTE_SCRIPT_PATH"] = "/opt/send_whatsapp.sh"
        cfg["WHATSAPP_TARGET_FAMILY"] = "+911234567890"
        monkeypatch.setattr(settings_module.runtime_config, "CONFIG", cfg)

        monkeypatch.delenv("SMTP_EMAIL", raising=False)
        monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_PORT", raising=False)

        settings = get_api_settings()
        assert settings.email_enabled is False
        assert settings.whatsapp_enabled is True

    def test_email_enabled_requires_smtp_host_and_port(self, monkeypatch):
        cfg = copy.deepcopy(settings_module.runtime_config.CONFIG)
        cfg["EMAIL_ENABLED"] = True
        cfg["WHATSAPP_ENABLED"] = False
        monkeypatch.setattr(settings_module.runtime_config, "CONFIG", cfg)

        monkeypatch.setenv("SMTP_EMAIL", "smtp@example.com")
        monkeypatch.setenv("SMTP_APP_PASSWORD", "secret-password")
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_PORT", raising=False)

        with pytest.raises(ValueError, match="SMTP_HOST"):
            get_api_settings()

    def test_fails_when_config_owned_key_is_set_in_env(self, monkeypatch):
        monkeypatch.setenv("EMAIL_ENABLED", "false")

        with pytest.raises(ValueError, match="config.py-owned keys"):
            get_api_settings()

    def test_fails_when_config_py_missing_required_key(self, monkeypatch):
        cfg = copy.deepcopy(settings_module.runtime_config.CONFIG)
        del cfg["GEOFENCE_SUBJECT_TEMPLATE"]
        monkeypatch.setattr(settings_module.runtime_config, "CONFIG", cfg)

        with pytest.raises(ValueError, match="config.py is missing required keys"):
            get_api_settings()
