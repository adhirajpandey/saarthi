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

### `search_transactions`

Short description:
Searches Trackcrow transactions for the configured MCP user and returns
structured rows for agents.

Expected input:

```json
{
  "recipient": "medical store",
  "category": "Health",
  "keyword": "syrup",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31",
  "limit": 10
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "recipient": "medical store",
    "category": "Health",
    "keyword": "syrup",
    "start_date": "2026-01-01",
    "end_date": "2026-01-31",
    "limit": 10
  },
  "transactions": [
    {
      "id": 41,
      "timestamp": "2026-01-01T12:30:00Z",
      "amount": 120.5,
      "recipient": "Push Medical Store",
      "recipient_name": "Push Medical Store",
      "category": "Health",
      "subcategory": "Medicine",
      "type": "UPI",
      "remarks": "cough syrup",
      "location": "Bangalore"
    }
  ]
}
```

Failure:

```json
{
  "success": false,
  "message": "Failed to search Trackcrow transactions"
}
```

Remarks:

- At least one filter is required.
- `limit` defaults to `10` and is capped at `50`.
- `start_date` and `end_date` accept ISO-8601 date or datetime strings.
- Searches are always scoped to the configured `TRACKCROW_MCP_USER_UUID`.
- This tool reads Trackcrow data directly from Postgres; it does not call a
  Trackcrow HTTP API.

### `list_cloudflare_zones`

Short description:
Lists Cloudflare zones visible to the configured API token and returns
normalized rows for agents.

Expected input:

```json
{
  "name": "adhirajpandey.tech",
  "status": "active",
  "page": 1,
  "per_page": 10
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "name": "adhirajpandey.tech",
    "status": "active",
    "page": 1,
    "per_page": 10
  },
  "zones": [
    {
      "id": "8ed154052fec209b922b5f9877d4c6c5",
      "name": "adhirajpandey.tech",
      "status": "active",
      "paused": false,
      "type": "full",
      "created_on": "2026-01-01T00:00:00Z",
      "modified_on": "2026-01-02T00:00:00Z",
      "name_servers": ["kenneth.ns.cloudflare.com", "molly.ns.cloudflare.com"]
    }
  ]
}
```

Remarks:

- This tool is read-only.
- `page` defaults to `1`.
- `per_page` defaults to `20` and is capped at `100`.

### `search_cloudflare_dns_records`

Short description:
Lists DNS records from a Cloudflare zone and returns normalized rows for
agents.

Expected input:

```json
{
  "zone_name": "adhirajpandey.tech",
  "type": "CNAME",
  "proxied": true,
  "page": 1,
  "per_page": 20
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "zone_id": "8ed154052fec209b922b5f9877d4c6c5",
    "zone_name": "adhirajpandey.tech",
    "type": "CNAME",
    "name": null,
    "content": null,
    "proxied": true,
    "page": 1,
    "per_page": 20
  },
  "records": [
    {
      "id": "0cbc6033384a922aba0c768da8390e81",
      "zone_id": "8ed154052fec209b922b5f9877d4c6c5",
      "zone_name": "adhirajpandey.tech",
      "name": "saarthi.adhirajpandey.tech",
      "type": "CNAME",
      "content": "fc13605b-9729-4162-bd26-679a6fd134ff.cfargotunnel.com",
      "proxied": true,
      "ttl": 1,
      "comment": null,
      "created_on": "2026-01-01T00:00:00Z",
      "modified_on": "2026-01-02T00:00:00Z"
    }
  ]
}
```

Remarks:

- This tool is read-only.
- Exactly one of `zone_id` or `zone_name` is required.
- `zone_name` is resolved to a zone ID before DNS record lookup.

### `get_cloudflare_dns_record`

Short description:
Fetches one DNS record from a Cloudflare zone by record ID.

Expected input:

```json
{
  "zone_name": "adhirajpandey.tech",
  "record_id": "0cbc6033384a922aba0c768da8390e81"
}
```

Expected output:

Success:

```json
{
  "success": true,
  "record": {
    "id": "0cbc6033384a922aba0c768da8390e81",
    "zone_id": "8ed154052fec209b922b5f9877d4c6c5",
    "zone_name": "adhirajpandey.tech",
    "name": "saarthi.adhirajpandey.tech",
    "type": "CNAME",
    "content": "fc13605b-9729-4162-bd26-679a6fd134ff.cfargotunnel.com",
    "proxied": true,
    "ttl": 1,
    "comment": null,
    "created_on": "2026-01-01T00:00:00Z",
    "modified_on": "2026-01-02T00:00:00Z"
  }
}
```

Remarks:

- This tool is read-only.
- Exactly one of `zone_id` or `zone_name` is required.

## Configuration

Secrets / auth (`.env`):

- `MCP_TOKEN`
- `CLOUDFLARE_API_TOKEN`
- `TRACKCROW_DB_URL`
- `TRACKCROW_MCP_USER_UUID`

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
- `CLOUDFLARE_API_TOKEN` is required for the Cloudflare MCP tools.
- `TRACKCROW_MCP_USER_UUID` fixes the Trackcrow user scope for transaction
  searches.
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
