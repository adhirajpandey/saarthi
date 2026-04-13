"""Tests for the Saarthi MCP server."""

import importlib.util
import asyncio
from pathlib import Path
from types import ModuleType

import pytest


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
            "WHATSAPP_REMOTE_SCRIPT_PATH": "/remote/send.py",
            "WHATSAPP_TARGET_PERSONAL": "1203@s.whatsapp.net",
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
    assert captured["whatsapp_settings"].target == "1203@s.whatsapp.net"


def test_send_personal_whatsapp_message_rejects_empty_message(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "pookie",
            "WHATSAPP_REMOTE_SCRIPT_PATH": "/remote/send.py",
            "WHATSAPP_TARGET_PERSONAL": "1203@s.whatsapp.net",
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
            "WHATSAPP_REMOTE_SCRIPT_PATH": "/remote/send.py",
            "WHATSAPP_TARGET_PERSONAL": "1203@s.whatsapp.net",
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
            "WHATSAPP_REMOTE_SCRIPT_PATH": "/remote/send.py",
            "WHATSAPP_TARGET_PERSONAL": "1203@s.whatsapp.net",
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
            "WHATSAPP_REMOTE_SCRIPT_PATH": "/remote/send.py",
            "WHATSAPP_TARGET_PERSONAL": "1203@s.whatsapp.net",
        }
    )
    monkeypatch.setenv("MCP_TOKEN", "valid-token")
    server = _load_mcp_server()
    settings = server.get_mcp_settings()

    token = asyncio.run(server.build_mcp_auth(settings).verify_token("invalid-token"))

    assert token is None
