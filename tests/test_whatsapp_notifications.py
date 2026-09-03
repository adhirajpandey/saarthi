"""Exercise the sender against an isolated wacli-protocol Unix socket."""

from contextlib import contextmanager
import json
import socket
import threading
from time import time

import pytest

from shared.notifications.whatsapp import send_whatsapp_message, whatsapp_available
from shared.settings import WhatsAppSettings


@pytest.fixture
def socket_server(test_workspace, monkeypatch):
    # Only these tests can connect real sockets, always in their private workspace.
    monkeypatch.setattr("shared.notifications.whatsapp.socket", socket)

    @contextmanager
    def serve(chunks):
        path = str(test_workspace / "send.sock")
        requests = []
        errors = []
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(path)
            listener.listen()
            listener.settimeout(2)

            def handle():
                try:
                    with listener.accept()[0] as connection:
                        connection.settimeout(2)
                        data = connection.makefile("rb").readline()
                        if data:
                            requests.append(json.loads(data))
                            for chunk in chunks:
                                connection.sendall(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as exc:
                    errors.append(exc)

            worker = threading.Thread(target=handle, daemon=True)
            worker.start()
            try:
                yield WhatsAppSettings(socket_path=path, target="15550001111@s.whatsapp.net", timeout_seconds=60), requests
            finally:
                worker.join(3)
                assert not worker.is_alive()
                assert not errors
        (test_workspace / "send.sock").unlink()

    return serve


def test_text_protocol_preserves_unicode_and_multiline_message(socket_server):
    message = "नमस्ते 👋\nBackup done; $(whoami) stays text."
    before = time()
    with socket_server([b'{"ok":true,', b'"sent":true,"id":"test-id"}\n']) as (settings, requests):
        assert send_whatsapp_message(message, settings) is True
    request, = requests
    assert request == {
        "version": 1,
        "kind": "text",
        "to": settings.target,
        "message": message,
        "no_preview": True,
        "timeout_ms": 55000,
        "deadline_unix_ms": request["deadline_unix_ms"],
    }
    assert int((before + 55) * 1000) <= request["deadline_unix_ms"] <= int((time() + 55) * 1000)


@pytest.mark.parametrize("response,accepted", [
    ({"ok": True, "sent": True}, True),
    ({"ok": True, "sent": True, "store_warning": "private database details"}, True),
    ({"ok": False, "error": "private recipient details"}, False),
    ({"ok": True, "sent": False}, False),
    ({"ok": True}, False),
    ({"ok": "true", "sent": True}, False),
    ({"ok": True, "sent": 1}, False),
    ([], False),
    (None, False),
])
def test_requires_explicit_acceptance_without_retry(socket_server, response, accepted, caplog):
    with socket_server([json.dumps(response).encode() + b"\n"]) as (settings, requests):
        assert send_whatsapp_message("private body", settings) is accepted
    assert len(requests) == 1
    assert "private" not in caplog.text
    assert settings.target not in caplog.text


@pytest.mark.parametrize("chunks", [
    [b"not JSON\n"], [b'{"ok":true'], [], [b"\xff\n"], [b"x" * 65537],
])
def test_invalid_or_incomplete_response(socket_server, chunks):
    with socket_server(chunks) as (settings, requests):
        assert send_whatsapp_message("hello", settings) is False
    assert len(requests) == 1


def test_response_can_finish_at_eof(socket_server):
    with socket_server([b'{"ok":true,"sent":true}']) as (settings, _):
        assert send_whatsapp_message("hello", settings) is True


def test_missing_socket(test_workspace, monkeypatch):
    monkeypatch.setattr("shared.notifications.whatsapp.socket", socket)
    settings = WhatsAppSettings(socket_path=str(test_workspace / "absent.sock"), target="15550001111@s.whatsapp.net", timeout_seconds=60)
    assert send_whatsapp_message("hello", settings) is False
    assert whatsapp_available(settings.socket_path) is False


def test_blank_message_never_connects():
    settings = WhatsAppSettings(socket_path="/must-not-connect", target="15550001111@s.whatsapp.net", timeout_seconds=60)
    assert send_whatsapp_message(" \n ", settings) is False


def test_deadline_is_shared_by_all_reads(socket_server, monkeypatch, caplog):
    ticks = iter([0, 0, 0, 61, 61])
    monkeypatch.setattr("shared.notifications.whatsapp.monotonic", lambda: next(ticks))
    with socket_server([]) as (settings, requests):
        assert send_whatsapp_message("private body", settings) is False
    assert len(requests) == 1
    assert "TimeoutError" in caplog.text
    assert "private body" not in caplog.text


def test_health_only_connects_and_sends_no_request(socket_server):
    with socket_server([]) as (settings, requests):
        assert whatsapp_available(settings.socket_path) is True
    assert requests == []


def test_new_connection_after_socket_recreation(socket_server):
    for _ in range(2):
        with socket_server([b'{"ok":true,"sent":true}\n']) as (settings, requests):
            assert send_whatsapp_message("hello", settings) is True
        assert len(requests) == 1
