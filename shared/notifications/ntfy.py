"""Ntfy push notification sender."""

import requests

from shared.config.env import get_env, load_environment
from shared.logging import logger


def send_ntfy_message(
    topic: str,
    message: str,
    title: str | None = None,
    priority: int | None = None,
) -> bool:
    """Send a message to an ntfy topic."""
    load_environment()
    ntfy_base_url = get_env("NTFY_BASE_URL")
    token = get_env("NTFY_TOKEN")

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
        response = requests.post(url, headers=headers, data=message, timeout=30)
        response.raise_for_status()
        logger.info(f"Ntfy message sent successfully to topic {topic}")
        return True
    except requests.RequestException as exc:
        logger.error(f"Failed to send ntfy message: {exc}")
        return False

