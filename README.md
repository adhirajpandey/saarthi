# Saarthi

Saarthi is a FastAPI-based backend + automation toolkit for location/geofence workflows, notifications, and operational backup jobs.

## Current Scope
- FastAPI service with typed settings and structured error responses.
- Admin-protected geofence + location ingestion endpoints.
- Notification pipeline for geofence events (email / ntfy / WhatsApp bridge, based on config).
- Utility scripts for DB backup, Google Drive sync, and scheduler orchestration.

## Project Structure
- `app/` — API routes, dependencies, services, schemas.
- `shared/` — settings, logging, notification utilities.
- `scripts/` — operational CLI jobs.
- `tests/` — pytest test suite.

## Prerequisites
- Python `>=3.12`
- [`uv`](https://docs.astral.sh/uv/) for dependency and task execution
- Optional: Docker + Docker Compose

## Local Setup (uv)
1. Clone the repo.
2. Create env file:
   - `cp .env.example .env`
3. Fill required values in `.env` (at minimum `ADMIN_TOKEN` and app/runtime paths).
4. Install dependencies:
   - `uv sync --dev`
5. Run the API:
   - `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Docker Setup
- Build + run:
  - `docker compose up --build`
- The app is exposed on port `8000`.

## Running Tests
- Full suite:
  - `uv run pytest`
- Focused runs:
  - `uv run pytest tests/test_geofence.py -q`
  - `uv run pytest tests/test_me_location.py -q`

## Script Commands
- Database backup:
  - `uv run backup-dbs`
- Google Drive sync backup:
  - `uv run backup-gdrive`
- Scheduler helper:
  - `uv run schedule-scripts`

## API Endpoints (Current)
- `GET /` — welcome/root message.
- `GET /health` — service health + IST timestamp.
- `POST /geofence/events` — submit geofence transition event (admin token required).
- `POST /me/location` — persist location ping + trigger geofence engine in background (admin token required).

Auth for protected endpoints:
- Header: `Authorization: Bearer <ADMIN_TOKEN>`

## Configuration Notes
- Environment variables are defined in `.env.example`.
- Keep `.env.example` updated whenever adding/changing required settings.
- Never commit secrets.

## Development Conventions
- Keep routers lightweight; put business logic in services.
- Use structured `AppError` responses for expected failure paths.
- Add/update tests with behavior changes.
- Follow Conventional Commits (`feat(...)`, `fix(...)`, `docs(...)`, etc.).
