# Scripts

## General

### Entry Points

Scripts are exposed via `pyproject.toml`:

- `backup-dbs` -> `scripts.backup_dbs.main:main`
- `backup-gdrive` -> `scripts.backup_gdrive.main:main`
- `schedule-scripts` -> `scripts.schedule_scripts.main:main`
- `shikari-visualize` -> `scripts.shikari_visualize.main:main`

Remarks:

- MCP is served by `mcp-server/server.py`; it is not a `pyproject.toml` script entry point.

### Shared Runtime Behavior

- Scripts load typed settings from `shared/settings.py`.
- Logging is initialized via `shared.logging.setup_logging(...)`.
- Exit code convention:
  - `0` = success
  - `1` = failure

### Shared Notification Pattern

Backup scripts (`backup-dbs`, `backup-gdrive`) send notifications based on toggles:

- ntfy (`NTFY_ENABLED`)
- WhatsApp (`WHATSAPP_ENABLED`)

Each script attempts notification dispatch but does not crash purely because a notification channel fails.
Backup scripts reuse the shared notification transports.

## Scripts

### `backup-dbs`

Short description:
Backs up configured PostgreSQL databases to S3 and sends status notifications.

ASCII flow:

```text
Load BackupDbSettings
  -> build db map
  -> for each DB:
       pg_dump
       sanity check (file exists + non-empty)
       upload to S3
  -> teardown local dump files
  -> dispatch ntfy/WhatsApp summary
  -> exit 0 or 1
```

Expected input:

Configuration (`app/config/config.py`):

- `BACKUP_BUCKET`
- `VIDWIZ_S3_PREFIX`
- `TRACKCROW_S3_PREFIX`
- `SMASHDIARY_S3_PREFIX`
- `VIDWIZ_DUMP_FILENAME`
- `TRACKCROW_DUMP_FILENAME`
- `SMASHDIARY_DUMP_FILENAME`
- notification toggles and shared runtime values

Secrets / connections (`.env`):

- `AWS_ACCESS_KEY`
- `AWS_SECRET_ACCESS_KEY`
- `VIDWIZ_DB_URL`
- `TRACKCROW_DB_URL`
- `SMASHDIARY_DB_URL`
- ntfy credentials when ntfy enabled

System prerequisites:

- `pg_dump` available on PATH
- network access to DB + S3

Expected output:

- Exit code `0` when all DB backups complete.
- Exit code `1` when any DB backup step fails or setup fails.
- Log output written to configured log destination.
- Local dump files are cleaned up in teardown.

Remarks:

- If one DB fails, script continues processing remaining targets, then returns failure overall.
- Top-level failures also attempt notification dispatch when settings are available.

### `backup-gdrive`

Short description:
Copies configured Google Drive folders to destination storage using `rclone`, then sends status notifications.

ASCII flow:

```text
Load BackupGdriveSettings
  -> for each configured folder:
       run rclone copy
       collect stdout/stderr/failures
  -> dispatch ntfy/WhatsApp summary
  -> exit 0 or 1
```

Expected input:

Configuration (`app/config/config.py`):

- `GDRIVE_SOURCE`
- `GDRIVE_DESTINATION`
- `GDRIVE_FOLDERS`
- notification toggles and shared runtime values

Secrets / connections (`.env`):

- ntfy credentials when ntfy enabled

System prerequisites:

- `rclone` installed and configured for referenced remotes
- network access to source/destination

Expected output:

- Exit code `0` when all folder copies succeed.
- Exit code `1` when any folder copy fails or setup fails.
- Aggregated command output captured for notifications.

Remarks:

- Script processes all folders and computes final success at the end.
- WhatsApp summary is intentionally concise compared to full ntfy/body output.

### `schedule-scripts`

Short description:
Generates systemd service/timer units from JSON config and enables timers.

ASCII flow:

```text
Load scripts/schedule_scripts/config.json
  -> validate SchedulerSettings
  -> generate *.service + *.timer files
  -> systemctl daemon-reload
  -> systemctl enable --now <name>.timer
  -> exit 0 or 1
```

Expected input:

JSON config (`scripts/schedule_scripts/config.json`):

- `systemd_path`
- `uv_bin`
- `working_dir`
- `home_dir`
- `scripts[]` with `name`, `command`, `time`, `description`

System prerequisites:

- systemd-based host
- write permission to configured `systemd_path`
- permission to run `systemctl`

Expected output:

- Generated `.service` and `.timer` files for each configured script.
- Enabled timers on success.
- Exit code `0` on full success, `1` on permission/systemctl/validation failures.

Remarks:

- Script does not use ntfy/WhatsApp notifications.
- Invalid `time` values in config are rejected by model validation.

### `shikari-visualize`

Short description:
Generates Plotly dashboards from bike sensor session directories.

ASCII flow:

```text
Load ShikariSettings
  -> resolve session data path
  -> discover candidate sessions (requires meta/device.csv + >=1 sensor csv)
  -> load + normalize sensor/meta CSVs
  -> build combined dashboard figure
  -> write html/png/pdf outputs
  -> exit 0 or 1
```

Expected input:

Configuration (`app/config/config.py`):

- `SHIKARI_SESSIONS_PATH`
- `SHIKARI_OUTPUTS_PATH`
- `SHIKARI_DEFAULT_THEME`
- `SHIKARI_DEFAULT_OUTPUT_FORMAT`

CLI options:

- `session` (optional)
- `--list`
- `--data-dir` (override sessions path)
- `--output` (`png`, `html`, `pdf`)
- `--theme` (`light`, `dark`)

Runtime prerequisites:

- Python dependencies installed via `uv sync` (includes `plotly` + `kaleido`)

Expected output:

- Exit code `0` on success.
- Exit code `1` for invalid input paths, load failures, or render/export failures.
- Generated files in `SHIKARI_OUTPUTS_PATH` (default `data/shikari/outputs`).

Remarks:

- Data merge target is `data/shikari/sessions`.
- Early/partial sessions without `meta/device.csv` are excluded from candidates.
- `--data-dir` can be used to render from any alternate sessions directory.

### Historical Migration Notes

- Sessions were consolidated into `data/shikari/sessions`.
- Legacy source used during the one-time migration: `/home/adhiraj/testing/shikari/sessions`.
- Generated artifacts are intentionally written to `data/shikari/outputs` (git-ignored via `data/`).

## Run Commands

- `uv run backup-dbs`
- `uv run backup-gdrive`
- `sudo env "PATH=$PATH" uv run schedule-scripts`
- `uv run shikari-visualize --list`
- `uv run shikari-visualize 2026-03-13-22:02:58 --output html png`
