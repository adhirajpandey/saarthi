"""Repository-managed runtime configuration.

Keep secrets and connection URLs in `.env`.
Keep non-sensitive operational config in this file.
"""

APP_CONFIG = {
    "APP_NAME": "SAARTHI",
    "LOCATION_DB_PATH": "data/saarthi.db",
    "GEOFENCE_MAPPING_PATH": "data/geofence_mapping.json",
}

LOGGING_CONFIG = {
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
    "LOG_FILE": "logs/app.log",
}

NOTIFICATION_FLAGS = {
    "EMAIL_ENABLED": True,
    "NTFY_ENABLED": True,
    "WHATSAPP_ENABLED": False,
}

WHATSAPP_CONFIG = {
    "WHATSAPP_SSH_HOST": None,
    "WHATSAPP_REMOTE_SCRIPT_PATH": None,
    "WHATSAPP_TARGET_FAMILY": None,
    "WHATSAPP_TARGET_PERSONAL": None,
    "WHATSAPP_TIMEOUT_SECONDS": 20,
}

GEOFENCE_CONFIG = {
    "GEOFENCE_SUBJECT_TEMPLATE": "Saarthi geofence: {area}",
    "GEOFENCE_EMAIL_TEMPLATE": "Geofence update: {area} {event}",
    "GEOFENCE_WHATSAPP_TEMPLATE": "Area {area}: {event}",
    "GEOFENCE_UPDATES_RECIPIENT": "alerts@example.com",
    "GEOFENCE_SENDER_NAME": "Saarthi",
}

NTFY_CONFIG = {
    "NTFY_TOPIC": "saarthi-backups",
}

BACKUP_DB_CONFIG = {
    "BACKUP_BUCKET": "backups",
    "VIDWIZ_S3_PREFIX": "db/vidwiz",
    "TRACKCROW_S3_PREFIX": "db/trackcrow",
    "VIDWIZ_DUMP_FILENAME": "vidwiz_backup",
    "TRACKCROW_DUMP_FILENAME": "trackcrow_backup",
}

GDRIVE_CONFIG = {
    "GDRIVE_SOURCE": "personal-drive",
    "GDRIVE_DESTINATION": "dwaar-s3:dwaar/backups/gdrive",
    "GDRIVE_FOLDERS": ["home", "workspace"],
}

CONFIG = {
    **APP_CONFIG,
    **LOGGING_CONFIG,
    **NOTIFICATION_FLAGS,
    **WHATSAPP_CONFIG,
    **GEOFENCE_CONFIG,
    **NTFY_CONFIG,
    **BACKUP_DB_CONFIG,
    **GDRIVE_CONFIG,
}
