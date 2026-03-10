"""Tests for me location endpoint."""

import copy
import json
import sqlite3
from pathlib import Path
import runpy
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
import shared.settings as settings_module

_EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.example.py"
_BASE_CONFIG = runpy.run_path(str(_EXAMPLE_CONFIG_PATH))["CONFIG"]


def test_me_location_requires_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/me/location",
            json={"latitude": 12.9716, "longitude": 77.5946},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_location_persists_row(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "saarthi.db"
    mapping_path = tmp_path / "geofence_mapping.json"
    mapping_path.write_text(
        json.dumps(
            {
                "GEOFENCE_MAPPING": [
                    {
                        "name": "Home",
                        "latitude": 12.9716,
                        "longitude": 77.5946,
                        "radius_meters": 200,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cfg = copy.deepcopy(_BASE_CONFIG)
    cfg["LOCATION_DB_PATH"] = str(db_path)
    cfg["GEOFENCE_MAPPING_PATH"] = str(mapping_path)
    monkeypatch.setattr(settings_module, "_load_repo_config_values", lambda: copy.deepcopy(cfg))

    with TestClient(app) as client:
        response = client.post(
            "/me/location",
            json={"latitude": 12.9716, "longitude": 77.5946},
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["id"] >= 1
    assert "timestamp" in payload

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT latitude, longitude FROM me_locations WHERE id = ?",
            (payload["id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == 12.9716
    assert row[1] == 77.5946


def test_me_location_rejects_invalid_coordinates() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/me/location",
            json={"latitude": 120.0, "longitude": 77.5946},
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 422


def test_me_location_returns_500_when_insert_fails() -> None:
    with patch("app.api.routers.me.save_location_ping", side_effect=RuntimeError("db down")):
        with TestClient(app) as client:
            response = client.post(
                "/me/location",
                json={"latitude": 12.9716, "longitude": 77.5946},
                headers={"Authorization": "Bearer test-admin-token"},
            )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "location_persist_failed"


def test_me_location_enqueues_geofence_engine() -> None:
    engine_mock = AsyncMock(return_value=None)
    with patch("app.api.routers.me.run_geofence_engine", engine_mock):
        with TestClient(app) as client:
            response = client.post(
                "/me/location",
                json={"latitude": 12.9716, "longitude": 77.5946},
                headers={"Authorization": "Bearer test-admin-token"},
            )

    assert response.status_code == 200
    engine_mock.assert_awaited_once()
