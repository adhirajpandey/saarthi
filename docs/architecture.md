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
      | routers + services |     | authenticated    |        | / cloudflare-zones /     |
      |                    |     | tool access      |        | cloudflare-dns /         |
      |                    |     |                  |        | google-tasks-auth /      |
      |                    |     |                  |        | restore-dbs-test /       |
      |                    |     |                  |        | shikari-visualize        |
      +---------+----------+     +--------+---------+        +---------+----------------+
                |                         |                            |
      +---------v----------+     +--------v---------+        +---------v----------------+
      | SQLite + Geofence  |     | WhatsApp tool    |        | pg_dump / rclone /       |
      | transition engine  |     | via SSH sender   |        | cloud uploads            |
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
5. Initialize the in-memory health response cache.
6. Attach settings, mapping, and cache to app state.

Layer responsibilities:

- Routers: HTTP contract + dependency wiring
- Dependencies: auth and settings access
- Services: persistence, transition detection, notification dispatch, and
  runtime availability checks
- The public health endpoint reports coarse state for SQLite, geofence mapping,
  email, and WhatsApp. Results are cached per API process for the configured
  TTL so repeated requests do not repeatedly probe dependencies.
- Health probes never send notifications. Public responses contain only
  `healthy`/`degraded` and `available`/`unavailable`/`disabled` states.

Error shape:

- `AppError` is translated to `{"error": {"code", "message"}}`

## MCP Runtime

Startup flow (`mcp-server/server.py`):

1. Load and validate MCP settings.
2. Configure FastMCP bearer-token auth from `MCP_TOKEN`.
3. Register MCP tools, including `send_whatsapp_message` only when WhatsApp is enabled.
4. Serve streamable HTTP on `/mcp`.

Current tool surface:

- `send_whatsapp_message(message)`: when WhatsApp is enabled, sends a message
  to `WHATSAPP_TARGET_PERSONAL` using the shared SSH WhatsApp transport.
- `search_transactions(...)`: reads Trackcrow transactions for the configured
  MCP user.
- `list_cloudflare_zones(...)`: lists zones visible to the configured
  Cloudflare token.
- `search_cloudflare_dns_records(...)`: lists DNS records from a Cloudflare
  zone.
- `get_cloudflare_dns_record(...)`: fetches one DNS record by record ID.
- `list_google_tasklists(...)`: lists Google Tasks task lists for the
  configured personal account.
- `list_google_tasks(...)`: lists tasks from one Google task list.
- `get_google_task(...)`: fetches one Google task by ID from one Google task
  list.
- `get_notion_database_schema(database_key)`: returns schema metadata for the
  configured Notion `links`, `work_items`, or `greenhouse_experiments`
  database.
- `query_notion_database(...)`: queries rows from the configured Notion
  `links`, `work_items`, or `greenhouse_experiments` database.
- `get_links_database_schema()`: returns schema metadata for the saved links
  Notion database.
- `list_saved_links(...)`: lists saved links from Notion.
- `get_work_items_database_schema()`: returns schema metadata for the
  work items Notion database.
- `list_work_items(...)`: lists Notion work items, optionally filtered by
  project.
- `list_work_item_projects()`: lists project names that currently have work
  items, with counts.
- `create_work_item(...)`: creates a work item in the Notion work items
  database.
- `update_work_item(...)`: updates a work item by Notion `page_id`.
- `get_greenhouse_experiments_schema()`: returns schema metadata for the
  Greenhouse experiments Notion database.
- `list_greenhouse_experiments(...)`: lists Greenhouse experiments from Notion.
- `create_greenhouse_experiment(...)`: creates a Greenhouse experiment.
- `update_greenhouse_experiment(...)`: updates a Greenhouse experiment by
  Notion `page_id`.

Detailed MCP contracts are documented in `mcp.md`.

Deployment defaults:

- Docker service: `saarthi-mcp`
- URL: `http://localhost:8001/mcp`
- Auth: `Authorization: Bearer <MCP_TOKEN>`

### Notion MCP tools

Flow:

1. Load typed Notion settings.
2. Resolve the configured Notion database URL to a database ID.
3. Fetch the single data source attached to that database.
4. Read schema metadata or query rows from the Notion Data Sources API for
   read-only tools.
5. Fetch the live data-source schema for write tools.
6. Serialize typed work-item or Greenhouse experiment fields to the actual
   Notion property types exposed by that schema, then create or patch the page.
7. Normalize page properties into agent-friendly MCP payloads.

Current Notion scope:

- `links`: saved links database, read-only
- `work_items`: work items database, read/write through MCP
- `greenhouse_experiments`: Greenhouse experiments database, read/write through
  MCP

Work items use a `Project` select with current options `Vidwiz`, `Trackcrow`,
and `Habitat`. Current typed work-item write fields are `Name`, `Project`,
`Status`, `Priority`, `Category`, and `Description`.
Greenhouse experiments live in their own Notion database and expose `Name`,
`Status`, `Priority`, and `Description`.
The write paths are schema-driven and do not assume any one fixed Notion
property subtype for fields such as `Status`.

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

### `restore-dbs-test`

Flow:

1. Load typed restore verification settings.
2. Build restore target map from shared S3 artifact config plus per-DB test queries.
3. Create a disposable per-run workspace under `RESTORE_TEMP_DIR`.
4. Find the latest S3 backup for each configured database.
5. Download, restore into disposable PostgreSQL containers, and run verification queries.
6. Remove the run workspace and containers.
7. Send status notifications.

### `cloudflare-zones`

Flow:

1. Load typed Cloudflare settings.
2. Validate CLI filters.
3. Call the Cloudflare zones API.
4. Normalize zone payloads.
5. Print human-readable or JSON output.

### `cloudflare-dns`

Flow:

1. Load typed Cloudflare settings.
2. Validate CLI filters.
3. Resolve `zone_name` to `zone_id` when required.
4. Call the Cloudflare DNS records API.
5. Normalize record payloads.
6. Print human-readable or JSON output.

### `google-tasks-auth`

Flow:

1. Load typed Google Tasks settings.
2. Start Google OAuth for the configured Desktop app client.
3. Complete either local-browser or headless pasted-redirect auth flow.
4. Write authorized-user token JSON to `GOOGLE_TASKS_TOKEN_PATH`.

### Google Tasks MCP tools

Flow:

1. Load typed Google Tasks settings.
2. Load authorized-user credentials from `GOOGLE_TASKS_TOKEN_PATH`.
3. Refresh access tokens when needed using the stored refresh token.
4. Call the Google Tasks API.
5. Normalize task list or task payloads for MCP consumers.

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

Validation enforces key ownership, runtime-specific config subsets, and
channel-specific requirements for API, MCP, DB backup, DB restore verification,
GDrive backup, and Shikari runtimes.

### Logging (`shared/logging/setup.py`)

- Single setup path for API, MCP, and scripts
- Console + file handlers
- Configurable format, level, date format, and file path
- DB and GDrive backup CLIs intentionally disable the file handler so host cron
  can keep separate full logs without duplicating their output in `app.log`.

### Notification Transports (`shared/notifications/*`)

- SMTP email
- WhatsApp via SSH remote command

## Runtime Paths and State

- `LOCATION_DB_PATH`: SQLite location history
- `GEOFENCE_MAPPING_PATH`: geofence definitions
- `HEALTH_CACHE_TTL_SECONDS`: per-process health response cache TTL
- `GEOFENCE_SUBJECT_TEMPLATE`: geofence email subject format
- `GEOFENCE_EMAIL_TEMPLATE`: geofence email body format using `{area}` and `{event}`
- `GEOFENCE_WHATSAPP_ENTERED_TEMPLATE`: geofence WhatsApp body for `entered` events
- `GEOFENCE_WHATSAPP_EXITED_TEMPLATE`: geofence WhatsApp body for `exited` events
- `MCP_TOKEN`: bearer token required by the MCP server
- `CLOUDFLARE_API_TOKEN`: API token used by Cloudflare scripts and MCP tools
- `GOOGLE_TASKS_CLIENT_ID`: OAuth client ID for Google Tasks personal auth
- `GOOGLE_TASKS_CLIENT_SECRET`: OAuth client secret for Google Tasks personal
  auth
- `GOOGLE_TASKS_TOKEN_PATH`: authorized-user token JSON written by
  `google-tasks-auth` and used by Google Tasks MCP tools
- `NOTION_API_KEY`: integration token used by the Notion MCP tools
- `NOTION_LINKS_DATABASE_URL`: saved links Notion database URL or ID
- `NOTION_WORK_ITEMS_DATABASE_URL`: work items Notion database URL or ID
- `NOTION_GREENHOUSE_EXPERIMENTS_DATABASE_URL`: Greenhouse experiments Notion
  database URL or ID
- `data/shikari/sessions`: merged Shikari + Saarthi sensor sessions
- `data/shikari/outputs`: generated visualization artifacts
- Shikari config keys: `SHIKARI_SESSIONS_PATH`, `SHIKARI_OUTPUTS_PATH`,
  `SHIKARI_DEFAULT_THEME`, `SHIKARI_DEFAULT_OUTPUT_FORMAT`

## Remarks

- API, MCP, and scripts are intentionally separate entrypoints.
- Runtime-specific docs contain the full config and secret requirements.
- Shared modules keep behavior consistent across runtimes.
