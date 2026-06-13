"""Google Tasks OAuth bootstrap CLI."""

from __future__ import annotations

import argparse
import logging
import sys

from app.services.google_tasks import run_oauth_bootstrap as run_google_tasks_oauth_bootstrap
from shared.logging import setup_logging
from shared.settings import get_google_tasks_settings

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Authorize Saarthi for Google Tasks access.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Print the Google auth URL and prompt for the pasted redirect URL instead of opening a browser.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = _parse_args()
        settings = get_google_tasks_settings()
        setup_logging(settings.logging_settings())
        token_path = run_google_tasks_oauth_bootstrap(settings=settings, headless=args.headless)
        print(f"Google Tasks authorization saved to: {token_path}")
        return 0
    except Exception as exc:
        logger.exception("Failed to authorize Google Tasks")
        print(f"Failed to authorize Google Tasks: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
