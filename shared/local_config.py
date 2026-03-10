"""Optional local config loader.

Loads untracked ``config.py`` from repository root and exposes values as a dict.
This is intended for non-secret runtime values that should not live in ``.env``.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG_PATH = REPO_ROOT / "config.py"


def load_local_config(*, required: bool = False) -> dict[str, Any]:
    """Load local config from ``config.py``.

    Supported shapes:
    - CONFIG = {"KEY": value}
    - Top-level UPPER_SNAKE_CASE constants
    """

    if not LOCAL_CONFIG_PATH.exists():
        if required:
            raise ValueError(f"Missing required config file: {LOCAL_CONFIG_PATH}")
        return {}

    spec = importlib.util.spec_from_file_location("saarthi_local_config", LOCAL_CONFIG_PATH)
    if spec is None or spec.loader is None:
        if required:
            raise ValueError(f"Unable to create import spec for {LOCAL_CONFIG_PATH}")
        logger.warning("Unable to create import spec for %s", LOCAL_CONFIG_PATH)
        return {}

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        if required:
            raise ValueError(f"Failed to load {LOCAL_CONFIG_PATH}: {exc}") from exc
        logger.warning("Failed to load %s: %s", LOCAL_CONFIG_PATH, exc)
        return {}

    config = getattr(module, "CONFIG", None)
    if isinstance(config, dict):
        return {str(key): value for key, value in config.items()}

    return {
        key: value
        for key, value in vars(module).items()
        if key.isupper() and not key.startswith("_")
    }
