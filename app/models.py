from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BaseConfig(BaseModel):
    app_name: str = Field(default="saarthi")
    debug: bool = Field(default=False)


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime


class RateLimitingConfig(BaseModel):
    default_limit: str = Field(default="50/minute")


class GeofenceConfig(BaseModel):
    email_template: str
    subject_template: str
    recipient: Optional[str] = None
    sender_name: Optional[str] = None


class SharedConfig(BaseModel):
    base: BaseConfig
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    admin_token: str
    geofence: GeofenceConfig
