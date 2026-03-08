# Saarthi - Smart Aide for Actions, Retrieval, Tasks, Handling Information

Saarthi is a personal, ever-evolving project where I bring together tools, scripts, APIs, and experiments in one place. Right now, it includes a web application and a set of utility scripts, and it keeps growing as I build things to solve real problems, automate repetitive work, and explore new ideas.

## What Saarthi Is

Saarthi is a practical workspace for building and operating useful software, not a fixed product.

## What It Includes Today

- A FastAPI web application for service health and monitoring workflows, protected admin access, and geofence-driven notifications.
- Utility scripts for operational automation, including database backups, Google Drive sync, and scheduler support.
- Shared infrastructure for typed settings, logging, and notification delivery so both app and scripts stay consistent.

## How It's Evolving

As new use cases come up, Saarthi expands with new components and experiments while maintaining a clean separation between web behavior and operational automation.

## Current Functional Snapshot

At the moment, Saarthi helps with:

- Observability through simple health and monitoring endpoints.
- Event-triggered communication through geofence notification flows via `POST /geofence/events`.
- Operational continuity through repeatable backup and sync automation.
- Maintainable growth by keeping APIs, shared infrastructure, and scripts organized by responsibility.

## API Notes

- `GET /health`: basic health response with IST timestamp.
- `POST /geofence/events`: admin protected endpoint to send geofence notifications.
- Protected routes use `Authorization: Bearer <ADMIN_TOKEN>`.
