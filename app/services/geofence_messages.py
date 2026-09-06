"""Contextual family WhatsApp copy and persistent selection state."""

from contextlib import closing
from datetime import datetime
import logging
import random
import sqlite3
from zoneinfo import ZoneInfo

from shared.settings import ApiSettings

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

# Keep variant IDs stable when editing or adding copy.
MESSAGES = {
    "office_first_entry": {
        "plain": "Adhiraj office pahunch gaye.",
        "playful": "Adhiraj office pahunch gaye. Aaj ki attendance lag gayi.",
    },
    "office_return": {
        "plain": "Adhiraj office wapas aa gaye.",
        "playful": "Adhiraj wapas office mein. Bugs ne phir bula liya.",
    },
    "office_early_exit": {
        "plain": "Adhiraj office se abhi bahar nikle hain.",
        "playful": "Adhiraj office se bahar nikle hain. Filhaal keyboard ko break.",
    },
    "office_late_exit": {
        "plain": "Adhiraj office se nikal gaye.",
        "playful": "Adhiraj office se nikal gaye. Bugs filhaal wahin hain.",
    },
    "eas_after_office": {
        "plain": "Adhiraj EAS pahunch gaye.",
        "playful": "Adhiraj EAS pahunch gaye. Aaj ki doosri attendance bhi lag gayi 🏸",
    },
    "eas_weekend": {
        "plain": "Adhiraj EAS pahunch gaye.",
        "playful": "Adhiraj EAS pahunch gaye. Weekend ki court attendance lag gayi.",
    },
    "eas_entry": {
        "plain": "Adhiraj EAS pahunch gaye.",
        "playful": "Adhiraj EAS pahunch gaye. Court ki attendance lag gayi 🏸",
    },
    "eas_exit": {
        "plain": "Adhiraj EAS se nikal gaye.",
        "playful": "Adhiraj EAS se nikal gaye. Score woh khud batayenge 😄",
    },
}


def _generic_message(settings: ApiSettings, area: str, event: str) -> str:
    if event == "entered":
        template = settings.geofence_whatsapp_entered_template
    elif event == "exited":
        template = settings.geofence_whatsapp_exited_template
    else:
        raise ValueError(f"Unsupported geofence event for WhatsApp template: {event}")
    return template.format(area=area)


def build_geofence_whatsapp_message(
    settings: ApiSettings, area: str, event: str, *, now: datetime | None = None,
) -> str:
    """Commit context and a non-repeating variant before WhatsApp transport."""
    if (
        not (settings.whatsapp_enabled and settings.geofence_whatsapp_enabled)
        or area not in ("Office", "EAS Badminton")
        or event not in ("entered", "exited")
    ):
        return _generic_message(settings, area, event)

    local_now = (now if now is not None else datetime.now(IST)).astimezone(IST)
    today = local_now.date().isoformat()
    try:
        with closing(sqlite3.connect(settings.location_db_path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT value FROM geofence_message_state WHERE key = 'office_visit_date'"
            ).fetchone()
            visited_office = row is not None and row[0] == today
            if area == "Office":
                if event == "entered":
                    category = "office_return" if visited_office else "office_first_entry"
                else:
                    category = "office_early_exit" if local_now.hour < 17 else "office_late_exit"
                conn.execute(
                    "INSERT OR REPLACE INTO geofence_message_state (key, value) VALUES (?, ?)",
                    ("office_visit_date", today),
                )
            elif event == "exited":
                category = "eas_exit"
            elif visited_office:
                category = "eas_after_office"
            elif local_now.weekday() >= 5:
                category = "eas_weekend"
            else:
                category = "eas_entry"

            key = f"last_variant:{category}"
            row = conn.execute(
                "SELECT value FROM geofence_message_state WHERE key = ?", (key,),
            ).fetchone()
            previous = row[0] if row else None
            variants = MESSAGES[category]
            selected = random.choice([variant for variant in variants if variant != previous])
            conn.execute(
                "INSERT OR REPLACE INTO geofence_message_state (key, value) VALUES (?, ?)",
                (key, selected),
            )
        return variants[selected]
    except sqlite3.Error:
        logger.exception("Failed to access geofence message state; using generic template")
        return _generic_message(settings, area, event)
