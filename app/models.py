from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BaseConfig(BaseModel):
    app_name: str = Field(default="saarthi")
    debug: bool = Field(default=False)


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime


class ChatMessage(BaseModel):
    message: str


class AIChatResponse(BaseModel):
    response: str
    processed_by: str


class ProviderConfig(BaseModel):
    base_url: str
    api_key: str


class ProvidersConfig(BaseModel):
    ollama: Optional[ProviderConfig] = None
    gemini: Optional[ProviderConfig] = None
    openrouter: Optional[ProviderConfig] = None


class ModelConfig(BaseModel):
    provider: str
    name: str
    priority: int = Field(default=-1, le=10)


class RateLimitingConfig(BaseModel):
    default_limit: str = Field(default="50/minute")
    chat_limit: str = Field(default="10/minute")


class AIServiceConfig(BaseModel):
    models: list[ModelConfig]
    providers: ProvidersConfig
    openai_api_key: Optional[str] = None
    google_drive_search_webhook_url: Optional[str] = None


class GeofenceConfig(BaseModel):
    email_template: str
    subject_template: str
    recipient: str
    sender_name: str


class SharedConfig(BaseModel):
    base: BaseConfig
    rate_limiting: RateLimitingConfig = RateLimitingConfig()
    ai_service: AIServiceConfig
    admin_token: str
    geofence: GeofenceConfig
