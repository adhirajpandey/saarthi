"""
Application configuration.

This file contains all static configuration values for the application.
Sensitive values (API keys, secrets) are loaded from environment variables.
"""

# Base configuration
APP_NAME = "SAARTHI"

# Rate limiting configuration
RATE_LIMIT_DEFAULT = "50/minute"
RATE_LIMIT_CHAT = "10/minute"

# AI Service models (ordered by priority)
AI_MODELS = [
    {"provider": "openrouter", "name": "mistralai/mistral-7b-instruct:free", "priority": 0},
    {"provider": "ollama", "name": "qwen3:0.6b", "priority": 1},
    {"provider": "ollama", "name": "qwen3:4b", "priority": 2},
    {"provider": "openai", "name": "gpt-4.1-nano", "priority": 3},
    {"provider": "openai", "name": "gpt-4o-mini", "priority": 4},
    {"provider": "gemini", "name": "gemini-2.0-flash-lite", "priority": 5},
    {"provider": "gemini", "name": "gemini-2.0-flash", "priority": 6},
]

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE = "logs/app.log"

# Geofence configuration
GEOFENCE_SUBJECT_TEMPLATE = "Adhiraj Location Update: {area}"
GEOFENCE_EMAIL_TEMPLATE = """Hello Pandey Parivaar,

Adhiraj ki location ka update:

Area - {area}
Update - {trigger}

Regards
Pandey Bot
"""
