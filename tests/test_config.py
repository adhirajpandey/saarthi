"""Tests for configuration loading.

These tests verify that the CONFIG object loads correctly with expected values.
"""

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
