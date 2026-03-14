# Deployment

## Target

Raspberry Pi Linux host with:

- API in Docker Compose (`saarthi-app`)
- Backups scheduled via host systemd timers (`schedule-scripts`)

## Quick Setup

1. Create config files:

```bash
cp app/config/config.example.py app/config/config.py
cp .env.example .env
```

2. Fill values:

- `app/config/config.py`: non-secret settings
- `.env`: secrets (`ADMIN_TOKEN`, SMTP/ntfy/AWS/DB URLs as needed)

3. Start API:

```bash
docker compose up --build -d
```

`docker-compose.yml` also mounts Tailscale runtime into the container so `/health` can evaluate `dell_home_connectivity`.

4. Configure backup timers:

```bash
sudo env "PATH=$PATH" uv run schedule-scripts
```

## Verify

```bash
curl -s http://localhost:8000/health
docker compose logs -f saarthi-app
systemctl status saarthi-backup-dbs.timer
systemctl status saarthi-backup-gdrive.timer
```

## Common Ops

```bash
# Redeploy after update
git pull
docker compose up --build -d

# Restart service
docker compose restart saarthi-app

# Manual backup runs
uv run backup-dbs
uv run backup-gdrive
```
