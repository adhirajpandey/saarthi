"""Pytest configuration and fixtures."""

import json
import os
import pytest


@pytest.fixture(autouse=True)
def block_real_whatsapp_send(monkeypatch):
    """Prevent tests from running real WhatsApp SSH commands."""

    def _blocked_subprocess_run(*args, **kwargs):
        raise AssertionError(
            "Real WhatsApp send is blocked in tests. "
            "Mock shared.notifications.whatsapp.subprocess.run explicitly."
        )

    monkeypatch.setattr(
        "shared.notifications.whatsapp.subprocess.run",
        _blocked_subprocess_run,
    )


@pytest.fixture(autouse=True)
def test_settings_environment(tmp_path):
    """Provide stable environment variables for settings-backed tests."""
    mapping_path = tmp_path / "geofence_mapping.json"
    mapping_path.write_text(
        json.dumps(
            {
                "GEOFENCE_MAPPING": [
                    {
                        "name": "Home",
                        "latitude": 12.9716,
                        "longitude": 77.5946,
                        "radius_meters": 200,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    env_vars = {
        "ADMIN_TOKEN": "test-admin-token",
        "GEOFENCE_UPDATES_RECIPIENT": "test@example.com",
        "GEOFENCE_SENDER_NAME": "Test Sender",
        "SMTP_EMAIL": "smtp@example.com",
        "SMTP_APP_PASSWORD": "secret-password",
        "WHATSAPP_ENABLED": "false",
        "LOCATION_DB_PATH": str(tmp_path / "saarthi-test.db"),
        "GEOFENCE_MAPPING_PATH": str(mapping_path),
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
