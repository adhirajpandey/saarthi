# Saarthi - Smart Aide for Actions, Retrieval, Tasks, Handling Information

Saarthi is a personal, ever-evolving project where I bring together tools, scripts, APIs, and experiments in one place.

## What Saarthi Is

Saarthi is a practical workspace for building and operating useful software, not a fixed product.

## Current Capabilities

- FastAPI endpoints for health checks (including host tool availability diagnostics), protected operations, and geofence/location-driven flows.
- Geofence transition handling with event-triggered notifications.
- Operational automation for database backups, Google Drive sync, and scheduler setup.
- Shikari sensor-session visualization CLI for ride dashboards.
- Shared runtime infrastructure for settings, logging, and notification clients.

## Quick Commands

```bash
uv run uvicorn app.main:app --reload
uv run shikari-visualize --list
uv run shikari-visualize 2026-03-13-22:02:58 --output html png
```

## More Docs

For technical details, see [docs/README.md](docs/README.md).
