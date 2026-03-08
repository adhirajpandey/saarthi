"""Pytest configuration and fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def test_settings_environment():
    """Provide stable environment variables for settings-backed tests."""
    env_vars = {
        "ADMIN_TOKEN": "test-admin-token",
        "GEOFENCE_UPDATES_RECIPIENT": "test@example.com",
        "GEOFENCE_SENDER_NAME": "Test Sender",
        "SMTP_EMAIL": "smtp@example.com",
        "SMTP_APP_PASSWORD": "secret-password",
    }
    original_values = {key: os.environ.get(key) for key in env_vars}
    for key, value in env_vars.items():
        os.environ[key] = value
    try:
        yield
    finally:
        for key, original in original_values.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original
