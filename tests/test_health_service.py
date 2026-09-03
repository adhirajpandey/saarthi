"""Tests for runtime health checks and response caching."""

import asyncio

from app.api.schemas import HealthCheckResponse, HealthChecks
from app.services.health import HealthResponseCache, collect_health_state


def _response(status: str = "healthy") -> HealthCheckResponse:
    return HealthCheckResponse(
        status=status,
        checks=HealthChecks(
            location_database="available",
            geofence_mapping="available",
            email="disabled",
            whatsapp="disabled",
        ),
    )


def test_collect_health_state_marks_failed_enabled_channel_as_degraded(
    client,
    monkeypatch,
) -> None:
    settings = client.app.state.settings
    settings.email_enabled = True
    settings.whatsapp_enabled = True
    settings.whatsapp_socket_path = "/tmp/wacli-test.sock"
    monkeypatch.setattr("app.services.health.whatsapp_available", lambda *_: False)
    settings.whatsapp_target_family = "120363000000000000@g.us"
    monkeypatch.setattr("app.services.health._check_location_database", lambda *_: True)
    monkeypatch.setattr("app.services.health._check_tcp_reachable", lambda *_: False)

    response = collect_health_state(settings, client.app.state.geofence_mapping)

    assert response.status == "degraded"
    assert response.checks.location_database == "available"
    assert response.checks.geofence_mapping == "available"
    assert response.checks.email == "unavailable"
    assert response.checks.whatsapp == "unavailable"


def test_collect_health_state_ignores_disabled_channels(client, monkeypatch) -> None:
    settings = client.app.state.settings
    settings.email_enabled = False
    settings.whatsapp_enabled = False
    monkeypatch.setattr("app.services.health._check_location_database", lambda *_: True)

    response = collect_health_state(settings, client.app.state.geofence_mapping)

    assert response.status == "healthy"
    assert response.checks.email == "disabled"
    assert response.checks.whatsapp == "disabled"


def test_health_uses_socket_without_requiring_family_recipient(client, monkeypatch):
    settings = client.app.state.settings
    settings.email_enabled = False
    settings.whatsapp_enabled = True
    settings.geofence_whatsapp_enabled = False
    settings.whatsapp_target_family = None
    settings.whatsapp_socket_path = "/tmp/wacli-test.sock"
    probes = []
    monkeypatch.setattr("app.services.health._check_location_database", lambda *_: True)
    monkeypatch.setattr("app.services.health.whatsapp_available", lambda *args: probes.append(args) or True)
    response = collect_health_state(settings, client.app.state.geofence_mapping)
    assert response.checks.whatsapp == "available"
    assert probes == [("/tmp/wacli-test.sock", 3)]


def test_collect_health_state_contains_unexpected_probe_error(client, monkeypatch) -> None:
    settings = client.app.state.settings
    settings.email_enabled = False
    settings.whatsapp_enabled = False

    def _raise_unexpected_error(*_args) -> bool:
        raise RuntimeError("private failure details")

    monkeypatch.setattr(
        "app.services.health._check_location_database",
        _raise_unexpected_error,
    )

    response = collect_health_state(settings, client.app.state.geofence_mapping)

    assert response.status == "degraded"
    assert response.checks.location_database == "unavailable"
    assert "private failure details" not in response.model_dump_json()


def test_health_response_cache_refreshes_after_ttl() -> None:
    now = 100.0
    calls = 0
    cache = HealthResponseCache(ttl_seconds=60, clock=lambda: now)

    async def loader() -> HealthCheckResponse:
        nonlocal calls
        calls += 1
        return _response("healthy" if calls == 1 else "degraded")

    async def exercise_cache():
        nonlocal now
        first = await cache.get(loader)
        now = 159.0
        cached = await cache.get(loader)
        now = 160.0
        refreshed = await cache.get(loader)
        now = 161.0
        cached_degraded = await cache.get(loader)
        return first, cached, refreshed, cached_degraded

    first, cached, refreshed, cached_degraded = asyncio.run(exercise_cache())

    assert first.status == "healthy"
    assert cached is first
    assert refreshed.status == "degraded"
    assert cached_degraded is refreshed
    assert calls == 2


def test_health_response_cache_coalesces_concurrent_refreshes() -> None:
    calls = 0
    cache = HealthResponseCache(ttl_seconds=60)

    async def loader() -> HealthCheckResponse:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return _response()

    async def load_concurrently():
        return await asyncio.gather(*(cache.get(loader) for _ in range(5)))

    responses = asyncio.run(load_concurrently())

    assert calls == 1
    assert all(response is responses[0] for response in responses)
