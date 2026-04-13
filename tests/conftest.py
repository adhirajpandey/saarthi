"""Pytest configuration and fixtures."""

import copy
import json
import os
from pathlib import Path
import runpy
import tempfile
import sys
import types
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
import shared.settings as settings_module

_EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "app" / "config" / "config.example.py"
_BASE_CONFIG = runpy.run_path(str(_EXAMPLE_CONFIG_PATH))["CONFIG"]


@pytest.fixture(autouse=True)
def side_effect_guard(monkeypatch):
    """Block real network/process side effects unless explicitly mocked by a test."""

    def _blocked_subprocess_run(*_args, **_kwargs):
        raise AssertionError(
            "Real subprocess execution is blocked in tests. "
            "Mock subprocess.run in the target module explicitly."
        )

    class _BlockedSmtpServer:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError(
                "Real SMTP is blocked in tests. "
                "Mock shared.notifications.email.smtplib.SMTP_SSL explicitly."
            )

    def _blocked_requests_post(*_args, **_kwargs):
        raise AssertionError(
            "Outbound HTTP is blocked in tests. "
            "Mock shared.notifications.ntfy.requests.post explicitly."
        )

    monkeypatch.setattr("subprocess.run", _blocked_subprocess_run)
    monkeypatch.setattr("shared.notifications.email.smtplib.SMTP_SSL", _BlockedSmtpServer)
    monkeypatch.setattr("shared.notifications.ntfy.requests.post", _blocked_requests_post)


@pytest.fixture(autouse=True)
def test_workspace() -> Path:
    """Create isolated per-test workspace and remove it entirely on teardown."""
    with tempfile.TemporaryDirectory(prefix="saarthi-tests-") as path:
        yield Path(path)


@pytest.fixture
def runtime_config(
    test_workspace: Path,
    monkeypatch,
) -> Callable[[dict[str, Any] | None], dict[str, Any]]:
    """Provide stable settings and allow per-test overrides."""
    env_path = test_workspace / ".env"
    env_path.write_text("", encoding="utf-8")
    mapping_path = test_workspace / "geofence_mapping.json"
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

    monkeypatch.setattr(settings_module, "ENV_FILE", env_path)
    monkeypatch.setattr(settings_module, "CONFIG_MODULE_PATH", "tests.runtime_config")

    env_vars = {
        "ADMIN_TOKEN": "test-admin-token",
        "MCP_TOKEN": "test-mcp-token",
        "SMTP_EMAIL": "smtp@example.com",
        "SMTP_APP_PASSWORD": "secret-password",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "465",
    }
    original_values = {key: os.environ.get(key) for key in env_vars}
    for key, value in env_vars.items():
        os.environ[key] = value

    def _configure(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        cfg = copy.deepcopy(_BASE_CONFIG)
        cfg["LOCATION_DB_PATH"] = str(test_workspace / "saarthi-test.db")
        cfg["GEOFENCE_MAPPING_PATH"] = str(mapping_path)
        cfg["WHATSAPP_ENABLED"] = False
        if overrides:
            cfg.update(overrides)

        runtime_module = types.ModuleType("tests.runtime_config")
        runtime_module.CONFIG = cfg
        sys.modules["tests.runtime_config"] = runtime_module
        return cfg

    _configure()

    try:
        yield _configure
    finally:
        for key, original in original_values.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original
        sys.modules.pop("tests.runtime_config", None)


@pytest.fixture(autouse=True)
def _default_runtime_config(runtime_config) -> None:
    runtime_config()


@pytest.fixture
def client(runtime_config) -> TestClient:
    """Return a TestClient with default runtime test config applied."""
    runtime_config()
    with TestClient(app) as test_client:
        yield test_client
