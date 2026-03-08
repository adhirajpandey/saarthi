"""API request and response schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


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
