"""Geofence notification service."""

from dataclasses import dataclass
import logging

from fastapi.concurrency import run_in_threadpool

from shared.notifications.email import send_email
from shared.notifications.whatsapp import send_whatsapp_message
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
    """Send geofence notifications and return structured outcome."""
    channel_results: dict[str, bool] = {}

    if settings.email_enabled:
        try:
            subject = settings.geofence_subject_template.format(area=area)
            email_body = settings.geofence_email_template.format(area=area, event=event)
        except (KeyError, ValueError) as exc:
            logger.error("Invalid geofence email template configuration: %s", exc)
            channel_results["email"] = False
        else:
            try:
                smtp_settings = settings.smtp_settings()
                sent = await run_in_threadpool(
                    send_email,
                    recipient=settings.geofence_updates_recipient,
                    subject=subject,
                    body=email_body,
                    smtp_settings=smtp_settings,
                    sender_name=settings.geofence_sender_name,
                )
                channel_results["email"] = sent
            except Exception as exc:
                logger.exception("Unexpected error while sending geofence email: %s", exc)
                channel_results["email"] = False

    if settings.whatsapp_enabled:
        try:
            whatsapp_body = settings.geofence_whatsapp_template.format(area=area, event=event)
        except (KeyError, ValueError) as exc:
            logger.error("Invalid geofence WhatsApp template configuration: %s", exc)
            channel_results["whatsapp"] = False
        else:
            try:
                sent = await run_in_threadpool(
                    send_whatsapp_message,
                    message=whatsapp_body,
                    whatsapp_settings=settings.whatsapp_settings_for_geofence(),
                )
                channel_results["whatsapp"] = sent
            except Exception as exc:
                logger.exception("Unexpected error while sending geofence WhatsApp: %s", exc)
                channel_results["whatsapp"] = False

    if not channel_results:
        return NotificationResult(
            success=False,
            message="No geofence notification channels enabled",
        )

    if any(channel_results.values()):
        return NotificationResult(
            success=True,
            message=(
                f"Geofence notification sent for {area} "
                f"(email={channel_results.get('email')}, whatsapp={channel_results.get('whatsapp')})"
            ),
        )

    return NotificationResult(
        success=False,
        message=(
            "Failed to send geofence notifications "
            f"(email={channel_results.get('email')}, whatsapp={channel_results.get('whatsapp')})"
        ),
    )
