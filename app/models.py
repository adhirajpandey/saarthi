from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")
    format: str = Field(
        default="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    date_format: str = Field(default="%Y-%m-%d %H:%M:%S")
    log_file: str = Field(default="logs/app.log")


class JWTConfig(BaseModel):
    secret_key: str
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)


class BaseConfig(BaseModel):
    app_name: str = Field(default="saarthi")
    debug: bool = Field(default=False)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime


class ChatMessage(BaseModel):
    message: str


class AIChatResponse(BaseModel):
    response: str
    processed_by: str


class ExternalClientConfig(BaseModel):
    base_url: str
    api_key: str


class ModelConfig(BaseModel):
    provider: str
    name: str
    external_client: Optional[ExternalClientConfig] = None
    priority: int = Field(default=-1, le=10)


class UserConfig(BaseModel):
    username: str = Field(default="admin")
    password: str = Field(default="password@123")


class RateLimitingConfig(BaseModel):
    default_limit: str = Field(default="50/minute")
    login_limit: str = Field(default="5/minute")
    chat_limit: str = Field(default="10/minute")


class AIServiceConfig(BaseModel):
    models: list[ModelConfig]
    external_client: Optional[ExternalClientConfig] = None
    openai_api_key: Optional[str] = None
    google_drive_search_webhook_url: Optional[str] = None


class SharedConfig(BaseModel):
    base: BaseConfig
    jwt: JWTConfig
    logging: LoggingConfig
    rate_limiting: RateLimitingConfig = RateLimitingConfig()
    users: list[UserConfig] = [UserConfig()]
    ai_service: AIServiceConfig
