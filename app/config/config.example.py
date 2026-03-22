"""Example repository-managed runtime configuration.

Copy this file to `app/config/config.py` and adjust non-sensitive operational values.
Keep secrets and URL/DB connection values in `.env`.
"""

APP_CONFIG = {
    "APP_NAME": "SAARTHI",
    "LOCATION_DB_PATH": "data/saarthi.db",
    "GEOFENCE_MAPPING_PATH": "data/geofence_mapping.json",
    "DELL_TAILSCALE_IP": "100.100.100.100",
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
    "GEOFENCE_SUBJECT_TEMPLATE": "Parivaar Location Update: {area}",
    "GEOFENCE_EMAIL_TEMPLATE": "Namaste,\n\nAdhiraj ne {area} area me {event} kiya hai.\n\nDhanyavaad,\nSaarthi",
    "GEOFENCE_WHATSAPP_TEMPLATE": "Location update: Adhiraj ne {area} area me {event} kiya hai.",
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
    "SMASHDIARY_S3_PREFIX": "db/smashdiary",
    "VIDWIZ_DUMP_FILENAME": "vidwiz_backup",
    "TRACKCROW_DUMP_FILENAME": "trackcrow_backup",
    "SMASHDIARY_DUMP_FILENAME": "smashdiary_backup",
}

GDRIVE_CONFIG = {
    "GDRIVE_SOURCE": "personal-drive",
    "GDRIVE_DESTINATION": "dwaar-s3:dwaar/backups/gdrive",
    "GDRIVE_FOLDERS": ["home", "workspace"],
}

SHIKARI_CONFIG = {
    "SHIKARI_SESSIONS_PATH": "data/shikari/sessions",
    "SHIKARI_OUTPUTS_PATH": "data/shikari/outputs",
    "SHIKARI_DEFAULT_THEME": "dark",
    "SHIKARI_DEFAULT_OUTPUT_FORMAT": "png",
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
    **SHIKARI_CONFIG,
}
