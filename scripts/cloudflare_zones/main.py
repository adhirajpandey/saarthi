"""Cloudflare zones CLI."""

from __future__ import annotations

import argparse
import logging
import sys

from app.services.cloudflare import list_zones
from scripts.cloudflare.cli import print_json, print_zone_table
from shared.logging import setup_logging
from shared.settings import get_cloudflare_settings

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Cloudflare zones.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List Cloudflare zones.")
    list_parser.add_argument("--name", default=None, help="Filter by exact zone name.")
    list_parser.add_argument("--status", default=None, help="Filter by zone status.")
    list_parser.add_argument("--page", type=int, default=1, help="Result page number.")
    list_parser.add_argument(
        "--per-page",
        type=int,
        default=20,
        dest="per_page",
        help="Results per page.",
    )
    list_parser.add_argument("--json", action="store_true", dest="as_json", help="Print JSON.")
    return parser.parse_args()


def main() -> int:
    try:
        settings = get_cloudflare_settings()
        setup_logging(settings.logging_settings())
        args = _parse_args()
        payload = list_zones(
            settings=settings,
            name=args.name,
            status=args.status,
            page=args.page,
            per_page=args.per_page,
        )
        if args.as_json:
            print_json(payload)
        else:
            print_zone_table(payload)
        return 0
    except Exception as exc:
        logger.exception("Failed to list Cloudflare zones")
        print(f"Failed to list Cloudflare zones: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
