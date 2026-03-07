"""Application-level email notification service."""

from app.models import GeofenceConfig
from shared.logging import logger
from shared.notifications.email import send_email


def send_geofence_notification(geofence_config: GeofenceConfig, area: str, trigger: str) -> bool:
    """Send a geofence location update notification email."""
    if not geofence_config.recipient:
        logger.error("GEOFENCE_UPDATES_RECIPIENT not configured")
        return False

    body = geofence_config.email_template.format(area=area, trigger=trigger)
    subject = geofence_config.subject_template.format(area=area)

    return send_email(
        recipient=geofence_config.recipient,
        subject=subject,
        body=body,
        sender_name=geofence_config.sender_name,
    )
