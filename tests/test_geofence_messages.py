"""Context, persistence, and notification integration tests using local SQLite."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
import sqlite3
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import geofence, geofence_messages as messages
from app.services.geofence_engine import GeofenceArea
from app.services.location import initialize_location_db
from shared.settings import get_api_settings


@pytest.fixture
def settings(runtime_config):
    runtime_config({
        "WHATSAPP_ENABLED": True,
        "GEOFENCE_WHATSAPP_ENABLED": True,
        "WHATSAPP_TARGET_FAMILY": "test-family@g.us",
        "WHATSAPP_SOCKET_PATH": "/tmp/mock-whatsapp.sock",
    })
    settings = get_api_settings()
    initialize_location_db(settings.location_db_path)
    return settings


def state(settings):
    with closing(sqlite3.connect(settings.location_db_path)) as conn:
        return dict(conn.execute("SELECT key, value FROM geofence_message_state"))


def build(settings, area="Office", event="entered", at="2026-09-07T10:00:00+05:30"):
    return messages.build_geofence_whatsapp_message(
        settings, area, event, now=datetime.fromisoformat(at),
    )


def test_first_entry_return_and_exit_proves_visit(settings):
    assert build(settings) in messages.MESSAGES["office_first_entry"].values()
    assert build(settings) in messages.MESSAGES["office_return"].values()
    assert state(settings)["office_visit_date"] == "2026-09-07"
    build(settings, event="exited", at="2026-09-08T10:00:00+05:30")
    assert build(settings, at="2026-09-08T10:01:00+05:30") in messages.MESSAGES["office_return"].values()


@pytest.mark.parametrize("at, category", [
    ("2026-09-07T16:59:00+05:30", "office_early_exit"),
    ("2026-09-07T17:00:00+05:30", "office_late_exit"),
    ("2026-09-07T11:29:00+00:00", "office_early_exit"),
    ("2026-09-07T11:30:00+00:00", "office_late_exit"),
])
def test_office_exit_boundary(settings, at, category):
    assert build(settings, event="exited", at=at) in messages.MESSAGES[category].values()
    assert state(settings)["office_visit_date"] == "2026-09-07"


def test_ist_midnight_resets_office_context(settings):
    build(settings, at="2026-09-07T18:29:59+00:00")
    assert build(settings, at="2026-09-07T18:30:00+00:00") in messages.MESSAGES["office_first_entry"].values()
    assert state(settings)["office_visit_date"] == "2026-09-08"


@pytest.mark.parametrize("at, office_event, category", [
    ("2026-09-05T10:00:00+05:30", None, "eas_weekend"),
    ("2026-09-06T10:00:00+05:30", None, "eas_weekend"),
    ("2026-09-07T10:00:00+05:30", None, "eas_entry"),
    ("2026-09-05T10:00:00+05:30", "entered", "eas_after_office"),
    ("2026-09-06T10:00:00+05:30", "exited", "eas_after_office"),
    ("2026-09-07T10:00:00+05:30", "exited", "eas_after_office"),
])
def test_eas_entry_context(settings, monkeypatch, at, office_event, category):
    monkeypatch.setattr(messages.random, "choice", lambda variants: variants[-1])
    if office_event:
        build(settings, event=office_event, at=at)
    assert build(settings, "EAS Badminton", at=at) == messages.MESSAGES[category]["playful"]
    assert f"last_variant:{category}" in state(settings)
    if not office_event:
        assert "office_visit_date" not in state(settings)


def test_eas_exit_and_previous_day_office(settings, monkeypatch):
    monkeypatch.setattr(messages.random, "choice", lambda variants: variants[-1])
    build(settings, event="exited", at="2026-09-04T18:29:59+00:00")
    assert build(settings, "EAS Badminton", at="2026-09-04T18:30:00+00:00") == messages.MESSAGES["eas_weekend"]["playful"]
    assert build(settings, "EAS Badminton", "exited") == messages.MESSAGES["eas_exit"]["playful"]
    assert state(settings)["office_visit_date"] == "2026-09-04"


def test_variant_persistence_and_dictionary_extension(settings, monkeypatch):
    first = build(settings, "EAS Badminton", "exited")
    # The builder closes its connection each time; a new settings object also uses saved state.
    reopened = settings.model_copy()
    second = build(reopened, "EAS Badminton", "exited")
    assert first != second
    assert build(reopened, "EAS Badminton", "exited") == first
    previous = state(settings)["last_variant:eas_exit"]
    monkeypatch.setitem(messages.MESSAGES["eas_exit"], "extra", "Adhiraj EAS se bahar aa gaye.")
    choice = Mock(return_value="extra")
    monkeypatch.setattr(messages.random, "choice", choice)
    assert build(settings, "EAS Badminton", "exited") == "Adhiraj EAS se bahar aa gaye."
    assert set(choice.call_args.args[0]) == set(messages.MESSAGES["eas_exit"]) - {previous}
    assert state(settings)["last_variant:eas_exit"] == "extra"


def test_concurrent_office_entries_have_one_first_entry(settings):
    barrier = Barrier(2)

    def select():
        barrier.wait(timeout=5)
        return build(settings)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(select) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert sum(result in messages.MESSAGES["office_first_entry"].values() for result in results) == 1
    assert sum(result in messages.MESSAGES["office_return"].values() for result in results) == 1


@pytest.mark.parametrize("area", ["Home", "office", "Office ", "EAS", "EAS badminton"])
@pytest.mark.parametrize("event", ["entered", "exited"])
def test_unknown_areas_never_access_state(settings, monkeypatch, area, event):
    connect = Mock(side_effect=AssertionError("Unexpected state access"))
    monkeypatch.setattr(messages.sqlite3, "connect", connect)
    template = getattr(settings, f"geofence_whatsapp_{event}_template")
    assert build(settings, area, event) == template.format(area=area)
    connect.assert_not_called()


@pytest.mark.parametrize("flag", ["whatsapp_enabled", "geofence_whatsapp_enabled"])
def test_disabled_family_skips_builder_and_keeps_email(settings, monkeypatch, flag):
    setattr(settings, flag, False)
    builder = Mock(side_effect=AssertionError("Unexpected builder call"))
    whatsapp = Mock()
    email = Mock(return_value=True)
    monkeypatch.setattr(geofence, "build_geofence_whatsapp_message", builder)
    monkeypatch.setattr(geofence, "send_whatsapp_message", whatsapp)
    monkeypatch.setattr(geofence, "send_email", email)
    assert asyncio.run(geofence.send_geofence_notification(settings, "Office", "entered")).success
    builder.assert_not_called()
    whatsapp.assert_not_called()
    email.assert_called_once()
    assert state(settings) == {}
    assert build(settings) == settings.geofence_whatsapp_entered_template.format(area="Office")
    assert state(settings) == {}


@pytest.mark.parametrize("failure", [False, RuntimeError("mock send failed")])
def test_failed_transport_consumes_selection_and_office_visit(settings, monkeypatch, failure):
    settings.email_enabled = False
    attempts = []

    def send(**kwargs):
        # A separate connection sees committed state while the sender is running.
        attempts.append((kwargs["message"], state(settings)))
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(geofence, "send_whatsapp_message", send)
    for _ in range(2):
        assert not asyncio.run(geofence.send_geofence_notification(settings, "Office", "exited")).success
    assert len(attempts) == 2
    assert attempts[0][0] != attempts[1][0]
    assert "office_visit_date" in attempts[0][1]
    monkeypatch.setattr(geofence, "send_whatsapp_message", Mock(return_value=True))
    assert asyncio.run(geofence.send_geofence_notification(settings, "Office", "entered")).success
    sent = geofence.send_whatsapp_message.call_args.kwargs["message"]
    assert sent in messages.MESSAGES["office_return"].values()


@pytest.mark.parametrize("failure", ["missing_table", "open", "write"])
def test_state_failure_uses_generic_and_preserves_email(settings, monkeypatch, caplog, failure):
    if failure == "open":
        settings.location_db_path += "/unavailable.db"
    else:
        with closing(sqlite3.connect(settings.location_db_path)) as conn, conn:
            if failure == "missing_table":
                conn.execute("DROP TABLE geofence_message_state")
            else:
                conn.execute("""CREATE TRIGGER fail_variant BEFORE INSERT ON geofence_message_state
                    WHEN NEW.key LIKE 'last_variant:%'
                    BEGIN SELECT RAISE(ABORT, 'mock write failure'); END""")
    email = Mock(return_value=True)
    whatsapp = Mock(return_value=True)
    monkeypatch.setattr(geofence, "send_email", email)
    monkeypatch.setattr(geofence, "send_whatsapp_message", whatsapp)
    assert asyncio.run(geofence.send_geofence_notification(settings, "Office", "entered")).success
    assert whatsapp.call_args.kwargs["message"] == settings.geofence_whatsapp_entered_template.format(area="Office")
    email.assert_called_once()
    assert "Failed to access geofence message state" in caplog.text
    if failure == "write":
        assert state(settings) == {}


def test_time_captured_once_before_email_and_builder_runs_in_threadpool(settings, monkeypatch):
    before = datetime.fromisoformat("2026-09-07T18:29:59+00:00")
    after = datetime.fromisoformat("2026-09-07T18:30:00+00:00")
    clock = Mock(return_value=before)
    monkeypatch.setattr(geofence, "datetime", SimpleNamespace(now=clock))

    def email(**kwargs):
        clock.return_value = after
        assert kwargs["recipient"] == settings.geofence_updates_recipient
        assert kwargs["subject"] == settings.geofence_subject_template.format(area="Office")
        assert kwargs["body"] == settings.geofence_email_template.format(area="Office", event="entered")
        assert kwargs["sender_name"] == settings.geofence_sender_name
        return True

    original = messages.build_geofence_whatsapp_message

    def builder(*args, **kwargs):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        assert kwargs["now"] == before
        return original(*args, **kwargs)

    monkeypatch.setattr(geofence, "build_geofence_whatsapp_message", builder)
    monkeypatch.setattr(geofence, "send_email", email)
    whatsapp = Mock(return_value=False)
    monkeypatch.setattr(geofence, "send_whatsapp_message", whatsapp)
    assert asyncio.run(geofence.send_geofence_notification(settings, "Office", "entered")).success
    clock.assert_called_once()
    assert state(settings)["office_visit_date"] == "2026-09-07"
    assert whatsapp.call_args.kwargs["whatsapp_settings"].target == "test-family@g.us"


def test_schema_initialization_preserves_existing_location_and_state(settings):
    with closing(sqlite3.connect(settings.location_db_path)) as conn, conn:
        conn.execute("DROP TABLE geofence_message_state")
        conn.execute("INSERT INTO me_locations (latitude, longitude, recorded_at) VALUES (12, 77, '2026-09-07T00:00:00+00:00')")
        original = conn.execute("SELECT * FROM me_locations").fetchall()
    initialize_location_db(settings.location_db_path)
    assert state(settings) == {}
    build(settings)
    saved = state(settings)
    for _ in range(2):
        initialize_location_db(settings.location_db_path)
    assert state(settings) == saved
    with closing(sqlite3.connect(settings.location_db_path)) as conn:
        assert conn.execute("SELECT * FROM me_locations").fetchall() == original


def test_both_http_paths_share_context(settings, monkeypatch):
    sent = []
    monkeypatch.setattr(geofence, "send_email", Mock(return_value=True))
    monkeypatch.setattr(geofence, "send_whatsapp_message", lambda **kw: sent.append(kw["message"]) or True)
    headers = {"Authorization": "Bearer test-admin-token"}
    with TestClient(app) as client:
        app.state.geofence_mapping = [GeofenceArea(name="Office", latitude=12, longitude=77, radius_meters=200)]
        response = client.post("/geofence/events", json={"area": "Office", "event": "entered"}, headers=headers)
        assert response.status_code == 200
        assert set(response.json()) == {"success", "message"}
        for latitude in (13, 12):
            response = client.post("/me/location", json={"latitude": latitude, "longitude": 77}, headers=headers)
            assert response.status_code == 200
            assert set(response.json()) == {"success", "id", "timestamp"}
    assert len(sent) == 2
    assert sent[0] in messages.MESSAGES["office_first_entry"].values()
    assert sent[1] in messages.MESSAGES["office_return"].values()


@pytest.mark.parametrize("category, area, event, at, office_visit", [
    ("office_first_entry", "Office", "entered", "2026-09-07T10:00:00+05:30", False),
    ("office_return", "Office", "entered", "2026-09-07T10:00:00+05:30", True),
    ("office_early_exit", "Office", "exited", "2026-09-07T16:59:00+05:30", False),
    ("office_late_exit", "Office", "exited", "2026-09-07T17:00:00+05:30", False),
    ("eas_after_office", "EAS Badminton", "entered", "2026-09-05T18:00:00+05:30", True),
    ("eas_weekend", "EAS Badminton", "entered", "2026-09-05T18:00:00+05:30", False),
    ("eas_entry", "EAS Badminton", "entered", "2026-09-07T18:00:00+05:30", False),
    ("eas_exit", "EAS Badminton", "exited", "2026-09-07T19:00:00+05:30", False),
])
def test_generated_samples(settings, monkeypatch, category, area, event, at, office_visit):
    instant = datetime.fromisoformat(at)
    monkeypatch.setattr(geofence, "datetime", SimpleNamespace(now=lambda tz: instant))
    monkeypatch.setattr(messages.random, "choice", lambda variants: variants[0])
    monkeypatch.setattr(geofence, "send_email", Mock(return_value=True))
    sender = Mock(return_value=True)
    monkeypatch.setattr(geofence, "send_whatsapp_message", sender)
    for variant in ("plain", "playful"):
        if office_visit:
            build(settings, event="exited", at=at)
        elif category == "office_first_entry":
            # Simulate a new day with no office visit, retaining variant history.
            with closing(sqlite3.connect(settings.location_db_path)) as conn, conn:
                conn.execute("DELETE FROM geofence_message_state WHERE key = 'office_visit_date'")
        assert asyncio.run(geofence.send_geofence_notification(settings, area, event)).success
        sample = sender.call_args.kwargs["message"]
        assert sample == messages.MESSAGES[category][variant]
        print(f"{category}/{variant}: {sample}")


def test_builder_defaults_to_aware_ist_time(settings, monkeypatch):
    clock = Mock(return_value=datetime.fromisoformat("2026-09-07T17:00:00+05:30"))
    monkeypatch.setattr(messages, "datetime", SimpleNamespace(now=clock))
    result = messages.build_geofence_whatsapp_message(settings, "Office", "exited")
    clock.assert_called_once_with(messages.IST)
    assert result in messages.MESSAGES["office_late_exit"].values()
