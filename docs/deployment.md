# Deployment

## Target

Raspberry Pi Linux host with:

- API in Docker Compose (`saarthi-api`)
- MCP server in Docker Compose (`saarthi-mcp`)
- Backups scheduled via host systemd timers (`schedule-scripts`)
- Local Shikari visualization CLI for ride dashboards (`shikari-visualize`)

## Quick Setup

1. Create config files:

```bash
cp app/config/config.example.py app/config/config.py
cp .env.example .env
```

2. Fill values:

- `app/config/config.py`: non-secret settings
- If enabling `WHATSAPP_ENABLED`, set `WHATSAPP_HERMES_COMMAND_PATH` explicitly to
  the correct binary path on that host. The example config leaves it unset on
  purpose.
- For geofence WhatsApp notifications, set both
  `GEOFENCE_WHATSAPP_ENTERED_TEMPLATE` and
  `GEOFENCE_WHATSAPP_EXITED_TEMPLATE`. These replace the older single-template
  approach and allow natural phrasing per event.
- `.env`: secrets (`ADMIN_TOKEN`, `MCP_TOKEN`, `CLOUDFLARE_API_TOKEN`,
  `GOOGLE_TASKS_CLIENT_ID`, `GOOGLE_TASKS_CLIENT_SECRET`,
  `GOOGLE_TASKS_TOKEN_PATH`, `NOTION_API_KEY`,
  `NOTION_LINKS_DATABASE_URL`, `NOTION_WORK_ITEMS_DATABASE_URL`,
  SMTP/ntfy/AWS/DB URLs, `RESTORE_PG_PASSWORD` as needed)
- Share the Notion integration tied to `NOTION_API_KEY` with both configured
  databases.
- `NOTION_WORK_ITEMS_DATABASE_URL` should point to the combined work items
  database that uses a `Project` select with `Vidwiz`, `Trackcrow`, and
  `Habitat`.

3. Start API and MCP:

```bash
docker compose up --build -d
```

`saarthi-api` mounts `tailscale`, `rclone`, and `pg_dump` binaries from host, and
mounts the Tailscale runtime socket path so `/health` can evaluate
`dell_home_connectivity`.
For `pg_dump_available`, `/health` checks host-mounted PATH presence of `pg_dump`.

`saarthi-mcp` serves the MCP endpoint on `http://localhost:8001/mcp` and requires
`Authorization: Bearer <MCP_TOKEN>`. Detailed MCP setup is documented in `mcp.md`.

4. Configure backup timers:

```bash
sudo env "PATH=$PATH" uv run schedule-scripts
```

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

The current `docker-compose.yml` mounts `/home/adhiraj/.config/saarthi` into
`saarthi-mcp` as read-only so a host token file at
`/home/adhiraj/.config/saarthi/google-tasks-token.json` is visible inside the
MCP container.

## Verify

```bash
curl -s http://localhost:8000/health
docker compose logs saarthi-api
docker compose logs saarthi-mcp
codex mcp get saarthi
systemctl status saarthi-backup-dbs.timer
systemctl status saarthi-backup-gdrive.timer
uv run cloudflare-zones list
uv run cloudflare-dns list --zone-name adhirajpandey.tech --proxied
uv run google-tasks-auth --headless
uv run shikari-visualize --list
```

For Notion MCP verification, confirm these tool calls succeed from the client:

- `get_links_database_schema()`
- `list_saved_links(page_size=5)`
- `get_work_items_database_schema()`
- `list_work_items(project="all", page_size=5)`
- `list_work_item_projects()`

## Common Ops

```bash
# Redeploy after update
git pull
docker compose up --build -d

# Restart service
docker compose restart saarthi-api
docker compose restart saarthi-mcp

# Manual backup runs
uv run backup-dbs
uv run backup-gdrive
uv run restore-dbs-test

# Manual Cloudflare reads
uv run cloudflare-zones list
uv run cloudflare-dns list --zone-name adhirajpandey.tech --proxied

# Google Tasks auth bootstrap
uv run google-tasks-auth --headless

# Manual Shikari output generation
uv run shikari-visualize --list
uv run shikari-visualize 2026-03-13-22:02:58 --output html
```
