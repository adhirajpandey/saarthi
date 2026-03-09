"""Location persistence service."""

from dataclasses import dataclass
from datetime import UTC, datetime
import sqlite3
from pathlib import Path

from fastapi.concurrency import run_in_threadpool


@dataclass(slots=True)
class StoredLocation:
    id: int
    timestamp: datetime


@dataclass(slots=True)
class LocationRecord:
    id: int
    latitude: float
    longitude: float
    timestamp: datetime


_CREATE_LOCATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS me_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    recorded_at TEXT NOT NULL
)
"""

_CREATE_LOCATION_RECORDED_AT_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_me_locations_recorded_at
ON me_locations (recorded_at)
"""


def initialize_location_db(db_path: str) -> None:
    """Create location storage file and schema if not present."""
    resolved_path = Path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(resolved_path) as conn:
        conn.execute(_CREATE_LOCATION_TABLE_SQL)
        conn.execute(_CREATE_LOCATION_RECORDED_AT_INDEX_SQL)
        conn.commit()


def _insert_location(db_path: str, latitude: float, longitude: float) -> StoredLocation:
    timestamp = datetime.now(UTC)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO me_locations (latitude, longitude, recorded_at)
            VALUES (?, ?, ?)
            """,
            (latitude, longitude, timestamp.isoformat()),
        )
        conn.commit()

    row_id = cursor.lastrowid
    if row_id is None:
        raise RuntimeError("Failed to persist location")

    return StoredLocation(id=row_id, timestamp=timestamp)


def _fetch_latest_location_records(db_path: str, limit: int) -> list[LocationRecord]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, latitude, longitude, recorded_at
            FROM me_locations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        LocationRecord(
            id=row[0],
            latitude=row[1],
            longitude=row[2],
            timestamp=datetime.fromisoformat(row[3]),
        )
        for row in rows
    ]


async def save_location_ping(db_path: str, latitude: float, longitude: float) -> StoredLocation:
    """Persist a location ping in SQLite."""
    return await run_in_threadpool(_insert_location, db_path, latitude, longitude)


async def get_latest_location_records(db_path: str, limit: int) -> list[LocationRecord]:
    """Fetch latest location rows from SQLite, newest first."""
    return await run_in_threadpool(_fetch_latest_location_records, db_path, limit)
