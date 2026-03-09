"""Unit tests for geofence transition engine."""

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from app.services.geofence_engine import (
    GeofenceArea,
    detect_transitions,
    load_geofence_mapping,
    resolve_geofence,
    run_geofence_engine,
)
from app.services.location import LocationRecord


def test_load_geofence_mapping_success(tmp_path: Path) -> None:
    mapping_path = tmp_path / "geofence_mapping.json"
    mapping_path.write_text(
        json.dumps(
            {
                "GEOFENCE_MAPPING": [
                    {"name": "Home", "latitude": 12.9716, "longitude": 77.5946, "radius_meters": 200}
                ]
            }
        ),
        encoding="utf-8",
    )

    mapping = load_geofence_mapping(str(mapping_path))

    assert len(mapping) == 1
    assert mapping[0].name == "Home"


def test_load_geofence_mapping_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        load_geofence_mapping(str(tmp_path / "missing.json"))


def test_resolve_geofence_prefers_nearest_in_overlap() -> None:
    mapping = [
        GeofenceArea(name="A", latitude=12.9716, longitude=77.5946, radius_meters=1_000),
        GeofenceArea(name="B", latitude=12.9722, longitude=77.5952, radius_meters=1_000),
    ]
    point = LocationRecord(
        id=1,
        latitude=12.9721,
        longitude=77.5951,
        timestamp=datetime.now(UTC),
    )

    matched = resolve_geofence(point=point, mapping=mapping)

    assert matched is not None
    assert matched.name == "B"


def test_detect_transitions_in_to_out() -> None:
    home = GeofenceArea(name="Home", latitude=12.0, longitude=77.0, radius_meters=100)

    transitions = detect_transitions(previous_area=home, current_area=None)

    assert [(item.area, item.event) for item in transitions] == [("Home", "exited")]


def test_detect_transitions_out_to_in() -> None:
    home = GeofenceArea(name="Home", latitude=12.0, longitude=77.0, radius_meters=100)

    transitions = detect_transitions(previous_area=None, current_area=home)

    assert [(item.area, item.event) for item in transitions] == [("Home", "entered")]


def test_detect_transitions_in_to_in_different() -> None:
    home = GeofenceArea(name="Home", latitude=12.0, longitude=77.0, radius_meters=100)
    office = GeofenceArea(name="Office", latitude=12.1, longitude=77.1, radius_meters=100)

    transitions = detect_transitions(previous_area=home, current_area=office)

    assert [(item.area, item.event) for item in transitions] == [
        ("Home", "exited"),
        ("Office", "entered"),
    ]


def test_run_geofence_engine_dispatches_exit_then_enter(monkeypatch) -> None:
    class _DummySettings:
        pass

    mapping = [
        GeofenceArea(name="Home", latitude=12.9716, longitude=77.5946, radius_meters=150),
        GeofenceArea(name="Office", latitude=12.9352, longitude=77.6245, radius_meters=150),
    ]
    latest = [
        LocationRecord(id=2, latitude=12.9352, longitude=77.6245, timestamp=datetime.now(UTC)),
        LocationRecord(id=1, latitude=12.9716, longitude=77.5946, timestamp=datetime.now(UTC)),
    ]
    calls: list[tuple[str, str]] = []

    async def _fake_get_latest_location_records(*_, **__):
        return latest

    async def _fake_send_geofence_notification(*_, **kwargs):
        calls.append((kwargs["area"], kwargs["event"]))
        return type("R", (), {"success": True, "message": "ok"})()

    monkeypatch.setattr(
        "app.services.geofence_engine.get_latest_location_records",
        _fake_get_latest_location_records,
    )
    monkeypatch.setattr(
        "app.services.geofence_engine.send_geofence_notification",
        _fake_send_geofence_notification,
    )

    asyncio.run(run_geofence_engine(settings=_DummySettings(), db_path="unused.db", mapping=mapping))

    assert calls == [("Home", "exited"), ("Office", "entered")]
