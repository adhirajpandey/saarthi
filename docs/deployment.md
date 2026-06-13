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
- `.env`: secrets (`ADMIN_TOKEN`, `MCP_TOKEN`, `CLOUDFLARE_API_TOKEN`,
  `GOOGLE_TASKS_CLIENT_ID`, `GOOGLE_TASKS_CLIENT_SECRET`,
  `GOOGLE_TASKS_TOKEN_PATH`, SMTP/ntfy/AWS/DB URLs, `RESTORE_PG_PASSWORD` as
  needed)

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
