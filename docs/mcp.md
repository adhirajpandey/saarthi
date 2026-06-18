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

### `list_google_tasklists`

Short description:
Lists Google task lists for the configured personal account and returns
normalized rows for agents.

Expected input:

```json
{
  "page_token": null,
  "max_results": 10
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "page_token": null,
    "max_results": 10
  },
  "next_page_token": null,
  "tasklists": [
    {
      "id": "MTUyMjg3MTU1OTQ5ODAxNzE1MDU6MDow",
      "title": "My Tasks",
      "updated": "2026-06-11T21:02:33.729Z",
      "self_link": "https://www.googleapis.com/tasks/v1/users/@me/lists/MTUyMjg3MTU1OTQ5ODAxNzE1MDU6MDow"
    }
  ]
}
```

Remarks:

- This tool is read-only.
- `max_results` defaults to `100` and is capped at `100`.
- This tool reads task lists for the single Google account authorized through
  `google-tasks-auth`.

### `list_google_tasks`

Short description:
Lists tasks from one Google task list and returns normalized rows for agents.

Expected input:

```json
{
  "tasklist_title": "My Tasks",
  "page_token": null,
  "max_results": 20,
  "show_completed": true,
  "show_hidden": false,
  "show_deleted": false,
  "show_assigned": false
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "tasklist_id": "MTUyMjg3MTU1OTQ5ODAxNzE1MDU6MDow",
    "tasklist_title": "My Tasks",
    "page_token": null,
    "max_results": 20,
    "show_completed": true,
    "show_hidden": false,
    "show_deleted": false,
    "show_assigned": false
  },
  "next_page_token": null,
  "tasks": [
    {
      "id": "task-1",
      "title": "Buy milk",
      "status": "needsAction",
      "notes": "2 liters",
      "due": "2026-06-14T00:00:00.000Z",
      "completed": null,
      "updated": "2026-06-13T00:00:00.000Z",
      "deleted": false,
      "hidden": false,
      "parent": null,
      "position": "00000000000000000001",
      "web_view_link": "https://tasks.google.com/task/...",
      "self_link": "https://www.googleapis.com/tasks/v1/lists/.../tasks/task-1",
      "links": [],
      "assignment_info": null
    }
  ]
}
```

Remarks:

- This tool is read-only.
- Exactly one of `tasklist_id` or `tasklist_title` is required.
- `tasklist_title` is resolved to a single task list before task lookup.
- Title-based task list resolution only searches the first `100` Google task
  lists returned by the API.
- `show_assigned` defaults to `false`; assigned tasks are not returned unless
  explicitly requested.

### `get_google_task`

Short description:
Fetches one Google task by ID from one Google task list.

Expected input:

```json
{
  "tasklist_title": "My Tasks",
  "task_id": "task-1"
}
```

Expected output:

Success:

```json
{
  "success": true,
  "task": {
    "id": "task-1",
    "title": "Buy milk",
    "status": "needsAction",
    "notes": "2 liters",
    "due": "2026-06-14T00:00:00.000Z",
    "completed": null,
    "updated": "2026-06-13T00:00:00.000Z",
    "deleted": false,
    "hidden": false,
    "parent": null,
    "position": "00000000000000000001",
    "web_view_link": "https://tasks.google.com/task/...",
    "self_link": "https://www.googleapis.com/tasks/v1/lists/.../tasks/task-1",
    "links": [],
    "assignment_info": null
  }
}
```

Remarks:

- This tool is read-only.
- Exactly one of `tasklist_id` or `tasklist_title` is required.
- Title-based task list resolution only searches the first `100` Google task
  lists returned by the API.

## Configuration

Secrets / auth (`.env`):

- `MCP_TOKEN`
- `CLOUDFLARE_API_TOKEN`
- `GOOGLE_TASKS_CLIENT_ID`
- `GOOGLE_TASKS_CLIENT_SECRET`
- `GOOGLE_TASKS_TOKEN_PATH`
- `TRACKCROW_DB_URL`
- `TRACKCROW_MCP_USER_UUID`

Configuration (`app/config/config.py`):

- `WHATSAPP_ENABLED`
- `WHATSAPP_SSH_HOST`
- `WHATSAPP_HERMES_COMMAND_PATH`
- `WHATSAPP_TARGET_PERSONAL`
- `WHATSAPP_TIMEOUT_SECONDS`

Remarks:

- `WHATSAPP_ENABLED` must be enabled for the MCP runtime.
- `WHATSAPP_TARGET_PERSONAL` is required because MCP messages are sent to the
  personal target, not the geofence family target.
- `CLOUDFLARE_API_TOKEN` is required for the Cloudflare MCP tools.
- `GOOGLE_TASKS_CLIENT_ID` and `GOOGLE_TASKS_CLIENT_SECRET` must reference a
  Google OAuth Desktop app client with the Google Tasks API enabled.
- `GOOGLE_TASKS_TOKEN_PATH` must point to an authorized-user token JSON file
  created by `uv run google-tasks-auth` or
  `uv run google-tasks-auth --headless`.
- `TRACKCROW_MCP_USER_UUID` fixes the Trackcrow user scope for transaction
  searches.
- The SSH private key is mounted into the `saarthi-mcp` container by
  `docker-compose.yml`.

## Verify

```bash
docker compose logs saarthi-mcp
codex mcp get saarthi
uv run google-tasks-auth --headless
```

## Runtime Boundaries

- MCP tools are exposed by FastMCP on `/mcp`.
- HTTP endpoints are documented in `api.md`.
- Operational CLIs are documented in `scripts.md`.
- MCP is served by `mcp-server/server.py`; it is not a `pyproject.toml` script
  entry point.
