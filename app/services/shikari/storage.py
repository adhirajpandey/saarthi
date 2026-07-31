"""SQLite persistence and read models for Shikari ride data."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

import pandas as pd

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
)


SCHEMA_VERSION = 1
MOTION_UNITS = {
    "Accelerometer": "m/s^2",
    "Gravity": "m/s^2",
    "Gyroscope": "rad/s",
    "Linear Acceleration": "m/s^2",
}

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rides (
    id INTEGER PRIMARY KEY,
    ride_key TEXT NOT NULL UNIQUE,
    canonical_label TEXT NOT NULL,
    started_at_utc_us INTEGER,
    ended_at_utc_us INTEGER,
    duration_ns INTEGER NOT NULL,
    utc_offset_minutes INTEGER,
    time_inferred INTEGER NOT NULL CHECK (time_inferred IN (0, 1)),
    metadata_json TEXT NOT NULL CHECK (json_valid(metadata_json)),
    created_at_utc_us INTEGER NOT NULL,
    updated_at_utc_us INTEGER NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS ride_imports (
    id INTEGER PRIMARY KEY,
    ride_id INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    parser_version INTEGER NOT NULL,
    imported_at_utc_us INTEGER NOT NULL,
    sample_count INTEGER NOT NULL,
    UNIQUE (source_name, manifest_sha256)
) STRICT;

CREATE TABLE IF NOT EXISTS ride_events (
    ride_id INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    event_index INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('START', 'PAUSE')),
    elapsed_ns INTEGER NOT NULL,
    system_time_utc_us INTEGER NOT NULL,
    system_time_text TEXT NOT NULL,
    PRIMARY KEY (ride_id, event_index)
) WITHOUT ROWID, STRICT;

CREATE TABLE IF NOT EXISTS motion_samples (
    ride_id INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    sensor_kind TEXT NOT NULL CHECK (
        sensor_kind IN ('Accelerometer', 'Gravity', 'Gyroscope', 'Linear Acceleration')
    ),
    elapsed_ns INTEGER NOT NULL,
    source_row INTEGER NOT NULL,
    x REAL,
    y REAL,
    z REAL,
    PRIMARY KEY (ride_id, sensor_kind, elapsed_ns, source_row)
) WITHOUT ROWID, STRICT;

CREATE TABLE IF NOT EXISTS scalar_samples (
    ride_id INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    sensor_kind TEXT NOT NULL,
    elapsed_ns INTEGER NOT NULL,
    source_row INTEGER NOT NULL,
    value REAL,
    PRIMARY KEY (ride_id, sensor_kind, elapsed_ns, source_row)
) WITHOUT ROWID, STRICT;

CREATE TABLE IF NOT EXISTS orientation_samples (
    ride_id INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    elapsed_ns INTEGER NOT NULL,
    source_row INTEGER NOT NULL,
    w REAL,
    x REAL,
    y REAL,
    z REAL,
    direction_deg REAL,
    yaw_deg REAL,
    pitch_deg REAL,
    roll_deg REAL,
    PRIMARY KEY (ride_id, elapsed_ns, source_row)
) WITHOUT ROWID, STRICT;

CREATE TABLE IF NOT EXISTS location_samples (
    ride_id INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    elapsed_ns INTEGER NOT NULL,
    source_row INTEGER NOT NULL,
    latitude_deg REAL,
    longitude_deg REAL,
    height_m REAL,
    velocity_mps REAL,
    direction_deg REAL,
    horizontal_accuracy_m REAL,
    vertical_accuracy_m REAL,
    PRIMARY KEY (ride_id, elapsed_ns, source_row)
) WITHOUT ROWID, STRICT;

CREATE INDEX IF NOT EXISTS idx_rides_started_at
ON rides (started_at_utc_us);

CREATE INDEX IF NOT EXISTS idx_ride_imports_ride
ON ride_imports (ride_id);

CREATE INDEX IF NOT EXISTS idx_ride_imports_manifest
ON ride_imports (manifest_sha256);
"""


@dataclass(slots=True, frozen=True)
class RideSummary:
    id: int
    label: str
    started_at_utc_us: int | None
    duration_s: float
    time_inferred: bool


@dataclass(slots=True, frozen=True)
class VerificationReport:
    ok: bool
    ride_count: int
    import_count: int
    sample_count: int
    integrity_result: str
    foreign_key_errors: tuple[tuple, ...]


def connect_database(db_path: str | Path) -> sqlite3.Connection:
    """Open a configured connection to an existing or initialized ride database."""
    connection = sqlite3.connect(Path(db_path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def database_connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open a transactional connection and always close it after use."""
    connection = connect_database(db_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(db_path: str | Path) -> None:
    """Create schema version 1 without changing an existing compatible database."""
    resolved_path = Path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    with database_connection(resolved_path) as connection:
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current_version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Ride database schema {current_version} is newer than supported {SCHEMA_VERSION}"
            )
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.executescript(_SCHEMA_SQL)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _require_database(db_path: str | Path) -> Path:
    resolved_path = Path(db_path)
    if not resolved_path.is_file():
        raise ValueError(f"Ride database not found: {resolved_path}")
    return resolved_path


def list_rides(db_path: str | Path) -> list[RideSummary]:
    """Return logical rides in chronological order, with unknown starts last."""
    resolved_path = _require_database(db_path)
    with database_connection(resolved_path) as connection:
        rows = connection.execute(
            """
            SELECT id, canonical_label, started_at_utc_us, duration_ns, time_inferred
            FROM rides
            ORDER BY started_at_utc_us IS NULL, started_at_utc_us, canonical_label
            """
        ).fetchall()
    return [
        RideSummary(
            id=int(row["id"]),
            label=str(row["canonical_label"]),
            started_at_utc_us=row["started_at_utc_us"],
            duration_s=int(row["duration_ns"]) / 1_000_000_000,
            time_inferred=bool(row["time_inferred"]),
        )
        for row in rows
    ]


def _resolve_ride(connection: sqlite3.Connection, ride_ref: str | int) -> sqlite3.Row:
    if isinstance(ride_ref, int) or str(ride_ref).isdigit():
        row = connection.execute(
            "SELECT * FROM rides WHERE id = ?", (int(ride_ref),)
        ).fetchone()
    else:
        row = connection.execute(
            "SELECT * FROM rides WHERE canonical_label = ?", (str(ride_ref),)
        ).fetchone()
        if row is None:
            row = connection.execute(
                """
                SELECT rides.*
                FROM ride_imports
                JOIN rides ON rides.id = ride_imports.ride_id
                WHERE ride_imports.source_name = ?
                ORDER BY ride_imports.id DESC
                LIMIT 1
                """,
                (str(ride_ref),),
            ).fetchone()
    if row is None:
        raise ValueError(f"Ride not found: {ride_ref}")
    return row


def _frame(rows: list[sqlite3.Row], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame.from_records(
        [tuple(row[column] for column in columns) for row in rows],
        columns=columns,
    )


def load_ride(
    db_path: str | Path,
    ride_ref: str | int,
) -> tuple[dict[str, pd.DataFrame], dict]:
    """Load one database ride in the same normalized shape used by existing plots."""
    resolved_path = _require_database(db_path)
    with database_connection(resolved_path) as connection:
        ride = _resolve_ride(connection, ride_ref)
        ride_id = int(ride["id"])
        metadata = json.loads(str(ride["metadata_json"]))
        data: dict[str, pd.DataFrame] = {}

        motion_kinds = connection.execute(
            """
            SELECT DISTINCT sensor_kind
            FROM motion_samples
            WHERE ride_id = ?
            ORDER BY sensor_kind
            """,
            (ride_id,),
        ).fetchall()
        for kind_row in motion_kinds:
            kind = str(kind_row["sensor_kind"])
            rows = connection.execute(
                """
                SELECT elapsed_ns / 1000000000.0 AS time_s, x, y, z
                FROM motion_samples
                WHERE ride_id = ? AND sensor_kind = ?
                ORDER BY elapsed_ns, source_row
                """,
                (ride_id, kind),
            ).fetchall()
            frame = _frame(rows, [TIME_COL, X_COL, Y_COL, Z_COL])
            frame.attrs["xyz_unit"] = MOTION_UNITS[kind]
            data[kind] = frame

        scalar_kinds = connection.execute(
            """
            SELECT DISTINCT sensor_kind
            FROM scalar_samples
            WHERE ride_id = ?
            ORDER BY sensor_kind
            """,
            (ride_id,),
        ).fetchall()
        for kind_row in scalar_kinds:
            kind = str(kind_row["sensor_kind"])
            rows = connection.execute(
                """
                SELECT elapsed_ns / 1000000000.0 AS time_s, value
                FROM scalar_samples
                WHERE ride_id = ? AND sensor_kind = ?
                ORDER BY elapsed_ns, source_row
                """,
                (ride_id, kind),
            ).fetchall()
            value_column = PRESSURE_COL if kind == "Pressure" else "value"
            frame = _frame(rows, [TIME_COL, "value"])
            data[kind] = frame.rename(columns={"value": value_column})

        orientation_rows = connection.execute(
            """
            SELECT elapsed_ns / 1000000000.0 AS time_s,
                   w, x, y, z, direction_deg, yaw_deg, pitch_deg, roll_deg
            FROM orientation_samples
            WHERE ride_id = ?
            ORDER BY elapsed_ns, source_row
            """,
            (ride_id,),
        ).fetchall()
        if orientation_rows:
            data["Orientation"] = _frame(
                orientation_rows,
                [
                    TIME_COL,
                    "w",
                    X_COL,
                    Y_COL,
                    Z_COL,
                    "direction_deg",
                    "yaw_deg",
                    "pitch_deg",
                    "roll_deg",
                ],
            )

        location_rows = connection.execute(
            """
            SELECT elapsed_ns / 1000000000.0 AS time_s,
                   latitude_deg, longitude_deg, height_m, velocity_mps,
                   direction_deg, horizontal_accuracy_m, vertical_accuracy_m
            FROM location_samples
            WHERE ride_id = ?
            ORDER BY elapsed_ns, source_row
            """,
            (ride_id,),
        ).fetchall()
        if location_rows:
            data["Location"] = _frame(
                location_rows,
                [
                    TIME_COL,
                    LAT_COL,
                    LON_COL,
                    HEIGHT_COL,
                    VELOCITY_COL,
                    DIRECTION_COL,
                    H_ACC_COL,
                    V_ACC_COL,
                ],
            )

        event_rows = connection.execute(
            """
            SELECT event_type, elapsed_ns, system_time_utc_us, system_time_text
            FROM ride_events
            WHERE ride_id = ?
            ORDER BY event_index
            """,
            (ride_id,),
        ).fetchall()

    events = [
        {
            "event": str(row["event_type"]),
            "experiment_time": int(row["elapsed_ns"]) / 1_000_000_000,
            "system_time": int(row["system_time_utc_us"]) / 1_000_000,
            "system_time_text": str(row["system_time_text"]),
        }
        for row in event_rows
    ]
    meta = {
        "device": metadata.get("device", {}),
        "sensors": metadata.get("sensors", {}),
        "events": events,
        "duration_s": int(ride["duration_ns"]) / 1_000_000_000,
        "session_name": str(ride["canonical_label"]),
        "time_inferred": bool(ride["time_inferred"]),
    }
    return data, meta


def verify_database(db_path: str | Path) -> VerificationReport:
    """Run integrity checks and return core archive counts."""
    resolved_path = _require_database(db_path)
    with database_connection(resolved_path) as connection:
        integrity_result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_key_errors = tuple(
            tuple(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        ride_count = int(connection.execute("SELECT count(*) FROM rides").fetchone()[0])
        import_count = int(
            connection.execute("SELECT count(*) FROM ride_imports").fetchone()[0]
        )
        sample_count = sum(
            int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in (
                "motion_samples",
                "scalar_samples",
                "orientation_samples",
                "location_samples",
            )
        )
    return VerificationReport(
        ok=integrity_result == "ok" and not foreign_key_errors,
        ride_count=ride_count,
        import_count=import_count,
        sample_count=sample_count,
        integrity_result=integrity_result,
        foreign_key_errors=foreign_key_errors,
    )


def backup_database(db_path: str | Path, destination: str | Path) -> VerificationReport:
    """Create a consistent SQLite backup and verify the resulting snapshot."""
    source_path = _require_database(db_path).resolve()
    destination_path = Path(destination).resolve()
    if source_path == destination_path:
        raise ValueError("Backup destination must differ from the source database")
    if destination_path.exists():
        raise FileExistsError(f"Backup destination already exists: {destination_path}")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with database_connection(source_path) as source, database_connection(destination_path) as target:
        source.backup(target)
    return verify_database(destination_path)
