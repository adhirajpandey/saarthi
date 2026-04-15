# MCP

## General

Saarthi exposes authenticated local tool access through a separate FastMCP
runtime. This is not part of the FastAPI app and is not exposed through the
HTTP API docs.

Runtime entrypoint:

- `mcp-server/server.py`

Docker service:

- `saarthi-mcp`

Default endpoint:

```text
http://localhost:8001/mcp
```

## Auth

MCP requests require:

- Header: `Authorization: Bearer <MCP_TOKEN>`

Codex should connect to the configured `saarthi` MCP server and supply the
bearer token from `MCP_TOKEN`.

Expected Codex MCP config:

```toml
[mcp_servers.saarthi]
url = "http://127.0.0.1:8001/mcp"
bearer_token_env_var = "MCP_TOKEN"
```

The Saarthi MCP container and the Codex process must see the same `MCP_TOKEN`
value.

## Tools

### `send_whatsapp_message`

Short description:
Sends a WhatsApp message through the shared SSH WhatsApp sender.

Expected input:

```json
{
  "message": "Hello from Saarthi"
}
```

Expected output:

Success:

```json
{
  "success": true,
  "message": "WhatsApp message sent"
}
```

Failure:

```json
{
  "success": false,
  "message": "Failed to send WhatsApp message"
}
```

Remarks:

- Empty or whitespace-only messages are rejected.
- The recipient is fixed to `WHATSAPP_TARGET_PERSONAL`.
- The MCP server defines the tool boundary; actual sending is performed by
  `shared.notifications.whatsapp`.

## Configuration

Secrets / auth (`.env`):

- `MCP_TOKEN`

Configuration (`app/config/config.py`):

- `WHATSAPP_ENABLED`
- `WHATSAPP_SSH_HOST`
- `WHATSAPP_REMOTE_SCRIPT_PATH`
- `WHATSAPP_TARGET_PERSONAL`
- `WHATSAPP_TIMEOUT_SECONDS`

Remarks:

- `WHATSAPP_ENABLED` must be enabled for the MCP runtime.
- `WHATSAPP_TARGET_PERSONAL` is required because MCP messages are sent to the
  personal target, not the geofence family target.
- The SSH private key is mounted into the `saarthi-mcp` container by
  `docker-compose.yml`.

## Verify

```bash
docker compose logs saarthi-mcp
codex mcp get saarthi
```

## Runtime Boundaries

- MCP tools are exposed by FastMCP on `/mcp`.
- HTTP endpoints are documented in `api.md`.
- Operational CLIs are documented in `scripts.md`.
- MCP is served by `mcp-server/server.py`; it is not a `pyproject.toml` script
  entry point.
