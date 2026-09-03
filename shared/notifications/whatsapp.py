"""Send text through the existing wacli sync process's Unix socket."""

import json
import logging
import socket
from time import monotonic, time

from shared.settings import WhatsAppSettings

logger = logging.getLogger(__name__)
_MAX_RESPONSE_BYTES = 64 * 1024


def whatsapp_available(socket_path: str, timeout_seconds: float = 3) -> bool:
    """Check local socket availability without requesting a WhatsApp operation."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout_seconds)
            connection.connect(socket_path)
        return True
    except OSError:
        return False


def send_whatsapp_message(message: str, whatsapp_settings: WhatsAppSettings) -> bool:
    """Return whether wacli confirmed acceptance, without retrying uncertain sends.

    Protocol version 1 matches Habitat's pinned wacli commit
    97e14efdf91a7c9de1b68845321eb6355943b5f5, cmd/wacli/send_ipc.go.
    Sync must use --send-spacing so queued requests honor their deadlines.
    """
    if not message.strip():
        return False

    started = monotonic()
    deadline = started + whatsapp_settings.timeout_seconds
    send_seconds = whatsapp_settings.timeout_seconds - 5
    request = {
        "version": 1,
        "kind": "text",
        "to": whatsapp_settings.target,
        "message": message,
        "no_preview": True,
        "timeout_ms": send_seconds * 1000,
        "deadline_unix_ms": int((time() + send_seconds) * 1000),
    }
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(max(0.001, deadline - monotonic()))
            connection.connect(whatsapp_settings.socket_path)
            connection.settimeout(max(0.001, deadline - monotonic()))
            connection.sendall(json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n")
            response = bytearray()
            while b"\n" not in response:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError
                connection.settimeout(remaining)
                chunk = connection.recv(min(4096, _MAX_RESPONSE_BYTES + 1 - len(response)))
                if not chunk:
                    break
                response.extend(chunk)
                if len(response) > _MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError("response must be an object")
    except (OSError, ValueError, UnicodeError) as exc:
        # Exception text and provider output may contain the message or recipient.
        logger.warning("WhatsApp send unconfirmed (%s, %.2fs)", type(exc).__name__, monotonic() - started)
        return False

    if result.get("ok") is True and result.get("sent") is True:
        if result.get("store_warning"):
            logger.warning("WhatsApp accepted message but local history storage failed")
        logger.info("WhatsApp accepted message (%.2fs)", monotonic() - started)
        return True
    logger.warning("WhatsApp send rejected (%.2fs)", monotonic() - started)
    return False
