"""Idempotent CSV-to-SQLite importer for Shikari sessions."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import time
from typing import Iterable

import pandas as pd

from app.services.shikari.constants import EVENT_START, XYZ_SENSORS
from app.services.shikari.loader import (
    DIRECTION_COL,
    H_ACC_COL,
    HEIGHT_COL,
    LAT_COL,
    LON_COL,
    PRESSURE_COL,
    TIME_COL,
    VELOCITY_COL,
    V_ACC_COL,
    X_COL,
    Y_COL,
    Z_COL,
    load_meta,
    load_session,
)
from app.services.shikari.storage import connect_database, initialize_database


PARSER_VERSION = 1
_UTC_OFFSET_RE = re.compile(r"UTC([+-])(\d{2}):(\d{2})")


@dataclass(slots=True, frozen=True)
class ImportResult:
    ride_id: int
    label: str
    status: str
    sample_count: int
    manifest_sha256: str


def _manifest_sha256(session_dir: Path) -> str:
    digest = hashlib.sha256()
    csv_files = sorted(session_dir.glob("*.csv")) + sorted((session_dir / "meta").glob("*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in session: {session_dir}")
    for csv_file in csv_files:
        relative_path = csv_file.relative_to(session_dir).as_posix().encode()
        digest.update(len(relative_path).to_bytes(4, "big"))
        digest.update(relative_path)
        with csv_file.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _elapsed_ns(value: object) -> int:
    return int(round(float(value) * 1_000_000_000))


def _system_time_us(value: object) -> int:
    return int(round(float(value) * 1_000_000))


def _nullable_number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _utc_offset_minutes(events: list[dict]) -> int | None:
    if not events:
        return None
    match = _UTC_OFFSET_RE.search(str(events[0].get("system_time_text", "")))
    if match is None:
        return None
    sign = 1 if match.group(1) == "+" else -1
    return sign * (int(match.group(2)) * 60 + int(match.group(3)))


def _trusted_start(events: list[dict], *, time_inferred: bool) -> dict | None:
    if time_inferred:
        return None
    return next((event for event in events if event.get("event") == EVENT_START), None)


def _ride_key(meta: dict, manifest_sha256: str) -> str:
    start = _trusted_start(meta.get("events", []), time_inferred=bool(meta["time_inferred"]))
    if start is None:
        return f"manifest:{manifest_sha256}"
    device_json = json.dumps(meta.get("device", {}), sort_keys=True, separators=(",", ":"))
    device_fingerprint = hashlib.sha256(device_json.encode()).hexdigest()[:20]
    return f"start:{_system_time_us(start['system_time'])}:{device_fingerprint}"


def _ride_times(meta: dict) -> tuple[int | None, int | None]:
    events = list(meta.get("events", []))
    starts = [event for event in events if event.get("event") == EVENT_START]
    started_at = _system_time_us(starts[0]["system_time"]) if starts else None
    if not starts:
        return None, None
    duration_s = float(meta["duration_s"])
    last_start = max(starts, key=lambda event: float(event["experiment_time"]))
    ended_at = _system_time_us(
        float(last_start["system_time"])
        + duration_s
        - float(last_start["experiment_time"])
    )
    final_events = [
        event
        for event in events
        if math.isclose(float(event["experiment_time"]), duration_s, abs_tol=1e-6)
    ]
    if final_events:
        ended_at = _system_time_us(final_events[-1]["system_time"])
    return started_at, ended_at


def _metadata_json(meta: dict) -> str:
    return json.dumps(
        {
            "device": meta.get("device", {}),
            "sensors": meta.get("sensors", {}),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _sample_rows(session_data: dict[str, pd.DataFrame]) -> dict[str, list[tuple]]:
    rows: dict[str, list[tuple]] = {
        "motion_samples": [],
        "scalar_samples": [],
        "orientation_samples": [],
        "location_samples": [],
    }
    for sensor_kind in XYZ_SENSORS:
        frame = session_data.get(sensor_kind)
        if frame is None:
            continue
        for source_row, row in enumerate(frame.itertuples(index=False)):
            row_values = row._asdict()
            rows["motion_samples"].append(
                (
                    sensor_kind,
                    _elapsed_ns(row_values[TIME_COL]),
                    source_row,
                    _nullable_number(row_values[X_COL]),
                    _nullable_number(row_values[Y_COL]),
                    _nullable_number(row_values[Z_COL]),
                )
            )

    pressure = session_data.get("Pressure")
    if pressure is not None:
        for source_row, row in enumerate(pressure.itertuples(index=False)):
            row_values = row._asdict()
            rows["scalar_samples"].append(
                (
                    "Pressure",
                    _elapsed_ns(row_values[TIME_COL]),
                    source_row,
                    _nullable_number(row_values[PRESSURE_COL]),
                )
            )

    orientation = session_data.get("Orientation")
    if orientation is not None:
        canonical_columns = {
            "Time (s)": TIME_COL,
            "Direct (°)": "direction_deg",
            "Yaw (°)": "yaw_deg",
            "Pitch (°)": "pitch_deg",
            "Roll (°)": "roll_deg",
        }
        orientation = orientation.rename(columns=canonical_columns)
        for source_row, row in enumerate(orientation.itertuples(index=False)):
            row_values = row._asdict()
            rows["orientation_samples"].append(
                (
                    _elapsed_ns(row_values[TIME_COL]),
                    source_row,
                    *(
                        _nullable_number(row_values[column])
                        for column in (
                            "w",
                            X_COL,
                            Y_COL,
                            Z_COL,
                            "direction_deg",
                            "yaw_deg",
                            "pitch_deg",
                            "roll_deg",
                        )
                    ),
                )
            )

    location = session_data.get("Location")
    if location is not None:
        for source_row, row in enumerate(location.itertuples(index=False)):
            row_values = row._asdict()
            rows["location_samples"].append(
                (
                    _elapsed_ns(row_values[TIME_COL]),
                    source_row,
                    *(
                        _nullable_number(row_values[column])
                        for column in (
                            LAT_COL,
                            LON_COL,
                            HEIGHT_COL,
                            VELOCITY_COL,
                            DIRECTION_COL,
                            H_ACC_COL,
                            V_ACC_COL,
                        )
                    ),
                )
            )
    return rows


def _merge_rows(
    connection: sqlite3.Connection,
    *,
    table: str,
    ride_id: int,
    rows: Iterable[tuple],
) -> int:
    specs = {
        "motion_samples": (
            ("sensor_kind", "elapsed_ns", "source_row"),
            ("x", "y", "z"),
        ),
        "scalar_samples": (
            ("sensor_kind", "elapsed_ns", "source_row"),
            ("value",),
        ),
        "orientation_samples": (
            ("elapsed_ns", "source_row"),
            ("w", "x", "y", "z", "direction_deg", "yaw_deg", "pitch_deg", "roll_deg"),
        ),
        "location_samples": (
            ("elapsed_ns", "source_row"),
            (
                "latitude_deg",
                "longitude_deg",
                "height_m",
                "velocity_mps",
                "direction_deg",
                "horizontal_accuracy_m",
                "vertical_accuracy_m",
            ),
        ),
    }
    key_columns, value_columns = specs[table]
    incoming_rows = list(rows)
    if not incoming_rows:
        return 0
    select_columns = ", ".join((*key_columns, *value_columns))
    existing_rows = connection.execute(
        f"SELECT {select_columns} FROM {table} WHERE ride_id = ?",
        (ride_id,),
    ).fetchall()
    key_size = len(key_columns)
    existing = {
        tuple(row[column] for column in key_columns): tuple(
            row[column] for column in value_columns
        )
        for row in existing_rows
    }
    to_insert: list[tuple] = []
    for incoming in incoming_rows:
        key = tuple(incoming[:key_size])
        values = tuple(incoming[key_size:])
        previous = existing.get(key)
        if previous is not None:
            if previous != values:
                raise ValueError(f"Conflicting {table} sample for ride {ride_id}: {key}")
            continue
        to_insert.append((ride_id, *incoming))
    columns = ("ride_id", *key_columns, *value_columns)
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        to_insert,
    )
    return len(to_insert)


def import_session(db_path: str | Path, session_dir: str | Path) -> ImportResult:
    """Import one session atomically, extending an existing logical ride when safe."""
    source_dir = Path(session_dir)
    if not source_dir.is_dir():
        raise ValueError(f"Session directory not found: {source_dir}")
    manifest_sha256 = _manifest_sha256(source_dir)
    initialize_database(db_path)
    now_us = time.time_ns() // 1_000

    with connect_database(db_path) as connection:
        previous_source = connection.execute(
            """
            SELECT ride_id, sample_count
            FROM ride_imports
            WHERE source_name = ? AND manifest_sha256 = ?
            """,
            (source_dir.name, manifest_sha256),
        ).fetchone()
        if previous_source is not None:
            return ImportResult(
                ride_id=int(previous_source["ride_id"]),
                label=source_dir.name,
                status="skipped",
                sample_count=int(previous_source["sample_count"]),
                manifest_sha256=manifest_sha256,
            )

        previous_manifest = connection.execute(
            """
            SELECT ride_id, sample_count
            FROM ride_imports
            WHERE manifest_sha256 = ?
            ORDER BY id
            LIMIT 1
            """,
            (manifest_sha256,),
        ).fetchone()
        if previous_manifest is not None:
            with connection:
                connection.execute(
                    """
                    INSERT INTO ride_imports (
                        ride_id, source_name, manifest_sha256, parser_version,
                        imported_at_utc_us, sample_count
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(previous_manifest["ride_id"]),
                        source_dir.name,
                        manifest_sha256,
                        PARSER_VERSION,
                        now_us,
                        int(previous_manifest["sample_count"]),
                    ),
                )
            return ImportResult(
                ride_id=int(previous_manifest["ride_id"]),
                label=source_dir.name,
                status="aliased",
                sample_count=int(previous_manifest["sample_count"]),
                manifest_sha256=manifest_sha256,
            )

    session_data = load_session(source_dir)
    meta = load_meta(source_dir, session_data=session_data)
    rows_by_table = _sample_rows(session_data)
    sample_count = sum(len(rows) for rows in rows_by_table.values())
    ride_key = _ride_key(meta, manifest_sha256)
    duration_ns = _elapsed_ns(meta["duration_s"])
    started_at, ended_at = _ride_times(meta)

    with connect_database(db_path) as connection, connection:
        ride = connection.execute(
            "SELECT * FROM rides WHERE ride_key = ?", (ride_key,)
        ).fetchone()
        is_new = ride is None
        if ride is None:
            cursor = connection.execute(
                """
                INSERT INTO rides (
                    ride_key, canonical_label, started_at_utc_us, ended_at_utc_us,
                    duration_ns, utc_offset_minutes, time_inferred, metadata_json,
                    created_at_utc_us, updated_at_utc_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ride_key,
                    source_dir.name,
                    started_at,
                    ended_at,
                    duration_ns,
                    _utc_offset_minutes(meta.get("events", [])),
                    int(bool(meta["time_inferred"])),
                    _metadata_json(meta),
                    now_us,
                    now_us,
                ),
            )
            ride_id = int(cursor.lastrowid)
            previous_duration_ns = -1
        else:
            ride_id = int(ride["id"])
            previous_duration_ns = int(ride["duration_ns"])

        inserted_count = sum(
            _merge_rows(
                connection,
                table=table,
                ride_id=ride_id,
                rows=rows,
            )
            for table, rows in rows_by_table.items()
        )

        if is_new or duration_ns >= previous_duration_ns:
            connection.execute("DELETE FROM ride_events WHERE ride_id = ?", (ride_id,))
            connection.executemany(
                """
                INSERT INTO ride_events (
                    ride_id, event_index, event_type, elapsed_ns,
                    system_time_utc_us, system_time_text
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        ride_id,
                        event_index,
                        str(event["event"]),
                        _elapsed_ns(event["experiment_time"]),
                        _system_time_us(event["system_time"]),
                        str(event.get("system_time_text", "")),
                    )
                    for event_index, event in enumerate(meta.get("events", []))
                ],
            )
            connection.execute(
                """
                UPDATE rides
                SET started_at_utc_us = COALESCE(started_at_utc_us, ?),
                    ended_at_utc_us = ?, duration_ns = ?,
                    utc_offset_minutes = COALESCE(utc_offset_minutes, ?),
                    time_inferred = ?, metadata_json = ?, updated_at_utc_us = ?
                WHERE id = ?
                """,
                (
                    started_at,
                    ended_at,
                    duration_ns,
                    _utc_offset_minutes(meta.get("events", [])),
                    int(bool(meta["time_inferred"])),
                    _metadata_json(meta),
                    now_us,
                    ride_id,
                ),
            )

        connection.execute(
            """
            INSERT INTO ride_imports (
                ride_id, source_name, manifest_sha256, parser_version,
                imported_at_utc_us, sample_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ride_id,
                source_dir.name,
                manifest_sha256,
                PARSER_VERSION,
                now_us,
                sample_count,
            ),
        )

    return ImportResult(
        ride_id=ride_id,
        label=source_dir.name,
        status="imported" if is_new else "extended",
        sample_count=sample_count if is_new else inserted_count,
        manifest_sha256=manifest_sha256,
    )
