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
- To enable personal WhatsApp notifications, set `WHATSAPP_ENABLED=True`,
  configure `WHATSAPP_TARGET_PERSONAL`, and set `WHATSAPP_SOCKET_PATH` to
  `/srv/appdata/wacli/store/.send.sock`. Keep `WHATSAPP_TIMEOUT_SECONDS=60`.
  Enabled settings require a timeout greater than five seconds.
- Use canonical recipient JIDs, such as `15550001111@s.whatsapp.net` for a
  personal number or an exact group JID ending in `@g.us`. Remove the legacy
  `whatsapp:` prefix.
- To enable family geofence alerts, set `GEOFENCE_WHATSAPP_ENABLED=True` and
  set `WHATSAPP_TARGET_FAMILY` to the intended group's canonical JID.
  Keep `WHATSAPP_ENABLED=True`.
- To keep family WhatsApp disabled, set `GEOFENCE_WHATSAPP_ENABLED=False` and
  leave `WHATSAPP_TARGET_FAMILY=None`. Personal notifications remain enabled.
  Family dispatch requires both WhatsApp flags, a family recipient, and the
  `GEOFENCE_WHATSAPP_ENTERED_TEMPLATE` and
  `GEOFENCE_WHATSAPP_EXITED_TEMPLATE` settings. Keep email enabled when the
  family WhatsApp channel is disabled.
- `.env`: authentication, secrets, and connection values (`ADMIN_TOKEN`,
  `MCP_PUBLIC_BASE_URL`, `MCP_GITHUB_CLIENT_ID`,
  `MCP_GITHUB_CLIENT_SECRET`, `MCP_GITHUB_ALLOWED_USER_ID`,
  `MCP_OAUTH_JWT_SIGNING_KEY`, `CLOUDFLARE_API_TOKEN`,
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
  Habitat production sets `SAARTHI_DATA_PATH=/srv/appdata/saarthi`. Keep this
  mutable state outside the replaceable Saarthi source checkout.
  Set `GOOGLE_TASKS_TOKEN_PATH` to `/app/secrets/google/google-tasks-token.json`
  so the runtime setting matches the fixed container target.
- For enabled WhatsApp in repository-local Compose, set
  `SAARTHI_WACLI_STORE_PATH=/srv/appdata/wacli/store` in `.env`. API, MCP, and
  cron mount that directory read-only at `/srv/appdata/wacli/store`.
  Repository-local Compose defaults to `./data/wacli`, which can remain empty
  when WhatsApp is disabled. Shed defaults to the existing production store.
  The directory mount lets clients reconnect after wacli recreates its socket.
- Create a GitHub OAuth App for MCP access. Set its authorization callback URL
  to `${MCP_PUBLIC_BASE_URL}/auth/callback` exactly, and use its client ID and
  client secret for `MCP_GITHUB_CLIENT_ID` and `MCP_GITHUB_CLIENT_SECRET`.
  `MCP_PUBLIC_BASE_URL` must be the public HTTPS origin without `/mcp`.
- Set `MCP_GITHUB_ALLOWED_USER_ID` to the numeric GitHub user ID permitted to
  call Saarthi tools. Generate a stable secret for `MCP_OAUTH_JWT_SIGNING_KEY`.
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

`saarthi-mcp` serves its repository-local host endpoint on
`http://localhost:8001/mcp`. Production clients connect to
`${MCP_PUBLIC_BASE_URL}/mcp` and authenticate through GitHub OAuth. The server
requests the `read:user` scope and permits only `MCP_GITHUB_ALLOWED_USER_ID`.
Detailed MCP setup is documented in `mcp.md`.
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

5. Ensure the production Shikari data paths exist:

```bash
sudo mkdir -p /srv/appdata/saarthi/shikari/sessions
sudo mkdir -p /srv/appdata/saarthi/shikari/outputs
sudo chown -R "$(id -un):$(id -gn)" /srv/appdata/saarthi
```

These host directories appear inside the containers as
`/app/data/shikari/sessions` and `/app/data/shikari/outputs`. Local development
may still use the git-ignored repository `data/` directory.

6. Authorize Google Tasks for MCP reads:

```bash
uv run google-tasks-auth --headless
```

This writes authorized-user token JSON to `GOOGLE_TASKS_TOKEN_PATH`. For a
headless host, open the printed Google login URL on another machine, complete
sign-in, copy the final `http://127.0.0.1:1/...` redirect URL from the browser
address bar, and paste it back into the terminal prompt.

For repository-local Compose, set `SAARTHI_GOOGLE_TASKS_TOKEN_PATH` to the host
token file. The Habitat Shed deployment instead mounts the writable
`/srv/appdata/saarthi/credentials/google/` directory. In both cases, set
`GOOGLE_TASKS_TOKEN_PATH=/app/secrets/google/google-tasks-token.json`.

## Connect Habitat's wacli service

Use the existing paired secondary account in Shed's
`black-box/services/wacli` deployment. Follow the
[wacli runbook](https://github.com/adhirajpandey/shed/blob/main/black-box/services/wacli/README.md)
for pairing and session recovery.

Keep wacli pinned to commit `97e14efdf91a7c9de1b68845321eb6355943b5f5`.
Saarthi uses its internal version-1 socket protocol. Retain `--send-spacing 1s`
in the sync command so queued requests respect their send deadlines.

Apply wacli configuration from its deployment directory:

```bash
cd /home/adhiraj/projects/shed/black-box/services/wacli
docker compose up -d
```

Rebuild both Saarthi images when changing the sender or its dependencies:

```bash
cd /home/adhiraj/projects/shed/black-box/projects/saarthi
docker compose --profile cron build saarthi-api saarthi-cron
docker compose up -d --no-build saarthi-api saarthi-mcp
```

After changing notification flags or recipients, restart API and MCP. Cron
loads the current configuration on its next one-shot invocation.

```bash
docker compose restart saarthi-api saarthi-mcp
curl -s http://localhost:6710/health
```

Use a separately authorized personal message to verify sending. Keep family
WhatsApp disabled during verification. Check the personal chat before
repeating an unconfirmed send because a timeout can occur after acceptance.

To disable WhatsApp, set `WHATSAPP_ENABLED=False` in Shed's Saarthi
`config.py`, then restart API and MCP with the command above. The MCP send
tool disappears, and subsequent script runs skip WhatsApp notifications.
Retain email for geofence notifications.

After host loss, recover Saarthi with WhatsApp disabled until wacli is paired
and sync is running. The wacli store is outside the existing backups.

## Verify

```bash
curl -s http://localhost:8000/health
curl -s https://saarthi.adhirajpandey.tech/.well-known/oauth-authorization-server
docker compose logs saarthi-api
docker compose logs saarthi-mcp
codex mcp get saarthi
codex mcp login saarthi
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
details. The WhatsApp probe checks local socket reachability only. It does not
verify authentication, the upstream connection, or recipient delivery.

The OAuth metadata response should advertise authorization and token endpoints
under `MCP_PUBLIC_BASE_URL`. `codex mcp login saarthi` should open the GitHub
authorization flow. MCP requests succeed only when the authenticated GitHub
user matches `MCP_GITHUB_ALLOWED_USER_ID`.

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

On black-box, the git-ignored `app/config/config.py` links to
`/home/adhiraj/projects/shed/black-box/projects/saarthi/config.py`, and `.env`
links to that deployment's `.env`. Preserve these links so manual restore
checks use the same notification settings as the containers. On another host,
create local config files and supply that host's connection values.

Run as `adhiraj` on black-box to access the owner-only wacli socket directly.
`WHATSAPP_SOCKET_PATH` has the same absolute value on the host and in the
containers. Preserve the store's private permissions.

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
