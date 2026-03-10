# Saarthi - Smart Aide for Actions, Retrieval, Tasks, Handling Information

Saarthi is a personal, ever-evolving project where I bring together tools, scripts, APIs, and experiments in one place. Right now, it includes a web application and a set of utility scripts, and it keeps growing as I build things to solve real problems, automate repetitive work, and explore new ideas.

## What Saarthi Is

Saarthi is a practical workspace for building and operating useful software, not a fixed product.

## What It Includes Today

- A FastAPI web app for service health, monitoring flows, protected admin access, and geofence/location-driven notifications.
- Utility scripts for operational work like database backups, Google Drive sync, and scheduler support.
- Shared building blocks for settings, logging, and notification delivery so app + scripts stay consistent.

## How It’s Evolving

As new use cases come up, Saarthi expands with new components and experiments while keeping a clean separation between web behavior and operational automation.

## Current Functional Snapshot

At the moment, Saarthi helps with:

- Observability through simple health and monitoring endpoints.
- Event-triggered communication through geofence flows.
- Operational continuity through repeatable backup and sync automation.
- Maintainable growth by keeping APIs, shared infrastructure, and scripts organized by responsibility.

## Runtime Config Pattern (2026-03-10)

- Keep **secrets** in `.env` (tokens, passwords, DB URLs, auth keys).
- Keep **non-secret runtime values** in local `config.py` (gitignored).
- Start from `config.example.py` and create your own `config.py`.
- These flows are intentionally separate:
  - non-secrets are read from `config.py` only,
  - secrets are read from env only.
- Saarthi fails fast on startup if required values are missing from either source.

## API Notes (2026-03-10)

- `GET /health`: basic health response with IST timestamp.
- `POST /geofence/events`: admin-protected endpoint to send geofence notifications.
- `POST /me/location`: admin-protected endpoint to store location pings and trigger geofence checks.
- Protected routes use `Authorization: Bearer <ADMIN_TOKEN>`.
