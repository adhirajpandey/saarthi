"""API contract tests for health endpoint."""


def test_health_endpoint_returns_status_and_timestamp(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
