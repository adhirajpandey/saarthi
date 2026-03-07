# Saarthi - Smart Aide for Actions, Retrieval, Tasks, Handling Information

Saarthi is a personal project that combines a FastAPI web application with utility automation scripts.

---
## Project Structure

```text
app/
  api/routers/         # API endpoints (Health, Geofence)
  config/              # Defaults + settings builder
  dependencies/        # FastAPI dependencies (auth, config)
  services/            # App business logic (Email)
  main.py              # FastAPI entrypoint
shared/
  config/              # Env loading helpers
  logging/             # Central logging setup
  notifications/       # Email + ntfy providers
scripts/
  backup_dbs/          # Database backups
  backup_gdrive/       # Google Drive sync
  schedule_scripts/    # Systemd timer generator
```

### Current Architecture
- `app/api/routers/`: FastAPI route handlers.
- `app/dependencies/`: FastAPI dependencies such as admin token auth.
- `app/config/config.py`: static defaults.
- `app/config/settings.py`: config assembly from defaults + env vars.
- `app/models.py`: App/domain Pydantic models.
- `shared/`: shared infra for env loading, logging, and notifications.
- `scripts/*`: script entrypoints and script-specific orchestration.

### Configuration Flow
- `.env` is loaded via `shared.config.env.load_environment()`.
- Defaults are defined in `app/config/config.py`.
- Runtime app configuration is built in `app/config/settings.py`.
- FastAPI initializes logging and config at startup lifecycle.

---

## Part 1: Web Application

### 1. Description
The FastAPI app provides health monitoring, geofence updates, and admin-token authentication.

### 2. Setup Steps

**Step 1: Configure Environment Variables**
```bash
cp .env.example .env
```

**Step 2: Install Dependencies**
```bash
uv sync
```

**Step 3: Run the Application**
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Part 2: Utility Scripts

### 1. Database Backup (`scripts/backup_dbs/`)
- Usage: `uv run backup-dbs`
- Requires: `AWS_ACCESS_KEY`, `AWS_SECRET_ACCESS_KEY`, `VIDWIZ_DB_URL`, `TRACKCROW_DB_URL`, `NTFY_*`

### 2. Google Drive Backup (`scripts/backup_gdrive/`)
- Usage: `uv run backup-gdrive`
- Requires configured `rclone` remotes + `NTFY_*`

### 3. Schedule Scripts (`scripts/schedule_scripts/`)
- Usage: `sudo "$(command -v uv)" run schedule-scripts`
- Config file: `scripts/schedule_scripts/config.json`
