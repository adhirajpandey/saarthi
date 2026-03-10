"""Pytest configuration and fixtures."""

import copy
import json
import os
from pathlib import Path
import runpy

import pytest

import shared.settings as settings_module

_EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.example.py"
_BASE_CONFIG = runpy.run_path(str(_EXAMPLE_CONFIG_PATH))["CONFIG"]


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
def test_settings_environment(tmp_path, monkeypatch):
    """Provide stable settings values for tests."""
    monkeypatch.chdir(tmp_path)

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

    cfg = copy.deepcopy(_BASE_CONFIG)
    cfg["LOCATION_DB_PATH"] = str(tmp_path / "saarthi-test.db")
    cfg["GEOFENCE_MAPPING_PATH"] = str(mapping_path)
    cfg["WHATSAPP_ENABLED"] = False
    monkeypatch.setattr(settings_module, "_load_repo_config_values", lambda: copy.deepcopy(cfg))

    env_vars = {
        "ADMIN_TOKEN": "test-admin-token",
        "SMTP_EMAIL": "smtp@example.com",
        "SMTP_APP_PASSWORD": "secret-password",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "465",
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
