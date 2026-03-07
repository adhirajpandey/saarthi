"""Tests for configuration loading.

These tests verify that the CONFIG object loads correctly with expected values.
"""


class TestConfig:
    """Test configuration values match expected settings."""

    def test_base_config(self):
        """Test base configuration values."""
        from app import CONFIG

        assert CONFIG.base.app_name == "SAARTHI"

    def test_admin_token_is_set(self):
        """Test admin token is loaded from environment."""
        from app import CONFIG

        assert CONFIG.admin_token is not None
        assert len(CONFIG.admin_token) > 0

    def test_rate_limiting_config(self):
        """Test rate limiting configuration defaults."""
        from app import CONFIG

        assert CONFIG.rate_limiting.default_limit == "50/minute"
