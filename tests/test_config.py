"""Tests for configuration loading.

These tests verify that the CONFIG object loads correctly with expected values.
"""

import pytest

from shared.settings import get_api_settings


class TestConfig:
    """Test configuration values match expected settings."""

    def test_base_config(self):
        """Test base configuration values."""
        settings = get_api_settings()
        assert settings.app_name == "SAARTHI"

    def test_admin_token_is_set(self):
        """Test admin token is loaded from environment."""
        settings = get_api_settings()
        assert settings.admin_token is not None
        assert len(settings.admin_token) > 0

    def test_smtp_config_is_set(self):
        """Test SMTP configuration values are present."""
        settings = get_api_settings()
        smtp = settings.smtp_settings()
        assert smtp.email
        assert smtp.app_password

    def test_settings_getter_returns_fresh_values(self, monkeypatch):
        """Test getter reads latest environment values per call."""
        monkeypatch.setenv("ADMIN_TOKEN", "first-token")
        first = get_api_settings()

        monkeypatch.setenv("ADMIN_TOKEN", "second-token")
        second = get_api_settings()

        assert first.admin_token == "first-token"
        assert second.admin_token == "second-token"

    def test_fails_when_all_notification_channels_disabled(self, monkeypatch):
        monkeypatch.setenv("EMAIL_ENABLED", "false")
        monkeypatch.setenv("NTFY_ENABLED", "false")
        monkeypatch.setenv("WHATSAPP_ENABLED", "false")

        with pytest.raises(ValueError, match="At least one geofence notification channel must be enabled"):
            get_api_settings()

    def test_fails_when_whatsapp_enabled_without_required_values(self, monkeypatch, tmp_path):
        # Isolate from repository .env so this assertion doesn't depend on local secrets/config.
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ADMIN_TOKEN", "test-token")
        monkeypatch.setenv("GEOFENCE_SUBJECT_TEMPLATE", "Subject {area} {event}")
        monkeypatch.setenv("GEOFENCE_EMAIL_TEMPLATE", "Email {area} {event}")
        monkeypatch.setenv("GEOFENCE_WHATSAPP_TEMPLATE", "WA {area} {event}")
        monkeypatch.setenv("GEOFENCE_UPDATES_RECIPIENT", "alerts@example.com")
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("EMAIL_ENABLED", "false")
        monkeypatch.setenv("NTFY_ENABLED", "false")
        monkeypatch.setenv("WHATSAPP_ENABLED", "true")
        monkeypatch.delenv("WHATSAPP_SSH_HOST", raising=False)
        monkeypatch.delenv("WHATSAPP_REMOTE_SCRIPT_PATH", raising=False)
        monkeypatch.delenv("WHATSAPP_TARGET_FAMILY", raising=False)
        monkeypatch.delenv("WHATSAPP_TARGET_PERSONAL", raising=False)

        with pytest.raises(ValueError, match="WHATSAPP_"):
            get_api_settings()

    def test_whatsapp_only_config_does_not_require_smtp(self, monkeypatch):
        monkeypatch.setenv("EMAIL_ENABLED", "false")
        monkeypatch.setenv("WHATSAPP_ENABLED", "true")
        monkeypatch.setenv("WHATSAPP_SSH_HOST", "ssh.example.com")
        monkeypatch.setenv("WHATSAPP_REMOTE_SCRIPT_PATH", "/opt/send_whatsapp.sh")
        monkeypatch.setenv("WHATSAPP_TARGET_FAMILY", "+911234567890")
        monkeypatch.delenv("SMTP_EMAIL", raising=False)
        monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)

        settings = get_api_settings()
        assert settings.email_enabled is False
        assert settings.whatsapp_enabled is True
