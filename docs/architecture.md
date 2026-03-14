# Architecture

## General

Saarthi has two execution surfaces:

- FastAPI runtime for HTTP-triggered workflows
- CLI script runtime for operational automation

Both surfaces reuse shared modules for settings, logging, and notification transports.

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
                               |          |
                +--------------+          +------------------+
                |                                         |
      +---------v----------+                    +---------v----------------+
      | FastAPI Runtime    |                    | Operational Script CLIs   |
      | app/main.py        |                    | backup-dbs / backup-gdrive|
      | routers + services |                    | / schedule-scripts        |
      +---------+----------+                    +---------+----------------+
                |                                         |
      +---------v----------+                    +---------v----------------+
      | SQLite + Geofence  |                    | pg_dump / rclone /       |
      | transition engine  |                    | systemd + cloud uploads  |
      +--------------------+                    +--------------------------+

                          +------------------------------+
                          | shared/logging +             |
                          | shared/notifications/*       |
                          +------------------------------+
```

## Components

- `app/`: API runtime and business services
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
- `scripts/schedule_scripts/config.json`: scheduler input

## Remarks

- API and scripts are intentionally separate entrypoints.
- Shared modules keep behavior consistent across both runtimes.
