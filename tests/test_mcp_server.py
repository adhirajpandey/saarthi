"""Tests for the Saarthi MCP server."""

import importlib.util
import asyncio
from pathlib import Path
from types import ModuleType

import pytest

_HERMES_BIN = "/home/pookie/.local/bin/hermes"
_HERMES_DM_TARGET = "whatsapp:166601898885178@lid"


def _load_mcp_server() -> ModuleType:
    server_path = Path(__file__).resolve().parents[1] / "mcp-server" / "server.py"
    spec = importlib.util.spec_from_file_location("saarthi_mcp_server", server_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load MCP server module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_send_personal_whatsapp_message_uses_personal_target(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()
    captured: dict[str, object] = {}

    def _fake_send_whatsapp_transport(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server, "send_whatsapp_transport", _fake_send_whatsapp_transport)

    result = server.send_personal_whatsapp_message(" hello ")

    assert result == {"success": True, "message": "WhatsApp message sent"}
    assert captured["message"] == " hello "
    assert captured["whatsapp_settings"].target == _HERMES_DM_TARGET


def test_send_personal_whatsapp_message_rejects_empty_message(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()
    monkeypatch.setattr(
        server,
        "send_whatsapp_transport",
        lambda **_: pytest.fail("transport should not be called"),
    )

    with pytest.raises(ValueError, match="message must not be empty"):
        server.send_personal_whatsapp_message("   ")


def test_send_personal_whatsapp_message_reports_transport_failure(
    monkeypatch,
    runtime_config,
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()
    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server, "send_whatsapp_transport", lambda **_: False)

    result = server.send_personal_whatsapp_message("hello")

    assert result == {"success": False, "message": "Failed to send WhatsApp message"}


def test_mcp_auth_accepts_configured_token(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.setenv("MCP_TOKEN", "valid-token")
    server = _load_mcp_server()
    settings = server.get_mcp_settings()

    token = asyncio.run(server.build_mcp_auth(settings).verify_token("valid-token"))

    assert token is not None
    assert token.client_id == "saarthi"


def test_mcp_auth_rejects_invalid_token(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    monkeypatch.setenv("MCP_TOKEN", "valid-token")
    server = _load_mcp_server()
    settings = server.get_mcp_settings()

    token = asyncio.run(server.build_mcp_auth(settings).verify_token("invalid-token"))

    assert token is None


def test_search_personal_transactions_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "search_trackcrow_transactions",
        lambda **kwargs: {"success": True, "count": 0, "filters": kwargs, "transactions": []},
    )

    result = server.search_personal_transactions(keyword="groceries", limit=5)

    assert result["success"] is True
    assert result["filters"]["keyword"] == "groceries"
    assert result["filters"]["limit"] == 5


def test_list_personal_cloudflare_zones_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "list_zones",
        lambda **kwargs: {"success": True, "count": 1, "filters": kwargs, "zones": []},
    )

    result = server.list_personal_cloudflare_zones(name="example.com", per_page=5)

    assert result["success"] is True
    assert result["filters"]["name"] == "example.com"
    assert result["filters"]["per_page"] == 5


def test_search_personal_cloudflare_dns_records_delegates_to_service(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "list_dns_records",
        lambda **kwargs: {"success": True, "count": 1, "filters": kwargs, "records": []},
    )

    result = server.search_personal_cloudflare_dns_records(zone_name="example.com", type="A")

    assert result["success"] is True
    assert result["filters"]["zone_name"] == "example.com"
    assert result["filters"]["type"] == "A"


def test_get_personal_cloudflare_dns_record_delegates_to_service(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "get_dns_record",
        lambda **kwargs: {"success": True, "record": kwargs},
    )

    result = server.get_personal_cloudflare_dns_record(
        zone_id="zone-1",
        record_id="record-1",
    )

    assert result["success"] is True
    assert result["record"]["zone_id"] == "zone-1"
    assert result["record"]["record_id"] == "record-1"


def test_list_personal_google_tasklists_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "list_tasklists",
        lambda **kwargs: {"success": True, "count": 1, "filters": kwargs, "tasklists": []},
    )

    result = server.list_personal_google_tasklists(max_results=5)

    assert result["success"] is True
    assert result["filters"]["max_results"] == 5


def test_list_personal_google_tasks_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "list_tasks",
        lambda **kwargs: {"success": True, "count": 1, "filters": kwargs, "tasks": []},
    )

    result = server.list_personal_google_tasks(tasklist_title="Personal", max_results=5)

    assert result["success"] is True
    assert result["filters"]["tasklist_title"] == "Personal"
    assert result["filters"]["max_results"] == 5


def test_get_personal_google_task_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "get_task",
        lambda **kwargs: {"success": True, "task": kwargs},
    )

    result = server.get_personal_google_task(task_id="task-1", tasklist_id="list-1")

    assert result["success"] is True
    assert result["task"]["task_id"] == "task-1"
    assert result["task"]["tasklist_id"] == "list-1"
