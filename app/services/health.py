"""Runtime checks and response caching for the health endpoint."""

import asyncio
from collections.abc import Awaitable, Callable
import logging
from pathlib import Path
import socket
import sqlite3
from time import monotonic
from typing import Literal

from app.api.schemas import HealthCheckResponse, HealthChecks
from app.services.geofence_engine import GeofenceArea
from shared.settings import ApiSettings
from shared.notifications.whatsapp import whatsapp_available

logger = logging.getLogger(__name__)
_PROBE_TIMEOUT_SECONDS = 3


class HealthResponseCache:
    """Cache one health response and coalesce concurrent refreshes."""

    def __init__(
        self,
        ttl_seconds: int,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._response: HealthCheckResponse | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get(
        self,
        loader: Callable[[], Awaitable[HealthCheckResponse]],
    ) -> HealthCheckResponse:
        """Return the cached response, refreshing it once after expiry."""
        if self._response is not None and self._clock() < self._expires_at:
            return self._response

        async with self._lock:
            if self._response is not None and self._clock() < self._expires_at:
                return self._response

            self._response = await loader()
            self._expires_at = self._clock() + self._ttl_seconds
            return self._response


def _check_location_database(db_path: str) -> bool:
    try:
        uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except (OSError, sqlite3.Error, ValueError):
        logger.exception("Location database health check failed")
        return False


def _check_tcp_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=_PROBE_TIMEOUT_SECONDS):
            return True
    except (OSError, TimeoutError):
        logger.exception("Integration TCP health check failed")
        return False


def _safe_probe(name: str, probe: Callable[[], bool]) -> bool:
    try:
        return probe()
    except Exception:
        logger.exception("Unexpected %s health check failure", name)
        return False


def _channel_state(
    enabled: bool,
    reachable: bool,
) -> Literal["available", "unavailable", "disabled"]:
    if not enabled:
        return "disabled"
    return "available" if reachable else "unavailable"


def collect_health_state(
    settings: ApiSettings,
    geofence_mapping: list[GeofenceArea],
) -> HealthCheckResponse:
    """Collect coarse runtime availability without exposing configuration."""
    location_database = _channel_state(
        True,
        _safe_probe(
            "location database",
            lambda: _check_location_database(settings.location_db_path),
        ),
    )
    geofence = _channel_state(True, bool(geofence_mapping))

    email_reachable = False
    if settings.email_enabled:
        def check_email() -> bool:
            smtp_settings = settings.smtp_settings()
            return _check_tcp_reachable(smtp_settings.host, smtp_settings.port)

        email_reachable = _safe_probe("email", check_email)
    email = _channel_state(settings.email_enabled, email_reachable)

    whatsapp_reachable = False
    if settings.whatsapp_enabled:
        def check_whatsapp() -> bool:
            return whatsapp_available(settings.whatsapp_socket_path, _PROBE_TIMEOUT_SECONDS)

        whatsapp_reachable = _safe_probe("WhatsApp", check_whatsapp)
    whatsapp = _channel_state(settings.whatsapp_enabled, whatsapp_reachable)

    checks = HealthChecks(
        location_database=location_database,
        geofence_mapping=geofence,
        email=email,
        whatsapp=whatsapp,
    )
    status = "degraded" if "unavailable" in checks.model_dump().values() else "healthy"
    return HealthCheckResponse(status=status, checks=checks)
