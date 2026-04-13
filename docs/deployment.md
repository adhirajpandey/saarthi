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
- `.env`: secrets (`ADMIN_TOKEN`, `MCP_TOKEN`, SMTP/ntfy/AWS/DB URLs as needed)

3. Start API and MCP:

```bash
docker compose up --build -d
```

`saarthi-api` mounts `tailscale`, `rclone`, and `pg_dump` binaries from host, and
mounts the Tailscale runtime socket path so `/health` can evaluate
`dell_home_connectivity`.
For `pg_dump_available`, `/health` checks host-mounted PATH presence of `pg_dump`.

`saarthi-mcp` serves the MCP endpoint on `http://localhost:8001/mcp` and requires
`Authorization: Bearer <MCP_TOKEN>`. Codex should be configured with the `saarthi`
MCP server pointing at that URL and using `MCP_TOKEN` as the bearer token env var.

Expected Codex MCP config:

```toml
[mcp_servers.saarthi]
url = "http://127.0.0.1:8001/mcp"
bearer_token_env_var = "MCP_TOKEN"
```

The Saarthi MCP container and the Codex process must see the same `MCP_TOKEN` value.

4. Configure backup timers:

```bash
sudo env "PATH=$PATH" uv run schedule-scripts
```

5. Ensure Shikari data paths exist:

```bash
mkdir -p data/shikari/sessions data/shikari/outputs
```

## Verify

```bash
curl -s http://localhost:8000/health
docker compose logs -f saarthi-api
docker compose logs -f saarthi-mcp
codex mcp get saarthi
systemctl status saarthi-backup-dbs.timer
systemctl status saarthi-backup-gdrive.timer
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

# Manual Shikari output generation
uv run shikari-visualize --list
uv run shikari-visualize 2026-03-13-22:02:58 --output html
```
