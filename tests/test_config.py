"""Tests for configuration loading."""

import sys
import types

import pytest

import shared.settings as settings_module
from shared.settings import get_api_settings, get_shikari_settings

def test_settings_getter_returns_fresh_values(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_TOKEN", "first-token")
    first = get_api_settings()

    monkeypatch.setenv("ADMIN_TOKEN", "second-token")
    second = get_api_settings()

    assert first.admin_token == "first-token"
    assert second.admin_token == "second-token"


def test_fails_when_all_notification_channels_disabled(runtime_config) -> None:
    runtime_config({"EMAIL_ENABLED": False, "WHATSAPP_ENABLED": False})

    with pytest.raises(
        ValueError,
        match="At least one geofence notification channel must be enabled",
    ):
        get_api_settings()


def test_fails_when_whatsapp_enabled_without_required_values(runtime_config) -> None:
    runtime_config(
        {
            "EMAIL_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": None,
            "WHATSAPP_REMOTE_SCRIPT_PATH": None,
            "WHATSAPP_TARGET_FAMILY": None,
        }
    )

    with pytest.raises(ValueError, match="WHATSAPP_"):
        get_api_settings()


def test_whatsapp_only_config_does_not_require_smtp(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "EMAIL_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_REMOTE_SCRIPT_PATH": "/opt/send_whatsapp.sh",
            "WHATSAPP_TARGET_FAMILY": "+911234567890",
        }
    )

    monkeypatch.delenv("SMTP_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)

    settings = get_api_settings()
    assert settings.email_enabled is False
    assert settings.whatsapp_enabled is True


def test_email_enabled_requires_smtp_host_and_port(monkeypatch, runtime_config) -> None:
    runtime_config({"EMAIL_ENABLED": True, "WHATSAPP_ENABLED": False})

    monkeypatch.setenv("SMTP_EMAIL", "smtp@example.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "secret-password")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)

    with pytest.raises(ValueError, match="SMTP_HOST"):
        get_api_settings()


def test_fails_when_config_owned_key_is_set_in_env(monkeypatch) -> None:
    monkeypatch.setenv("EMAIL_ENABLED", "false")

    with pytest.raises(ValueError, match="app/config/config.py-owned keys"):
        get_api_settings()


def test_fails_when_config_py_missing_required_key(runtime_config) -> None:
    cfg = runtime_config()
    missing_required = {k: v for k, v in cfg.items() if k != "GEOFENCE_SUBJECT_TEMPLATE"}
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = missing_required
    sys.modules["tests.runtime_config"] = module

    with pytest.raises(ValueError, match="app/config/config.py is missing required keys"):
        get_api_settings()


def test_fails_when_config_module_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "CONFIG_MODULE_PATH", "tests.missing_runtime_config")
    sys.modules.pop("tests.missing_runtime_config", None)

    with pytest.raises(ValueError, match="Missing app/config/config.py"):
        get_api_settings()


def test_fails_when_config_object_is_missing() -> None:
    module = types.ModuleType("tests.runtime_config")
    module.NOT_CONFIG = {}
    sys.modules["tests.runtime_config"] = module

    with pytest.raises(ValueError, match="must define CONFIG"):
        get_api_settings()


def test_shikari_settings_loads_repo_values(runtime_config) -> None:
    runtime_config(
        {
            "SHIKARI_SESSIONS_PATH": "data/shikari/sessions",
            "SHIKARI_OUTPUTS_PATH": "data/shikari/outputs",
            "SHIKARI_DEFAULT_THEME": "dark",
            "SHIKARI_DEFAULT_OUTPUT_FORMAT": "png",
        }
    )

    settings = get_shikari_settings()

    assert settings.shikari_sessions_path == "data/shikari/sessions"
    assert settings.shikari_outputs_path == "data/shikari/outputs"
    assert settings.shikari_default_theme == "dark"
    assert settings.shikari_default_output_format == "png"
