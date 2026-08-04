# Deployment

## Target

Raspberry Pi Linux host with:

- API in Docker Compose (`saarthi-api`)
- MCP server in Docker Compose (`saarthi-mcp`)
- Backups scheduled by host cron invoking Docker Compose one-shot runs
- Local Shikari visualization CLI for ride dashboards (`shikari-visualize`)

## Quick Setup

1. Create config files:

```bash
cp app/config/config.example.py app/config/config.py
cp .env.example .env
```

2. Fill values:

- `app/config/config.py`: non-secret settings
- Set `HEALTH_CACHE_TTL_SECONDS` to the number of seconds each API process
  should cache the complete `/health` response. The default is `60`; the value
  must be a positive integer.
- Operational backup and restore-verification scripts require
  `WHATSAPP_ENABLED`. Set `WHATSAPP_HERMES_COMMAND_PATH` explicitly to the
  correct binary path on that host and configure `WHATSAPP_TARGET_PERSONAL`.
  The example config leaves these values unset on purpose.
- For geofence WhatsApp notifications, set both
  `GEOFENCE_WHATSAPP_ENTERED_TEMPLATE` and
  `GEOFENCE_WHATSAPP_EXITED_TEMPLATE`. These replace the older single-template
  approach and allow natural phrasing per event.
- `.env`: secrets (`ADMIN_TOKEN`, `MCP_TOKEN`, `CLOUDFLARE_API_TOKEN`,
  `GOOGLE_TASKS_CLIENT_ID`, `GOOGLE_TASKS_CLIENT_SECRET`,
  `GOOGLE_TASKS_TOKEN_PATH`, `NOTION_API_KEY`,
  `NOTION_LINKS_DATABASE_URL`, `NOTION_WORK_ITEMS_DATABASE_URL`,
  `NOTION_GREENHOUSE_EXPERIMENTS_DATABASE_URL`,
  `TRACKCROW_MCP_USER_UUID`, SMTP/AWS/DB URLs,
  `RESTORE_PG_PASSWORD` as needed)
- `.env`: Docker host-side bind mount paths
  (`SAARTHI_DATA_PATH`, `SAARTHI_LOGS_PATH`,
  `SAARTHI_GOOGLE_TASKS_TOKEN_PATH`, `SAARTHI_RCLONE_CONFIG_PATH`,
  `SAARTHI_RCLONE_SERVICE_ACCOUNT_PATH`). Container-side targets are fixed in
  `docker-compose.yml` under `/app/data`, `/app/logs`, and `/app/secrets/...`.
  Set `GOOGLE_TASKS_TOKEN_PATH` to `/app/secrets/google/google-tasks-token.json`
  so the runtime setting matches the fixed container target.
- `SAARTHI_SSH_KEY_PATH` is required when `WHATSAPP_ENABLED` is true. When
  WhatsApp is disabled and the path is unset, Docker Compose mounts `/dev/null`
  instead so API, MCP, backup, and restore startup do not depend on an SSH key.
- Share the Notion integration tied to `NOTION_API_KEY` with all configured
  Notion databases, with read access for the saved links database and
  read/write access for the work items and Greenhouse experiments databases.
- `NOTION_WORK_ITEMS_DATABASE_URL` should point to the work items
  database that uses a `Project` select with `Vidwiz`, `Trackcrow`, and
  `Habitat`.
- `NOTION_GREENHOUSE_EXPERIMENTS_DATABASE_URL` should point to the Greenhouse
  experiments database with `Name`, `Status`, `Priority`, and `Description`.

3. Start API and MCP:

```bash
docker compose up --build -d
```

`docker-compose.yml` uses one file for API, MCP, and the profiled ops service.
The default `up` starts only `saarthi-api` and `saarthi-mcp`.

`saarthi-mcp` serves the MCP endpoint on `http://localhost:8001/mcp` and requires
`Authorization: Bearer <MCP_TOKEN>`. Detailed MCP setup is documented in `mcp.md`.
When `WHATSAPP_ENABLED` is false, MCP starts normally without the
`send_whatsapp_message` tool; its other configured tools remain available.

4. Configure host cron:

```bash
docker compose run --rm --no-deps saarthi-cron uv run backup-dbs >> /home/adhiraj/projects/saarthi/logs/cron-backup-dbs.log 2>&1
docker compose run --rm --no-deps saarthi-cron uv run backup-gdrive >> /home/adhiraj/projects/saarthi/logs/cron-backup-gdrive.log 2>&1
```

Add those commands to the host crontab at the desired schedule. The
`saarthi-cron` service is under the `cron` profile and is intended for
one-shot `docker compose run` invocations, not long-running `up`.
Both backup CLIs are console-only: they do not write to the shared `app.log`.
Cron captures their complete stdout and stderr in separate per-job files, so
backup output is not duplicated across log files. Keep `uv run` in the
container command because the project entry points are installed in its uv
environment rather than on the container's global `PATH`.
For services running on the Docker host itself, use `host.docker.internal`
in `.env` connection URLs rather than `localhost`; inside a container,
`localhost` points at the container.

5. Ensure Shikari data paths exist:

```bash
mkdir -p data/shikari/sessions data/shikari/outputs
```

6. Authorize Google Tasks for MCP reads:

```bash
uv run google-tasks-auth --headless
```

This writes authorized-user token JSON to `GOOGLE_TASKS_TOKEN_PATH`. For a
headless host, open the printed Google login URL on another machine, complete
sign-in, copy the final `http://127.0.0.1:1/...` redirect URL from the browser
address bar, and paste it back into the terminal prompt.

Set `SAARTHI_GOOGLE_TASKS_TOKEN_PATH` to the host token file and set
`GOOGLE_TASKS_TOKEN_PATH=/app/secrets/google/google-tasks-token.json`.

## Verify

```bash
curl -s http://localhost:8000/health
docker compose logs saarthi-api
docker compose logs saarthi-mcp
codex mcp get saarthi
docker compose run --rm --no-deps saarthi-cron uv run backup-dbs
docker compose run --rm --no-deps saarthi-cron uv run backup-gdrive
uv run cloudflare-zones list
uv run cloudflare-dns list --zone-name adhirajpandey.tech --proxied
uv run google-tasks-auth --headless
uv run shikari-visualize --list
```

The health response should return HTTP `200` with an overall `healthy` or
`degraded` status and coarse states for `location_database`,
`geofence_mapping`, `email`, and `whatsapp`. Repeated requests within
`HEALTH_CACHE_TTL_SECONDS` return the same in-memory result without re-running
the underlying checks. A degraded response indicates that at least one
required or enabled integration is unavailable; inspect `saarthi-api` logs for
details.

For Notion MCP verification, confirm these tool calls succeed from the client:

- `get_links_database_schema()`
- `list_saved_links(page_size=5)`
- `get_work_items_database_schema()`
- `list_work_items(project="all", page_size=5)`
- `list_work_item_projects()`
- `create_work_item(name="Saarthi MCP verification item", project="Habitat")`
- `update_work_item(page_id="<page_id from create_work_item>", status="Completed")`
- `get_greenhouse_experiments_schema()`
- `list_greenhouse_experiments(page_size=5)`
- `create_greenhouse_experiment(name="Saarthi MCP verification experiment")`
- `update_greenhouse_experiment(page_id="<page_id from create_greenhouse_experiment>", status="Completed")`

## Common Ops

```bash
# Redeploy after update
git pull
docker compose up --build -d

# Restart service
docker compose restart saarthi-api
docker compose restart saarthi-mcp

# Manual backup runs
docker compose run --rm --no-deps saarthi-cron uv run backup-dbs
docker compose run --rm --no-deps saarthi-cron uv run backup-gdrive

# Manual Cloudflare reads
uv run cloudflare-zones list
uv run cloudflare-dns list --zone-name adhirajpandey.tech --proxied

# Google Tasks auth bootstrap
uv run google-tasks-auth --headless

# Manual Shikari output generation
uv run shikari-visualize --list
uv run shikari-visualize 2026-03-13-22:02:58 --output html
```

### Manual database restore verification

Run restore verification directly from the Docker host when you need to prove
that the latest S3 backups can be restored—for example after changing backup
settings or during a periodic disaster-recovery check:

```bash
cd /home/adhiraj/projects/saarthi
uv run restore-dbs-test
```

This is intentionally a host-only, manually initiated operation. Do not add it
to host cron and do not run it through `saarthi-cron`. The script uses the
host's Docker CLI to start and remove disposable PostgreSQL containers; the ops
container intentionally has no Docker socket mount.

Before running, confirm that the repository dependencies and runtime
configuration are current, the host user can run Docker, the configured
PostgreSQL image is available, and the host can access S3. Success requires a
`Restore verification passed` line for every configured database, followed by
`All restore verification checks passed`, with exit code `0`. A missing backup,
restore failure, or verification-query mismatch produces exit code `1` after
the remaining databases are checked.

The script normally removes its per-run files and `restore-test-*` containers
on both success and failure. If the process is interrupted, inspect any
leftovers before rerunning:

```bash
docker ps -a --filter name=restore-test-
```

See `scripts.md` for the full configuration, verification, and cleanup
contract.
