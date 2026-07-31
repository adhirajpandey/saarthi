"""Tests for the SQLite-backed Shikari ride archive."""

from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from app.services.shikari.importer import import_session
from app.services.shikari.storage import (
    backup_database,
    initialize_database,
    list_rides,
    load_ride,
    verify_database,
)


def _write_session(
    base_dir: Path,
    name: str,
    *,
    end_time: float = 1.0,
    include_metadata: bool = True,
) -> Path:
    session_dir = base_dir / name
    session_dir.mkdir(parents=True)
    (session_dir / "Accelerometer.csv").write_text(
        '"Time (s)","Acceleration x (m/s^2)","Acceleration y (m/s^2)","Acceleration z (m/s^2)"\n'
        "0.0,1,2,3\n"
        "0.0,4,5,6\n"
        f"{end_time},7,8,9\n",
        encoding="utf-8",
    )
    (session_dir / "Location.csv").write_text(
        '"Time (s)","Latitude (°)","Longitude (°)","Height (m)","Velocity (m/s)","Direction (°)","Horizontal Accuracy (m)","Vertical Accuracy (m)"\n'
        "0.0,28.4,77.0,NaN,NaN,NaN,300,20\n"
        f"{end_time},28.5,77.1,250,10,90,4,6\n",
        encoding="utf-8",
    )
    meta_dir = session_dir / "meta"
    meta_dir.mkdir()
    if include_metadata:
        (meta_dir / "device.csv").write_text(
            '"property","value"\n'
            '"version","1.2.0"\n'
            '"deviceModel","Pixel 6a"\n'
            '"accelerometer Resolution","0.1"\n',
            encoding="utf-8",
        )
        (meta_dir / "time.csv").write_text(
            '"event","experiment time","system time","system time text"\n'
            '"START",0.0,1770000000.0,"2026-02-02 20:10:00.000 UTC+05:30"\n'
            f'"PAUSE",{end_time},{1770000000.0 + end_time},"2026-02-02 20:10:01.000 UTC+05:30"\n',
            encoding="utf-8",
        )
    else:
        (meta_dir / "device.csv").write_text('"property","value"\n', encoding="utf-8")
    return session_dir


def test_import_preserves_duplicate_times_nulls_and_metadata(test_workspace: Path) -> None:
    session_dir = _write_session(test_workspace / "sessions", "2026-02-02-20:10:00")
    db_path = test_workspace / "rides.sqlite3"

    result = import_session(db_path, session_dir)
    ride_data, meta = load_ride(db_path, session_dir.name)

    assert result.status == "imported"
    assert result.sample_count == 5
    assert ride_data["Accelerometer"]["time_s"].tolist() == [0.0, 0.0, 1.0]
    assert pd.isna(ride_data["Location"].iloc[0]["height_m"])
    assert pd.isna(ride_data["Location"].iloc[0]["velocity_mps"])
    assert meta["device"]["deviceModel"] == "Pixel 6a"
    assert meta["sensors"]["accelerometer"]["Resolution"] == "0.1"
    assert [event["event"] for event in meta["events"]] == ["START", "PAUSE"]


def test_reimport_is_idempotent_and_records_an_alias(test_workspace: Path) -> None:
    sessions_dir = test_workspace / "sessions"
    first = _write_session(sessions_dir, "2026-02-02-20:10:00")
    alias = sessions_dir / "2026-02-02-20:20:00"
    alias.mkdir()
    for source_file in first.rglob("*.csv"):
        target = alias / source_file.relative_to(first)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source_file.read_bytes())
    db_path = test_workspace / "rides.sqlite3"

    first_result = import_session(db_path, first)
    repeat_result = import_session(db_path, first)
    alias_result = import_session(db_path, alias)

    assert first_result.status == "imported"
    assert repeat_result.status == "skipped"
    assert alias_result.status == "aliased"
    assert len(list_rides(db_path)) == 1
    assert load_ride(db_path, alias.name)[1]["session_name"] == first.name
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT count(*) FROM ride_imports").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM motion_samples").fetchone()[0] == 3


def test_longer_export_extends_an_existing_logical_ride(test_workspace: Path) -> None:
    sessions_dir = test_workspace / "sessions"
    shorter = _write_session(sessions_dir, "short", end_time=1.0)
    longer = _write_session(sessions_dir, "long", end_time=2.0)
    db_path = test_workspace / "rides.sqlite3"

    import_session(db_path, shorter)
    result = import_session(db_path, longer)
    ride_data, meta = load_ride(db_path, "long")

    assert result.status == "extended"
    assert len(list_rides(db_path)) == 1
    assert ride_data["Accelerometer"]["time_s"].tolist() == [0.0, 0.0, 1.0, 2.0]
    assert meta["duration_s"] == 2.0


def test_inferred_time_session_with_non_timestamp_name_imports(test_workspace: Path) -> None:
    session_dir = _write_session(
        test_workspace / "sessions",
        "2026-02-02-20:10:00--export",
        include_metadata=False,
    )
    db_path = test_workspace / "rides.sqlite3"

    import_session(db_path, session_dir)
    _, meta = load_ride(db_path, session_dir.name)

    assert meta["time_inferred"] is True
    assert meta["events"] == []
    assert meta["duration_s"] == 1.0


def test_import_loads_pressure_and_orientation_shapes(test_workspace: Path) -> None:
    session_dir = _write_session(test_workspace / "sessions", "2026-02-02-20:10:00")
    (session_dir / "Pressure.csv").write_text(
        '"Time (s)","Pressure (hPa)"\n0.0,980.5\n1.0,981.0\n',
        encoding="utf-8",
    )
    (session_dir / "Orientation.csv").write_text(
        '"Time (s)","w","x","y","z","Direct (°)","Yaw (°)","Pitch (°)","Roll (°)"\n'
        "0.0,1,0,0,0,90,10,20,30\n"
        "1.0,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN\n",
        encoding="utf-8",
    )
    db_path = test_workspace / "rides.sqlite3"

    import_session(db_path, session_dir)
    ride_data, _ = load_ride(db_path, session_dir.name)

    assert ride_data["Pressure"]["pressure_hpa"].tolist() == [980.5, 981.0]
    assert ride_data["Orientation"].iloc[0]["yaw_deg"] == 10.0
    assert pd.isna(ride_data["Orientation"].iloc[1]["w"])


def test_import_stores_missing_device_metadata_as_json_null(test_workspace: Path) -> None:
    session_dir = _write_session(test_workspace / "sessions", "2026-02-02-20:10:00")
    (session_dir / "meta" / "device.csv").write_text(
        '"property","value"\n'
        '"deviceModel","Pixel 6a"\n'
        '"deviceBaseOS",NaN\n'
        '"humidity Name",NaN\n',
        encoding="utf-8",
    )
    db_path = test_workspace / "rides.sqlite3"

    import_session(db_path, session_dir)
    _, meta = load_ride(db_path, session_dir.name)

    assert meta["device"]["deviceBaseOS"] is None
    assert meta["sensors"]["humidity"]["Name"] is None


def test_verify_and_backup_create_a_restorable_database(test_workspace: Path) -> None:
    source_dir = _write_session(test_workspace / "sessions", "2026-02-02-20:10:00")
    db_path = test_workspace / "rides.sqlite3"
    backup_path = test_workspace / "backups" / "rides.sqlite3"
    import_session(db_path, source_dir)

    report = verify_database(db_path)
    backup_report = backup_database(db_path, backup_path)

    assert report.ok is True
    assert report.ride_count == 1
    assert report.sample_count == 5
    assert backup_report.ok is True
    assert verify_database(backup_path).sample_count == 5


def test_schema_initialization_is_idempotent_and_strict(test_workspace: Path) -> None:
    db_path = test_workspace / "rides.sqlite3"

    initialize_database(db_path)
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO rides (
                    ride_key, canonical_label, duration_ns, time_inferred,
                    metadata_json, created_at_utc_us, updated_at_utc_us
                ) VALUES ('key', 'label', 'not-an-integer', 0, '{}', 1, 1)
                """
            )
