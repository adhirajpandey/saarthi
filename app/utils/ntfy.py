"""
Ntfy service for sending push notifications.
"""

import os
import requests
from app.utils.logging import logger


def send_ntfy_message(
    topic: str,
    message: str,
    title: str | None = None,
    priority: int | None = None,
) -> bool:
    """
    Send a message to an ntfy topic.

    Args:
        topic: Topic name
        message: Message body
        title: Optional notification title
        priority: Optional priority (1–5)

    Returns:
        True if message sent successfully, False otherwise
    """
    ntfy_base_url = os.getenv("NTFY_BASE_URL")
    token = os.getenv("NTFY_TOKEN")

    if not ntfy_base_url or not token:
        logger.error("NTFY_BASE_URL or NTFY_TOKEN not configured")
        return False

    url = f"{ntfy_base_url.rstrip('/')}/{topic}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain",
    }

    if title:
        headers["Title"] = title
    if priority:
        headers["Priority"] = str(priority)

    try:
        response = requests.post(url, headers=headers, data=message)
        response.raise_for_status()
        logger.info(f"Ntfy message sent successfully to topic {topic}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send ntfy message: {e}")
        return False