"""API request and response schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime


class GeofenceEvent(StrEnum):
    ENTERED = "entered"
    EXITED = "exited"


class GeofenceEventRequest(BaseModel):
    area: str
    event: GeofenceEvent


class GeofenceEventResponse(BaseModel):
    success: bool
    message: str


class MeLocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class MeLocationResponse(BaseModel):
    success: bool
    id: int
    timestamp: datetime
