"""Tests for the Saarthi MCP server."""

import importlib.util
import asyncio
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

_WACLI_SOCKET = "/tmp/wacli-test.sock"
_PERSONAL_TARGET = "15550001111@s.whatsapp.net"


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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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

    assert result == {"success": True, "message": "Message accepted by WhatsApp"}
    assert captured["message"] == " hello "
    assert captured["whatsapp_settings"].target == _PERSONAL_TARGET


def test_send_personal_whatsapp_message_rejects_empty_message(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()
    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server, "send_whatsapp_transport", lambda **_: False)

    result = server.send_personal_whatsapp_message("hello")

    assert result == {"success": False, "message": "WhatsApp send was not confirmed"}


def test_mcp_auth_check_accepts_configured_github_user(runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()
    settings = server.get_mcp_settings()

    check = server.require_mcp_principal(settings.mcp_github_allowed_user_id)
    context = SimpleNamespace(
        token=SimpleNamespace(claims={"sub": str(settings.mcp_github_allowed_user_id)})
    )

    assert check(context) is True


def test_mcp_auth_check_rejects_other_github_user(runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()
    settings = server.get_mcp_settings()

    check = server.require_mcp_principal(settings.mcp_github_allowed_user_id)
    context = SimpleNamespace(token=SimpleNamespace(claims={"sub": "12345"}))

    assert check(context) is False


def test_mcp_auth_check_accepts_static_bearer_identity(runtime_config) -> None:
    server = _load_mcp_server()
    settings = server.get_mcp_settings()
    check = server.require_mcp_principal(settings.mcp_github_allowed_user_id)
    context = SimpleNamespace(
        token=SimpleNamespace(
            claims={
                "sub": server.STATIC_BEARER_SUBJECT,
                "auth_method": server.STATIC_BEARER_AUTH_METHOD,
            }
        )
    )

    assert check(context) is True


def test_mcp_auth_check_rejects_spoofed_static_bearer_identity(runtime_config) -> None:
    server = _load_mcp_server()
    settings = server.get_mcp_settings()
    check = server.require_mcp_principal(settings.mcp_github_allowed_user_id)
    context = SimpleNamespace(
        token=SimpleNamespace(
            claims={"sub": "12345", "auth_method": server.STATIC_BEARER_AUTH_METHOD}
        )
    )

    assert check(context) is False


def test_mcp_auth_check_rejects_missing_identity(runtime_config) -> None:
    server = _load_mcp_server()
    settings = server.get_mcp_settings()
    check = server.require_mcp_principal(settings.mcp_github_allowed_user_id)

    assert check(SimpleNamespace(token=None)) is False
    assert check(SimpleNamespace(token=SimpleNamespace(claims={}))) is False


def test_mcp_auth_combines_static_bearer_with_github_oauth(runtime_config) -> None:
    server = _load_mcp_server()
    settings = server.get_mcp_settings()

    auth = server.build_mcp_auth(settings)
    route_paths = {route.path for route in server.mcp.http_app(path="/mcp").routes}

    assert auth.__class__.__name__ == "MultiAuth"
    assert auth.server.__class__.__name__ == "GitHubProvider"
    assert len(auth.verifiers) == 1
    assert auth.verifiers[0].__class__.__name__ == "StaticBearerTokenVerifier"
    assert any(
        middleware.__class__.__name__ == "AuthMiddleware"
        for middleware in server.mcp.middleware
    )
    assert {
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-protected-resource/mcp",
        "/register",
        "/authorize",
        "/token",
        "/auth/callback",
        "/consent",
        "/mcp",
    } <= route_paths


def test_static_bearer_verifier_accepts_only_configured_token(runtime_config) -> None:
    server = _load_mcp_server()
    settings = server.get_mcp_settings()
    verifier = server.StaticBearerTokenVerifier(settings.mcp_static_bearer_token)

    accepted = asyncio.run(verifier.verify_token("test-static-bearer-token"))
    rejected = asyncio.run(verifier.verify_token("wrong-token"))

    assert accepted is not None
    assert accepted.client_id == server.STATIC_BEARER_CLIENT_ID
    assert accepted.scopes == ["read:user"]
    assert accepted.claims == {
        "sub": server.STATIC_BEARER_SUBJECT,
        "auth_method": server.STATIC_BEARER_AUTH_METHOD,
    }
    assert rejected is None


def test_oauth_code_exchange_persists_mapping_for_a_fresh_provider(
    monkeypatch, runtime_config, tmp_path
) -> None:
    import time

    import fastmcp
    from fastmcp.server.auth import AccessToken
    from fastmcp.server.auth.oauth_proxy.models import ClientCode
    from mcp.shared.auth import OAuthClientInformationFull

    # Exercise token exchange and encrypted persistence, not only tools/list.
    monkeypatch.setattr(fastmcp.settings, "home", tmp_path / "mcp")
    runtime_config()
    server = _load_mcp_server()
    settings = server.get_mcp_settings()
    auth = server.mcp.auth
    auth.set_mcp_path("/mcp")
    github_auth = auth.server
    assert github_auth is not None

    async def verify_upstream(token):
        assert token == "test-upstream-token"
        return AccessToken(
            token=token, client_id="test-client", scopes=["read:user"],
            claims={"sub": str(settings.mcp_github_allowed_user_id)},
        )

    async def exercise():
        client = OAuthClientInformationFull(
            client_id="test-client", redirect_uris=["http://localhost/callback"],
            token_endpoint_auth_method="none",
        )
        await github_auth.register_client(client)
        await github_auth._code_store.put(
            key="test-code",
            value=ClientCode(
                code="test-code", client_id="test-client",
                redirect_uri="http://localhost/callback", code_challenge="test-challenge",
                code_challenge_method="S256", scopes=["read:user"],
                idp_tokens={"access_token": "test-upstream-token", "expires_in": 120},
                expires_at=time.time() + 120, created_at=time.time(),
            ), ttl=120,
        )
        code = await github_auth.load_authorization_code(client, "test-code")
        assert code is not None
        token = await github_auth.exchange_authorization_code(client, code)
        assert token.access_token != "test-upstream-token"
        assert await github_auth.load_authorization_code(client, "test-code") is None

        fresh = server.build_mcp_auth(settings)
        fresh.set_mcp_path("/mcp")
        fresh_github_auth = fresh.server
        assert fresh_github_auth is not None
        monkeypatch.setattr(
            fresh_github_auth._token_validator,
            "verify_token",
            verify_upstream,
        )
        assert await fresh_github_auth.get_client("test-client") is not None
        validated = await fresh.verify_token(token.access_token)
        assert validated is not None
        assert validated.claims["sub"] == str(settings.mcp_github_allowed_user_id)

    asyncio.run(exercise())


def test_mcp_server_omits_whatsapp_tool_when_disabled(runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": False,
            "WHATSAPP_SOCKET_PATH": None,
            "WHATSAPP_TARGET_PERSONAL": None,
        }
    )

    server = _load_mcp_server()
    tool_names = {
        component.name
        for key, component in server.mcp._local_provider._components.items()
        if key.startswith("tool:")
    }

    assert "send_whatsapp_message" not in tool_names
    assert "search_transactions" in tool_names


def test_mcp_server_registers_whatsapp_tool_when_enabled(runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )

    server = _load_mcp_server()
    tool_names = {
        component.name
        for key, component in server.mcp._local_provider._components.items()
        if key.startswith("tool:")
    }

    assert "send_whatsapp_message" in tool_names


@pytest.mark.parametrize(
    ("enabled", "allowed_user"), [(True, True), (False, True), (True, False)]
)
def test_http_tool_discovery_respects_identity_and_whatsapp_flag(
    monkeypatch, runtime_config, enabled, allowed_user
) -> None:
    from fastmcp.server.auth import AccessToken
    from starlette.testclient import TestClient

    runtime_config({"WHATSAPP_ENABLED": enabled, "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET})
    server = _load_mcp_server()
    settings = server.get_mcp_settings()

    async def verify_test_token(token):
        if token != "test-discovery-token":
            return None
        return AccessToken(
            token=token,
            client_id="test-client",
            scopes=["read:user"],
            claims={"sub": str(settings.mcp_github_allowed_user_id) if allowed_user else "other-user"},
        )

    # Exercise the real HTTP and authorization middleware without GitHub or sends.
    monkeypatch.setattr(server.mcp.auth, "verify_token", verify_test_token)
    app = server.mcp.http_app(path="/mcp", json_response=True)
    with TestClient(app) as client:
        headers = {"Accept": "application/json, text/event-stream"}
        initialize = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "discovery-test", "version": "1"}},
        }
        assert client.post("/mcp", headers=headers, json=initialize).status_code == 401
        headers["Authorization"] = "Bearer test-discovery-token"
        response = client.post("/mcp", headers=headers, json=initialize)
        assert response.status_code == 200
        headers["Mcp-Session-Id"] = response.headers["mcp-session-id"]
        client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })
        response = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
        })
        assert response.status_code == 200
        tools = {tool["name"]: tool for tool in response.json()["result"]["tools"]}
        registered_tools = {
            component.name
            for key, component in server.mcp._local_provider._components.items()
            if key.startswith("tool:")
        }
        assert set(tools) == (registered_tools if allowed_user else set())
        assert ("send_whatsapp_message" in tools) == (enabled and allowed_user)
        assert ("search_transactions" in tools) == allowed_user
        if enabled and allowed_user:
            assert tools["send_whatsapp_message"]["inputSchema"]["required"] == ["message"]


def test_http_tool_discovery_accepts_static_bearer_token(runtime_config) -> None:
    from starlette.testclient import TestClient

    server = _load_mcp_server()
    app = server.mcp.http_app(path="/mcp", json_response=True)
    headers = {
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer test-static-bearer-token",
    }
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "static-token-test", "version": "1"},
        },
    }

    with TestClient(app) as client:
        invalid_headers = {**headers, "Authorization": "Bearer wrong-token"}
        assert client.post(
            "/mcp", headers=invalid_headers, json=initialize
        ).status_code == 401

        response = client.post("/mcp", headers=headers, json=initialize)
        assert response.status_code == 200
        headers["Mcp-Session-Id"] = response.headers["mcp-session-id"]
        client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        response = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )

    assert response.status_code == 200
    tools = {tool["name"] for tool in response.json()["result"]["tools"]}
    registered_tools = {
        component.name
        for key, component in server.mcp._local_provider._components.items()
        if key.startswith("tool:")
    }
    assert tools == registered_tools


def test_search_personal_transactions_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
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


def test_get_personal_notion_database_schema_delegates_to_service(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "get_notion_database_schema",
        lambda **kwargs: {"success": True, "schema": kwargs},
    )

    result = server.get_personal_notion_database_schema(database_key="links")

    assert result["success"] is True
    assert result["schema"]["database_key"] == "links"


def test_query_personal_notion_database_delegates_to_service(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "query_notion_database",
        lambda **kwargs: {"success": True, "filters": kwargs, "pages": []},
    )

    result = server.query_personal_notion_database(
        database_key="work_items",
        start_cursor="cursor-1",
        page_size=5,
        project="Habitat",
    )

    assert result["success"] is True
    assert result["filters"]["database_key"] == "work_items"
    assert result["filters"]["start_cursor"] == "cursor-1"
    assert result["filters"]["page_size"] == 5
    assert result["filters"]["project"] == "Habitat"


def test_notion_links_aliases_use_links_database_key(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "get_notion_database_schema",
        lambda **kwargs: {"success": True, "schema": kwargs},
    )
    monkeypatch.setattr(
        server,
        "query_notion_database",
        lambda **kwargs: {"success": True, "filters": kwargs, "pages": []},
    )

    schema_result = server.get_links_database_schema()
    list_result = server.list_saved_links(page_size=5)

    assert schema_result["schema"]["database_key"] == "links"
    assert list_result["filters"]["database_key"] == "links"
    assert list_result["filters"]["page_size"] == 5


def test_notion_work_items_aliases_use_work_items_database_key(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "get_notion_database_schema",
        lambda **kwargs: {"success": True, "schema": kwargs},
    )
    monkeypatch.setattr(
        server,
        "query_notion_database",
        lambda **kwargs: {"success": True, "filters": kwargs, "pages": []},
    )

    schema_result = server.get_work_items_database_schema()
    list_result = server.list_work_items(page_size=10, project="Trackcrow")

    assert schema_result["schema"]["database_key"] == "work_items"
    assert list_result["filters"]["database_key"] == "work_items"
    assert list_result["filters"]["page_size"] == 10
    assert list_result["filters"]["project"] == "Trackcrow"


def test_notion_greenhouse_experiment_aliases_use_greenhouse_database_key(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "get_notion_database_schema",
        lambda **kwargs: {"success": True, "schema": kwargs},
    )
    monkeypatch.setattr(
        server,
        "query_notion_database",
        lambda **kwargs: {"success": True, "filters": kwargs, "pages": []},
    )

    schema_result = server.get_greenhouse_experiments_schema()
    list_result = server.list_greenhouse_experiments(page_size=10)

    assert schema_result["schema"]["database_key"] == "greenhouse_experiments"
    assert list_result["filters"]["database_key"] == "greenhouse_experiments"
    assert list_result["filters"]["page_size"] == 10


def test_list_work_item_projects_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "list_notion_work_item_projects",
        lambda **kwargs: {
            "success": True,
            "count": 2,
            "projects": [
                {"name": "Habitat", "work_item_count": 3},
                {"name": "Vidwiz", "work_item_count": 7},
            ],
            "filters": kwargs,
        },
    )

    result = server.list_work_item_projects()

    assert result["success"] is True
    assert result["count"] == 2
    assert result["projects"][0]["name"] == "Habitat"


def test_create_personal_work_item_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "create_notion_work_item",
        lambda **kwargs: {"success": True, "page": kwargs},
    )

    result = server.create_personal_work_item(
        name="Ship Notion writes",
        project="Habitat",
        status="Pending",
        priority="High",
        category="Backend",
        description="MCP write path",
    )

    assert result["success"] is True
    assert result["page"]["name"] == "Ship Notion writes"
    assert result["page"]["project"] == "Habitat"
    assert result["page"]["description"] == "MCP write path"


def test_update_personal_work_item_delegates_to_service(monkeypatch, runtime_config) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "update_notion_work_item",
        lambda **kwargs: {"success": True, "page": kwargs},
    )

    result = server.update_personal_work_item(
        page_id="33333333-3333-3333-3333-333333333333",
        status="In Progress",
        description="Updated copy",
    )

    assert result["success"] is True
    assert result["page"]["page_id"] == "33333333-3333-3333-3333-333333333333"
    assert result["page"]["status"] == "In Progress"
    assert result["page"]["description"] == "Updated copy"


def test_create_greenhouse_experiment_delegates_to_service(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "create_notion_greenhouse_experiment",
        lambda **kwargs: {"success": True, "page": kwargs},
    )

    result = server.create_greenhouse_experiment(
        name="Run capacity benchmark",
        status="Pending",
        priority="P2",
        description="Measure the limit",
    )

    assert result["success"] is True
    assert result["page"]["name"] == "Run capacity benchmark"
    assert result["page"]["status"] == "Pending"
    assert result["page"]["priority"] == "P2"
    assert result["page"]["description"] == "Measure the limit"
    assert "category" not in result["page"]


def test_update_greenhouse_experiment_delegates_to_service(
    monkeypatch, runtime_config
) -> None:
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SOCKET_PATH": _WACLI_SOCKET,
            "WHATSAPP_TARGET_PERSONAL": _PERSONAL_TARGET,
        }
    )
    server = _load_mcp_server()

    monkeypatch.setattr(server, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server,
        "update_notion_greenhouse_experiment",
        lambda **kwargs: {"success": True, "page": kwargs},
    )

    result = server.update_greenhouse_experiment(
        page_id="55555555-5555-5555-5555-555555555555",
        status="Completed",
        description="Observed result",
    )

    assert result["success"] is True
    assert result["page"]["page_id"] == "55555555-5555-5555-5555-555555555555"
    assert result["page"]["status"] == "Completed"
    assert result["page"]["description"] == "Observed result"
    assert "category" not in result["page"]
