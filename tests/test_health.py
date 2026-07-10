"""API contract tests for health endpoint."""

from app.api.schemas import HealthCheckResponse, HealthChecks


def test_health_endpoint_returns_cached_runtime_state(client, monkeypatch) -> None:
    calls = 0

    def _collect_health_state(*_args, **_kwargs) -> HealthCheckResponse:
        nonlocal calls
        calls += 1
        return HealthCheckResponse(
            status="healthy",
            checks=HealthChecks(
                location_database="available",
                geofence_mapping="available",
                email="disabled",
                whatsapp="available",
            ),
        )

    monkeypatch.setattr("app.api.routers.health.collect_health_state", _collect_health_state)

    first_response = client.get("/health")
    second_response = client.get("/health")

    assert first_response.status_code == 200
    assert first_response.json() == {
        "status": "healthy",
        "checks": {
            "location_database": "available",
            "geofence_mapping": "available",
            "email": "disabled",
            "whatsapp": "available",
        },
    }
    assert second_response.json() == first_response.json()
    assert calls == 1
