"""Shared CLI helpers for Cloudflare scripts."""

from __future__ import annotations

import json
from typing import Any


def print_json(payload: dict[str, Any]) -> None:
    """Print stable JSON for machine consumption."""
    print(json.dumps(payload, indent=2, sort_keys=True))


def print_zone_table(payload: dict[str, Any]) -> None:
    """Print a concise human-readable zone summary."""
    zones = payload["zones"]
    if not zones:
        print("No zones found.")
        return
    print(f"Found {payload['count']} zone(s):")
    for zone in zones:
        name_servers = ", ".join(zone["name_servers"]) if zone["name_servers"] else "-"
        print(
            f"- {zone['name']} [{zone['id']}] status={zone['status']} "
            f"paused={zone['paused']} type={zone['type']} ns={name_servers}"
        )


def print_record_table(payload: dict[str, Any]) -> None:
    """Print a concise human-readable DNS record summary."""
    records = payload["records"]
    if not records:
        print("No DNS records found.")
        return
    zone_name = payload["filters"].get("zone_name") or payload["filters"].get("zone_id")
    print(f"Found {payload['count']} DNS record(s) in {zone_name}:")
    for record in records:
        print(
            f"- {record['name']} [{record['id']}] type={record['type']} "
            f"content={record['content']} proxied={record['proxied']} ttl={record['ttl']}"
        )


def print_record_detail(payload: dict[str, Any]) -> None:
    """Print a concise human-readable DNS record detail."""
    record = payload["record"]
    print(f"Record: {record['name']} [{record['id']}]")
    print(f"Type: {record['type']}")
    print(f"Zone: {record['zone_name'] or record['zone_id']}")
    print(f"Content: {record['content']}")
    print(f"Proxied: {record['proxied']}")
    print(f"TTL: {record['ttl']}")
    print(f"Comment: {record['comment'] or '-'}")
