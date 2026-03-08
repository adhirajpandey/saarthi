"""Ntfy push notification sender."""

import logging

import requests

from shared.settings import NtfySettings

logger = logging.getLogger(__name__)


def send_ntfy_message(
    message: str,
    ntfy_settings: NtfySettings,
    topic: str | None = None,
    title: str | None = None,
    priority: int | None = None,
) -> bool:
    """Send a message to an ntfy topic."""
    resolved_topic = topic or ntfy_settings.topic
    url = f"{ntfy_settings.base_url.rstrip('/')}/{resolved_topic}"
    headers = {
        "Authorization": f"Bearer {ntfy_settings.token}",
        "Content-Type": "text/plain",
    }

    if title:
        headers["Title"] = title
    if priority:
        headers["Priority"] = str(priority)

    try:
        response = requests.post(url, headers=headers, data=message, timeout=30)
        response.raise_for_status()
        logger.info(f"Ntfy message sent successfully to topic {resolved_topic}")
        return True
    except requests.RequestException as exc:
        logger.error(f"Failed to send ntfy message: {exc}")
        return False
