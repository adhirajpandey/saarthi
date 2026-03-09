"""Geofence transition engine driven by stored location points."""

from dataclasses import dataclass
import json
import logging
import math
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.services.geofence import send_geofence_notification
from app.services.location import LocationRecord, get_latest_location_records
from shared.settings import ApiSettings

logger = logging.getLogger(__name__)


class GeofenceArea(BaseModel):
    """Single geofence area definition."""

    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_meters: float = Field(gt=0)


class GeofenceMappingConfig(BaseModel):
    """Geofence mapping payload loaded from disk."""

    geofence_mapping: list[GeofenceArea] = Field(alias="GEOFENCE_MAPPING")


@dataclass(slots=True)
class GeofenceTransition:
    area: str
    event: str


def load_geofence_mapping(mapping_path: str) -> list[GeofenceArea]:
    """Load and validate geofence mapping from JSON file."""
    path = Path(mapping_path)
    if not path.exists():
        raise ValueError(f"Geofence mapping file not found at {mapping_path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid geofence mapping JSON at {mapping_path}: {exc}") from exc

    try:
        config = GeofenceMappingConfig.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid geofence mapping payload at {mapping_path}: {exc}") from exc

    if not config.geofence_mapping:
        raise ValueError("GEOFENCE_MAPPING must contain at least one geofence")

    logger.info("Loaded %s geofence areas from %s", len(config.geofence_mapping), mapping_path)
    return config.geofence_mapping


def _haversine_meters(
    source_latitude: float,
    source_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    earth_radius_meters = 6_371_000
    source_lat_rad = math.radians(source_latitude)
    source_lon_rad = math.radians(source_longitude)
    target_lat_rad = math.radians(target_latitude)
    target_lon_rad = math.radians(target_longitude)

    lat_delta = target_lat_rad - source_lat_rad
    lon_delta = target_lon_rad - source_lon_rad
    value = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(source_lat_rad) * math.cos(target_lat_rad) * math.sin(lon_delta / 2) ** 2
    )
    return 2 * earth_radius_meters * math.asin(math.sqrt(value))


def resolve_geofence(point: LocationRecord, mapping: list[GeofenceArea]) -> GeofenceArea | None:
    """Resolve geofence for a point using nearest-center winner across inside matches."""
    inside_areas: list[tuple[GeofenceArea, float]] = []
    for area in mapping:
        distance = _haversine_meters(
            source_latitude=point.latitude,
            source_longitude=point.longitude,
            target_latitude=area.latitude,
            target_longitude=area.longitude,
        )
        if distance <= area.radius_meters:
            inside_areas.append((area, distance))

    if not inside_areas:
        return None

    inside_areas.sort(key=lambda item: item[1])
    return inside_areas[0][0]


def detect_transitions(
    previous_area: GeofenceArea | None,
    current_area: GeofenceArea | None,
) -> list[GeofenceTransition]:
    """Build ordered geofence transitions between two location points."""
    if previous_area is None and current_area is None:
        return []
    if previous_area is not None and current_area is not None and previous_area.name == current_area.name:
        return []
    if previous_area is None and current_area is not None:
        return [GeofenceTransition(area=current_area.name, event="entered")]
    if previous_area is not None and current_area is None:
        return [GeofenceTransition(area=previous_area.name, event="exited")]
    assert previous_area is not None
    assert current_area is not None
    return [
        GeofenceTransition(area=previous_area.name, event="exited"),
        GeofenceTransition(area=current_area.name, event="entered"),
    ]


async def run_geofence_engine(
    settings: ApiSettings,
    db_path: str,
    mapping: list[GeofenceArea],
) -> None:
    """Evaluate latest location transition and dispatch geofence notifications."""
    logger.info("Geofence engine triggered (db_path=%s)", db_path)
    latest = await get_latest_location_records(db_path=db_path, limit=2)
    if len(latest) < 2:
        logger.info("Geofence engine skipped: only %s location point(s) available", len(latest))
        return

    current_point = latest[0]
    previous_point = latest[1]
    logger.info(
        "Geofence engine evaluating points previous(id=%s, lat=%s, lon=%s) -> current(id=%s, lat=%s, lon=%s)",
        previous_point.id,
        previous_point.latitude,
        previous_point.longitude,
        current_point.id,
        current_point.latitude,
        current_point.longitude,
    )

    previous_area = resolve_geofence(point=previous_point, mapping=mapping)
    current_area = resolve_geofence(point=current_point, mapping=mapping)
    logger.info(
        "Geofence resolution previous_area=%s current_area=%s",
        previous_area.name if previous_area else "outside",
        current_area.name if current_area else "outside",
    )

    transitions = detect_transitions(previous_area=previous_area, current_area=current_area)
    if not transitions:
        logger.info("No geofence transitions detected for latest movement")
        return

    logger.info("Detected %s geofence transition(s)", len(transitions))
    for transition in transitions:
        logger.info(
            "Dispatching geofence notification area=%s event=%s",
            transition.area,
            transition.event,
        )
        try:
            result = await send_geofence_notification(
                settings=settings,
                area=transition.area,
                event=transition.event,
            )
            if not result.success:
                logger.warning(
                    "Geofence notification dispatch failed for area=%s event=%s: %s",
                    transition.area,
                    transition.event,
                    result.message,
                )
            else:
                logger.info(
                    "Geofence notification dispatched successfully for area=%s event=%s",
                    transition.area,
                    transition.event,
                )
        except Exception:
            logger.exception(
                "Unexpected error while dispatching geofence transition area=%s event=%s",
                transition.area,
                transition.event,
            )
