"""Connectivity checks used by API endpoints."""

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def _is_command_runnable(cmd: list[str], *, command_name: str) -> bool:
    """Return whether a command binary exists and executes successfully."""
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        logger.warning("%s binary not found; reporting unavailable", command_name)
        return False
    except Exception:
        logger.exception("Failed to run %s probe; reporting unavailable", command_name)
        return False

    if result.returncode != 0:
        logger.warning(
            "%s probe failed with return code %s; reporting unavailable",
            command_name,
            result.returncode,
        )
        return False

    return True


def check_tailscale_available() -> bool:
    """Return whether tailscale command is available and runnable."""
    return _is_command_runnable(["tailscale", "version"], command_name="tailscale")


def check_rclone_available() -> bool:
    """Return whether rclone command is available and runnable."""
    return _is_command_runnable(["rclone", "version"], command_name="rclone")


def check_pg_dump_available() -> bool:
    """Return whether pg_dump command is available on PATH (host-mounted)."""
    pg_dump_path = shutil.which("pg_dump")
    if not pg_dump_path:
        logger.warning("pg_dump binary not found on PATH; reporting unavailable")
        return False
    return True


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
