"""OpenAPI contract tests."""


def test_geofence_uses_http_bearer_security(client) -> None:
    schema = client.get("/openapi.json").json()

    security_schemes = schema["components"]["securitySchemes"]
    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["type"] == "http"
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"

    me_location_post = schema["paths"]["/me/location"]["post"]
    assert {"HTTPBearer": []} in me_location_post["security"]


def test_health_schema_is_liveness_only(client) -> None:
    schema = client.get("/openapi.json").json()

    health_schema = schema["components"]["schemas"]["HealthCheckResponse"]

    assert health_schema["required"] == ["status"]
    assert health_schema["properties"] == {
        "status": {"type": "string", "title": "Status"}
    }
