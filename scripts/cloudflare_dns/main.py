"""Cloudflare DNS CLI."""

from __future__ import annotations

import argparse
import logging
import sys

from app.services.cloudflare import get_dns_record, list_dns_records
from scripts.cloudflare.cli import print_json, print_record_detail, print_record_table
from shared.logging import setup_logging
from shared.settings import get_cloudflare_settings

logger = logging.getLogger(__name__)


def _add_zone_selector(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--zone-id", default=None, help="Cloudflare zone ID.")
    parser.add_argument("--zone-name", default=None, help="Cloudflare zone name.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect Cloudflare DNS records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List DNS records in a zone.")
    _add_zone_selector(list_parser)
    list_parser.add_argument("--type", default=None, help="DNS record type filter.")
    list_parser.add_argument("--name", default=None, help="Exact DNS record name filter.")
    list_parser.add_argument("--content", default=None, help="Exact DNS record content filter.")
    list_parser.add_argument(
        "--proxied",
        dest="proxied",
        action="store_true",
        help="Only proxied DNS records.",
    )
    list_parser.add_argument(
        "--not-proxied",
        dest="proxied",
        action="store_false",
        help="Only unproxied DNS records.",
    )
    list_parser.set_defaults(proxied=None)
    list_parser.add_argument("--page", type=int, default=1, help="Result page number.")
    list_parser.add_argument(
        "--per-page",
        type=int,
        default=20,
        dest="per_page",
        help="Results per page.",
    )
    list_parser.add_argument("--json", action="store_true", dest="as_json", help="Print JSON.")

    get_parser = subparsers.add_parser("get", help="Get one DNS record by ID.")
    _add_zone_selector(get_parser)
    get_parser.add_argument("--record-id", required=True, help="DNS record ID.")
    get_parser.add_argument("--json", action="store_true", dest="as_json", help="Print JSON.")
    return parser.parse_args()


def main() -> int:
    try:
        settings = get_cloudflare_settings()
        setup_logging(settings.logging_settings())
        args = _parse_args()

        if args.command == "list":
            payload = list_dns_records(
                settings=settings,
                zone_id=args.zone_id,
                zone_name=args.zone_name,
                type=args.type,
                name=args.name,
                content=args.content,
                proxied=args.proxied,
                page=args.page,
                per_page=args.per_page,
            )
            if args.as_json:
                print_json(payload)
            else:
                print_record_table(payload)
            return 0

        payload = get_dns_record(
            settings=settings,
            zone_id=args.zone_id,
            zone_name=args.zone_name,
            record_id=args.record_id,
        )
        if args.as_json:
            print_json(payload)
        else:
            print_record_detail(payload)
        return 0
    except Exception as exc:
        logger.exception("Failed to inspect Cloudflare DNS records")
        print(f"Failed to inspect Cloudflare DNS records: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
