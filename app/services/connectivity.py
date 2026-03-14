"""Connectivity checks used by API endpoints."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def check_dell_home_connectivity(dell_tailscale_ip: str) -> bool:
    """Return whether the Dell host is reachable over Tailscale."""
    try:
        result = subprocess.run(
            ["tailscale", "ping", "--timeout=3s", dell_tailscale_ip],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        logger.warning("tailscale binary not found; reporting dell_home_connectivity=false")
        return False
    except Exception:
        logger.exception("Failed to run tailscale ping; reporting dell_home_connectivity=false")
        return False

    if result.returncode != 0:
        logger.warning(
            "tailscale ping failed for %s with return code %s; reporting dell_home_connectivity=false",
            dell_tailscale_ip,
            result.returncode,
        )
        return False

    return True
