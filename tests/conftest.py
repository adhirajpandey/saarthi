"""Pytest configuration and fixtures."""

import json
import os
import pytest


TEST_CONFIG = {
    "APP_NAME": "SAARTHI",
    "LOCATION_DB_PATH": "data/saarthi-test.db",
    "GEOFENCE_MAPPING_PATH": "data/geofence_mapping.json",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
    "LOG_FILE": "logs/saarthi-test.log",
    "EMAIL_ENABLED": True,
    "NTFY_ENABLED": False,
    "WHATSAPP_ENABLED": False,
    "GEOFENCE_UPDATES_RECIPIENT": "test@example.com",
    "GEOFENCE_SENDER_NAME": "Test Sender",
    "GEOFENCE_SUBJECT_TEMPLATE": "Subject {area} {event}",
    "GEOFENCE_EMAIL_TEMPLATE": "Email {area} {event}",
    "GEOFENCE_WHATSAPP_TEMPLATE": "WA {area} {event}",
    "SMTP_EMAIL": "smtp@example.com",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": 587,
}


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
def test_settings_environment(monkeypatch, tmp_path):
    """Provide stable config.py values and env secrets for settings-backed tests."""
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

    config = dict(TEST_CONFIG)
    config["LOCATION_DB_PATH"] = str(tmp_path / "saarthi-test.db")
    config["GEOFENCE_MAPPING_PATH"] = str(mapping_path)
    monkeypatch.setattr("shared.settings.load_local_config", lambda required=True: config)

    env_vars = {
        "ADMIN_TOKEN": "test-admin-token",
        "SMTP_APP_PASSWORD": "secret-password",
        "AWS_ACCESS_KEY": "test-aws-key",
        "AWS_SECRET_ACCESS_KEY": "test-aws-secret",
        "VIDWIZ_DB_URL": "postgres://vidwiz:pass@localhost:5432/vidwiz",
        "TRACKCROW_DB_URL": "postgres://trackcrow:pass@localhost:5432/trackcrow",
        "NTFY_TOKEN": "test-ntfy-token",
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
