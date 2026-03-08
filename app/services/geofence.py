"""Geofence notification service."""

from dataclasses import dataclass
import logging

from fastapi.concurrency import run_in_threadpool

from shared.notifications.email import send_email
from shared.settings import ApiSettings


@dataclass(slots=True)
class NotificationResult:
    success: bool
    message: str


logger = logging.getLogger(__name__)


async def send_geofence_notification(
    settings: ApiSettings,
    area: str,
    event: str,
) -> NotificationResult:
    """Send geofence email notification and return structured outcome."""
    try:
        subject = settings.geofence_subject_template.format(area=area)
        body = settings.geofence_email_template.format(area=area, event=event)
    except (KeyError, ValueError) as exc:
        logger.error("Invalid geofence template configuration: %s", exc)
        return NotificationResult(
            success=False,
            message="Geofence notification template configuration is invalid",
        )

    smtp_settings = settings.smtp_settings()

    try:
        sent = await run_in_threadpool(
            send_email,
            recipient=settings.geofence_updates_recipient,
            subject=subject,
            body=body,
            smtp_settings=smtp_settings,
            sender_name=settings.geofence_sender_name,
        )
    except Exception as exc:
        logger.exception("Unexpected error while sending geofence email: %s", exc)
        return NotificationResult(
            success=False,
            message="Unexpected error while sending geofence notification",
        )

    if not sent:
        return NotificationResult(success=False, message="Failed to send geofence notification email")

    return NotificationResult(success=True, message=f"Geofence notification sent for {area}")
