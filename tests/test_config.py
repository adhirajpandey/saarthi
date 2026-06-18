"""Tests for configuration loading."""

import sys
import types

import pytest

import shared.settings as settings_module
from shared.settings import (
    get_backup_db_settings,
    get_backup_gdrive_settings,
    get_api_settings,
    get_cloudflare_settings,
    get_google_tasks_settings,
    get_mcp_settings,
    get_restore_db_test_settings,
    get_shikari_settings,
)

_HERMES_BIN = "/home/pookie/.local/bin/hermes"
_HERMES_DM_TARGET = "whatsapp:166601898885178@lid"
_HERMES_GROUP_TARGET = "whatsapp:120363369409471870@g.us"


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
            "WHATSAPP_HERMES_COMMAND_PATH": None,
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
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_FAMILY": _HERMES_GROUP_TARGET,
        }
    )

    monkeypatch.delenv("SMTP_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)

    settings = get_api_settings()
    assert settings.email_enabled is False
    assert settings.whatsapp_enabled is True


def test_mcp_settings_requires_personal_whatsapp_target(runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": None,
        }
    )

    with pytest.raises(ValueError, match="WHATSAPP_TARGET_PERSONAL"):
        get_mcp_settings()


def test_mcp_settings_requires_mcp_token(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.delenv("MCP_TOKEN", raising=False)

    with pytest.raises(ValueError, match="mcp_token"):
        get_mcp_settings()


def test_mcp_settings_requires_trackcrow_user_uuid(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.delenv("TRACKCROW_MCP_USER_UUID", raising=False)

    with pytest.raises(ValueError, match="trackcrow_mcp_user_uuid"):
        get_mcp_settings()


def test_mcp_settings_requires_trackcrow_db_url(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.delenv("TRACKCROW_DB_URL", raising=False)

    with pytest.raises(ValueError, match="trackcrow_db_url"):
        get_mcp_settings()


def test_cloudflare_settings_requires_api_token(monkeypatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="cloudflare_api_token"):
        get_cloudflare_settings()


def test_google_tasks_settings_require_client_id(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_TASKS_CLIENT_ID", raising=False)
    monkeypatch.setenv("GOOGLE_TASKS_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_TASKS_TOKEN_PATH", "/tmp/google-tasks-token.json")

    with pytest.raises(ValueError, match="google_tasks_client_id"):
        get_google_tasks_settings()


def test_google_tasks_settings_require_client_secret(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TASKS_CLIENT_ID", "client-id")
    monkeypatch.delenv("GOOGLE_TASKS_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_TASKS_TOKEN_PATH", "/tmp/google-tasks-token.json")

    with pytest.raises(ValueError, match="google_tasks_client_secret"):
        get_google_tasks_settings()


def test_google_tasks_settings_require_token_path(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TASKS_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_TASKS_CLIENT_SECRET", "client-secret")
    monkeypatch.delenv("GOOGLE_TASKS_TOKEN_PATH", raising=False)

    with pytest.raises(ValueError, match="google_tasks_token_path"):
        get_google_tasks_settings()


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


def test_global_env_audit_rejects_api_config_key_for_mcp_runtime(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.setenv("APP_NAME", "wrong-source")

    with pytest.raises(ValueError, match="APP_NAME"):
        get_mcp_settings()


def test_global_env_audit_rejects_gdrive_config_key_for_api_runtime(monkeypatch) -> None:
    monkeypatch.setenv("GDRIVE_SOURCE", "wrong-source")

    with pytest.raises(ValueError, match="GDRIVE_SOURCE"):
        get_api_settings()


def test_global_env_audit_rejects_restore_config_key_for_mcp_runtime(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.setenv("RESTORE_PG_IMAGE", "postgres:16")

    with pytest.raises(ValueError, match="RESTORE_PG_IMAGE"):
        get_mcp_settings()


def test_fails_when_config_py_missing_required_key(runtime_config) -> None:
    cfg = runtime_config()
    missing_required = {k: v for k, v in cfg.items() if k != "GEOFENCE_SUBJECT_TEMPLATE"}
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = missing_required
    sys.modules["tests.runtime_config"] = module

    with pytest.raises(ValueError, match="app/config/config.py is missing required keys"):
        get_api_settings()


def test_api_settings_ignore_restore_only_config_keys(runtime_config) -> None:
    cfg = runtime_config()
    trimmed = {
        key: value
        for key, value in cfg.items()
        if not key.startswith("RESTORE_") and "_RESTORE_" not in key
    }
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = trimmed
    sys.modules["tests.runtime_config"] = module

    settings = get_api_settings()

    assert settings.app_name == trimmed["APP_NAME"]


def test_mcp_settings_ignore_api_only_config_keys(runtime_config) -> None:
    cfg = runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    trimmed = {
        key: value
        for key, value in cfg.items()
        if key
        not in {
            "APP_NAME",
            "LOCATION_DB_PATH",
            "GEOFENCE_MAPPING_PATH",
            "DELL_TAILSCALE_IP",
            "GEOFENCE_SUBJECT_TEMPLATE",
            "GEOFENCE_EMAIL_TEMPLATE",
            "GEOFENCE_WHATSAPP_TEMPLATE",
            "GEOFENCE_UPDATES_RECIPIENT",
            "GEOFENCE_SENDER_NAME",
        }
    }
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = trimmed
    sys.modules["tests.runtime_config"] = module

    settings = get_mcp_settings()

    assert settings.mcp_token == "test-mcp-token"


def test_backup_gdrive_settings_ignore_restore_only_config_keys(runtime_config) -> None:
    cfg = runtime_config(
        {
            "NTFY_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    trimmed = {
        key: value
        for key, value in cfg.items()
        if not key.startswith("RESTORE_") and "_RESTORE_" not in key
    }
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = trimmed
    sys.modules["tests.runtime_config"] = module

    settings = get_backup_gdrive_settings()

    assert settings.gdrive_source == trimmed["GDRIVE_SOURCE"]


def test_restore_db_test_settings_require_restore_only_config_keys(runtime_config, monkeypatch) -> None:
    cfg = runtime_config(
        {
            "NTFY_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    missing_restore = {k: v for k, v in cfg.items() if k != "RESTORE_PG_IMAGE"}
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = missing_restore
    sys.modules["tests.runtime_config"] = module
    monkeypatch.setenv("AWS_ACCESS_KEY", "ak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("RESTORE_PG_PASSWORD", "postgres")

    with pytest.raises(ValueError, match="RESTORE_PG_IMAGE"):
        get_restore_db_test_settings()


def test_backup_gdrive_settings_require_gdrive_config_keys(runtime_config) -> None:
    cfg = runtime_config(
        {
            "NTFY_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    missing_gdrive = {k: v for k, v in cfg.items() if k != "GDRIVE_SOURCE"}
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = missing_gdrive
    sys.modules["tests.runtime_config"] = module

    with pytest.raises(ValueError, match="GDRIVE_SOURCE"):
        get_backup_gdrive_settings()


def test_shikari_settings_require_shikari_config_keys(runtime_config) -> None:
    cfg = runtime_config()
    missing_shikari = {k: v for k, v in cfg.items() if k != "SHIKARI_DEFAULT_THEME"}
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = missing_shikari
    sys.modules["tests.runtime_config"] = module

    with pytest.raises(ValueError, match="SHIKARI_DEFAULT_THEME"):
        get_shikari_settings()


def test_runtime_specific_config_keys_are_rejected_from_env(monkeypatch) -> None:
    monkeypatch.setenv("RESTORE_PG_IMAGE", "postgres:16")

    with pytest.raises(ValueError, match="app/config/config.py-owned keys"):
        get_restore_db_test_settings()


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


def test_restore_db_test_settings_loads_repo_and_env_values(runtime_config, monkeypatch) -> None:
    runtime_config(
        {
            "NTFY_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
            "RESTORE_PG_IMAGE": "postgres:16",
            "RESTORE_TIMEOUT_SECONDS": 90,
            "RESTORE_TEMP_DIR": "data/restore-tests",
            "VIDWIZ_RESTORE_TEST_QUERY": "SELECT 1",
            "VIDWIZ_RESTORE_EXPECTED_OUTPUT": "1",
            "TRACKCROW_RESTORE_TEST_QUERY": "SELECT 2",
            "TRACKCROW_RESTORE_EXPECTED_OUTPUT": "2",
            "SMASHDIARY_RESTORE_TEST_QUERY": "SELECT 3",
            "SMASHDIARY_RESTORE_EXPECTED_OUTPUT": "3",
        }
    )
    monkeypatch.setenv("AWS_ACCESS_KEY", "ak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("RESTORE_PG_PASSWORD", "postgres")

    settings = get_restore_db_test_settings()

    assert settings.restore_pg_image == "postgres:16"
    assert settings.restore_timeout_seconds == 90
    assert settings.restore_pg_password == "postgres"
    assert settings.smashdiary_restore_expected_output == "3"


def test_restore_db_settings_ignore_api_only_config_keys(runtime_config, monkeypatch) -> None:
    cfg = runtime_config(
        {
            "NTFY_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
            "RESTORE_PG_IMAGE": "postgres:16",
            "RESTORE_TIMEOUT_SECONDS": 90,
            "RESTORE_TEMP_DIR": "data/restore-tests",
            "VIDWIZ_RESTORE_TEST_QUERY": "SELECT 1",
            "VIDWIZ_RESTORE_EXPECTED_OUTPUT": "1",
            "TRACKCROW_RESTORE_TEST_QUERY": "SELECT 2",
            "TRACKCROW_RESTORE_EXPECTED_OUTPUT": "2",
            "SMASHDIARY_RESTORE_TEST_QUERY": "SELECT 3",
            "SMASHDIARY_RESTORE_EXPECTED_OUTPUT": "3",
        }
    )
    trimmed = {
        key: value
        for key, value in cfg.items()
        if key
        not in {
            "APP_NAME",
            "LOCATION_DB_PATH",
            "GEOFENCE_MAPPING_PATH",
            "DELL_TAILSCALE_IP",
            "GEOFENCE_SUBJECT_TEMPLATE",
            "GEOFENCE_EMAIL_TEMPLATE",
            "GEOFENCE_WHATSAPP_TEMPLATE",
            "GEOFENCE_UPDATES_RECIPIENT",
            "GEOFENCE_SENDER_NAME",
        }
    }
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = trimmed
    sys.modules["tests.runtime_config"] = module
    monkeypatch.setenv("AWS_ACCESS_KEY", "ak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("RESTORE_PG_PASSWORD", "postgres")

    settings = get_restore_db_test_settings()

    assert settings.restore_pg_image == "postgres:16"


def test_backup_db_settings_still_requires_live_db_urls(runtime_config, monkeypatch) -> None:
    runtime_config(
        {
            "NTFY_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.setenv("AWS_ACCESS_KEY", "ak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "sk")
    monkeypatch.delenv("VIDWIZ_DB_URL", raising=False)
    monkeypatch.delenv("TRACKCROW_DB_URL", raising=False)
    monkeypatch.delenv("SMASHDIARY_DB_URL", raising=False)

    with pytest.raises(ValueError, match="vidwiz_db_url|trackcrow_db_url|smashdiary_db_url"):
        get_backup_db_settings()


def test_backup_db_settings_ignore_restore_only_config_keys(runtime_config, monkeypatch) -> None:
    cfg = runtime_config(
        {
            "NTFY_ENABLED": False,
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    trimmed = {
        key: value
        for key, value in cfg.items()
        if not key.startswith("RESTORE_") and "_RESTORE_" not in key
    }
    module = types.ModuleType("tests.runtime_config")
    module.CONFIG = trimmed
    sys.modules["tests.runtime_config"] = module
    monkeypatch.setenv("AWS_ACCESS_KEY", "ak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("VIDWIZ_DB_URL", "postgres://vidwiz")
    monkeypatch.setenv("TRACKCROW_DB_URL", "postgres://trackcrow")
    monkeypatch.setenv("SMASHDIARY_DB_URL", "postgres://smashdiary")

    settings = get_backup_db_settings()

    assert settings.vidwiz_db_url == "postgres://vidwiz"
