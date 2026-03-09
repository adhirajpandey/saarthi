"""Manual test for geofence WhatsApp helper.

Run:
  python3 scripts/manual/whatsapp_helper.py --message "Test from saarthi helper"
"""

from __future__ import annotations

import argparse
import sys

from shared.notifications.whatsapp import send_whatsapp_message
from shared.settings import get_api_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Test saarthi WhatsApp helper")
    parser.add_argument(
        "--message",
        default="Hello from saarthi test_whatsapp_helper.py",
        help="Message to send via helper",
    )
    args = parser.parse_args()

    settings = get_api_settings()
    ok = send_whatsapp_message(
        message=args.message,
        whatsapp_settings=settings.whatsapp_settings_for_geofence(),
    )
    if ok:
        print("WhatsApp helper send: OK")
        return 0

    print("WhatsApp helper send: FAILED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
