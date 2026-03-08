"""OpenAPI contract tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_geofence_uses_http_bearer_security() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    security_schemes = schema["components"]["securitySchemes"]
    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["type"] == "http"
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"
