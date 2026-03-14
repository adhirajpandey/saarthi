# API

## General

### Auth

Protected endpoints require:

- Header: `Authorization: Bearer <ADMIN_TOKEN>`

If token is missing or invalid, response is:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "..."
  }
}
```

### Common Response Behavior

- Success responses use endpoint-specific models.
- Application failures use:

```json
{
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

### Runtime Flow (Shared)

```text
Client Request
    |
    v
FastAPI Router
    |
    +--> (If protected) Admin token validation
    |
    v
Service Layer
    |
    +--> AppError? ----yes----> JSON error response
    |                          {"error": {"code", "message"}}
    |
    no
    v
JSON success response
```

## Endpoints

### `GET /health`

Short description:
Returns service liveness status, current IST timestamp, Dell home connectivity via Tailscale,
and host tool availability diagnostics.

ASCII flow:

```text
Client -> /health -> health router -> get_now_ist() + tool probes + optional tailscale ping -> response
```

Expected input:

- No auth required
- No request body

Expected output:

```json
{
  "status": "ok",
  "timestamp": "2026-03-14T12:34:56+05:30",
  "dell_home_connectivity": true,
  "tailscale_available": true,
  "rclone_available": true,
  "pg_dump_available": true
}
```

Remarks:

- Timestamp is generated in IST (`Asia/Kolkata`).
- `dell_home_connectivity` is `true` only when `tailscale ping` to configured Dell IP succeeds.
- `tailscale_available` and `rclone_available` indicate whether each command is present and runnable.
- `pg_dump_available` indicates whether `pg_dump` is present on PATH (host-mounted binary check).
- If `tailscale_available` is `false`, `dell_home_connectivity` is reported as `false` without running `tailscale ping`.
- When Tailscale is unavailable/unreachable, `dell_home_connectivity` is reported as `false`.

### `POST /geofence/events`

Short description:
Accepts a geofence event payload and triggers geofence notification dispatch.

ASCII flow:

```text
Client
  -> /geofence/events
  -> auth check
  -> send_geofence_notification(area, event)
  -> success/failure response
```

Expected input:

Headers:

- `Authorization: Bearer <ADMIN_TOKEN>`

Body:

```json
{
  "area": "Home",
  "event": "entered"
}
```

- `event` allowed values: `entered`, `exited`

Expected output:

Success (`200`):

```json
{
  "success": true,
  "message": "..."
}
```

Failure (`500`):

```json
{
  "error": {
    "code": "notification_failed",
    "message": "..."
  }
}
```

Remarks:

- Notification service treats dispatch as success when at least one enabled channel succeeds.

### `POST /me/location`

Short description:
Stores a location ping and schedules geofence transition evaluation in the background.

ASCII flow:

```text
Client
  -> /me/location
  -> auth check
  -> save_location_ping(SQLite)
  -> enqueue run_geofence_engine(background)
  -> immediate success response

Background task:
  run_geofence_engine
    -> fetch latest 2 location points
    -> resolve previous/current geofence
    -> detect transitions (entered/exited)
    -> send notifications per transition
```

Expected input:

Headers:

- `Authorization: Bearer <ADMIN_TOKEN>`

Body:

```json
{
  "latitude": 12.9716,
  "longitude": 77.5946
}
```

Validation constraints:

- `latitude`: `-90` to `90`
- `longitude`: `-180` to `180`

Expected output:

Success (`200`):

```json
{
  "success": true,
  "id": 123,
  "timestamp": "2026-03-14T07:04:00+00:00"
}
```

Validation failure (`422`):

- Standard FastAPI validation error payload.

Persistence failure (`500`):

```json
{
  "error": {
    "code": "location_persist_failed",
    "message": "Failed to persist location ping"
  }
}
```

Remarks:

- Endpoint response is immediate; geofence evaluation happens asynchronously.
- Geofence engine needs at least two stored location points to evaluate transitions.
