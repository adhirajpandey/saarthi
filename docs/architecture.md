# Architecture

## General

Saarthi has three execution surfaces:

- FastAPI runtime for HTTP-triggered workflows
- FastMCP runtime for authenticated local tool access
- CLI script runtime for operational automation

All surfaces reuse shared modules for settings, logging, and notification transports.

## High-Level Diagram

```text
                    +------------------------------+
                    |      app/config/config.py    |
                    | (non-sensitive runtime cfg)  |
                    +---------------+--------------+
                                    |
                    +---------------v--------------+
                    |          .env / env          |
                    | (secrets + connection values)|
                    +---------------+--------------+
                                    |
                         +----------v----------+
                         | shared/settings.py  |
                         | typed validation    |
                         +-----+----------+----+
                               |          |          |
                +--------------+          |          +------------------+
                |                         |                             |
      +---------v----------+     +--------v---------+        +---------v----------------+
      | FastAPI Runtime    |     | FastMCP Runtime  |        | Operational Script CLIs   |
      | app/main.py        |     | mcp-server       |        | backup-dbs / backup-gdrive|
      | routers + services |     | authenticated    |        | / schedule-scripts /      |
      |                    |     | tool access      |        | shikari-visualize         |
      +---------+----------+     +--------+---------+        +---------+----------------+
                |                         |                            |
      +---------v----------+     +--------v---------+        +---------v----------------+
      | SQLite + Geofence  |     | WhatsApp tool    |        | pg_dump / rclone /       |
      | transition engine  |     | via SSH sender   |        | systemd + cloud uploads  |
      +--------------------+     +------------------+        +--------------------------+

                          +------------------------------+
                          | shared/logging +             |
                          | shared/notifications/*       |
                          +------------------------------+
```

## Components

- `app/`: API runtime and business services
- `mcp-server/`: FastMCP runtime and tool definitions
- `scripts/`: operational command entry points
- `shared/`: cross-cutting runtime modules
- `tests/`: behavior and contract test suite
- `data/`: runtime data artifacts
- `logs/`: runtime logs

## API Runtime

Startup flow (`app/main.py`):

1. Load and validate API settings.
2. Load geofence mapping from JSON.
3. Initialize shared logging.
4. Initialize SQLite schema for location storage.
5. Attach settings and mapping to app state.

Layer responsibilities:

- Routers: HTTP contract + dependency wiring
- Dependencies: auth and settings access
- Services: persistence, transition detection, notification dispatch
- Health endpoint also reports host tool availability (`tailscale`, `rclone`, `pg_dump`)
  and performs a Tailscale reachability probe to Dell home.

Error shape:

- `AppError` is translated to `{"error": {"code", "message"}}`

## MCP Runtime

Startup flow (`mcp-server/server.py`):

1. Load and validate MCP settings.
2. Configure FastMCP bearer-token auth from `MCP_TOKEN`.
3. Register MCP tools.
4. Serve streamable HTTP on `/mcp`.

Current tool surface:

- `send_whatsapp_message(message)`: sends a WhatsApp message to
  `WHATSAPP_TARGET_PERSONAL` using the shared SSH WhatsApp transport.

Deployment defaults:

- Docker service: `saarthi-mcp`
- URL: `http://localhost:8001/mcp`
- Auth: `Authorization: Bearer <MCP_TOKEN>`

## Script Runtime

### `backup-dbs`

Flow:

1. Load typed backup settings.
2. Build database target map.
3. Run `pg_dump` per target.
4. Sanity-check and upload to S3.
5. Cleanup local dumps.
6. Send status notifications.

### `backup-gdrive`

Flow:

1. Load typed backup settings.
2. Run `rclone copy` for configured folders.
3. Aggregate output/failures.
4. Send status notifications.

### `schedule-scripts`

Flow:

1. Load scheduler JSON config.
2. Validate scheduler model.
3. Generate systemd unit files.
4. Reload daemon and enable timers.

### `shikari-visualize`

Flow:

1. Load typed Shikari settings.
2. Resolve session data from `SHIKARI_SESSIONS_PATH` (or CLI override).
3. Discover candidate sensor session folders.
4. Normalize sensor/meta CSV schemas.
5. Build combined Plotly dashboard.
6. Write outputs under `data/shikari/outputs` (by default).

## Shared Infrastructure

### Settings (`shared/settings.py`)

- `app/config/config.py`: non-sensitive operational values
- `.env` / environment: secrets and connection values

Validation enforces key ownership and channel-specific requirements.

### Logging (`shared/logging/setup.py`)

- Single setup path for API and scripts
- Console + file handlers
- Configurable format, level, date format, and file path

### Notification Transports (`shared/notifications/*`)

- SMTP email
- ntfy HTTP
- WhatsApp via SSH remote command

## Data and State

- `LOCATION_DB_PATH`: SQLite location history
- `GEOFENCE_MAPPING_PATH`: geofence definitions
- `MCP_TOKEN`: bearer token required by the MCP server
- `scripts/schedule_scripts/config.json`: scheduler input
- `data/shikari/sessions`: merged Shikari + Saarthi sensor sessions
- `data/shikari/outputs`: generated visualization artifacts
- Shikari config keys: `SHIKARI_SESSIONS_PATH`, `SHIKARI_OUTPUTS_PATH`,
  `SHIKARI_DEFAULT_THEME`, `SHIKARI_DEFAULT_OUTPUT_FORMAT`

## Remarks

- API, MCP, and scripts are intentionally separate entrypoints.
- Shared modules keep behavior consistent across runtimes.
