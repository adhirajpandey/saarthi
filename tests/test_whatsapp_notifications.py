"""Unit tests for WhatsApp notification sender."""

import subprocess

from shared.notifications.whatsapp import send_whatsapp_message
from shared.settings import WhatsAppSettings

_HERMES_BIN = "/home/pookie/.local/bin/hermes"
_HERMES_DM_TARGET = "whatsapp:166601898885178@lid"


def test_send_whatsapp_message_success(monkeypatch) -> None:
    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("shared.notifications.whatsapp.subprocess.run", _fake_run)

    sent = send_whatsapp_message(
        message="hello",
        whatsapp_settings=WhatsAppSettings(
            ssh_host="pookie",
            remote_script_path=_HERMES_BIN,
            target=_HERMES_DM_TARGET,
            timeout_seconds=5,
        ),
    )

    assert sent is True


def test_send_whatsapp_message_non_zero_exit(monkeypatch) -> None:
    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr("shared.notifications.whatsapp.subprocess.run", _fake_run)

    sent = send_whatsapp_message(
        message="hello",
        whatsapp_settings=WhatsAppSettings(
            ssh_host="pookie",
            remote_script_path=_HERMES_BIN,
            target=_HERMES_DM_TARGET,
            timeout_seconds=5,
        ),
    )

    assert sent is False


def test_send_whatsapp_message_timeout(monkeypatch) -> None:
    def _fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["ssh"], timeout=5)

    monkeypatch.setattr("shared.notifications.whatsapp.subprocess.run", _fake_run)

    sent = send_whatsapp_message(
        message="hello",
        whatsapp_settings=WhatsAppSettings(
            ssh_host="pookie",
            remote_script_path=_HERMES_BIN,
            target=_HERMES_DM_TARGET,
            timeout_seconds=5,
        ),
    )

    assert sent is False


def test_send_whatsapp_message_streams_message_to_remote_hermes(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs):
        captured["command"] = args[0]
        captured["input"] = kwargs["input"]
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("shared.notifications.whatsapp.subprocess.run", _fake_run)

    sent = send_whatsapp_message(
        message="DB Backup Success (SUCCESS)\nBackup complete for vidwiz",
        whatsapp_settings=WhatsAppSettings(
            ssh_host="pookie",
            remote_script_path=_HERMES_BIN,
            target="whatsapp:120363369409471870@g.us",
            timeout_seconds=5,
        ),
    )

    assert sent is True
    assert captured["input"] == "DB Backup Success (SUCCESS)\nBackup complete for vidwiz"
    assert captured["command"] == [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "pookie",
        "/home/pookie/.local/bin/hermes send --to whatsapp:120363369409471870@g.us --file - --quiet",
    ]


def test_send_whatsapp_message_quotes_remote_hermes_args(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs):
        captured["command"] = args[0]
        captured["input"] = kwargs["input"]
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("shared.notifications.whatsapp.subprocess.run", _fake_run)

    sent = send_whatsapp_message(
        message="hello",
        whatsapp_settings=WhatsAppSettings(
            ssh_host="pookie",
            remote_script_path="/home/pookie/bin/hermes cli",
            target="whatsapp:team chat;ops@g.us",
            timeout_seconds=5,
        ),
    )

    assert sent is True
    assert captured["command"] == [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "pookie",
        "'/home/pookie/bin/hermes cli' send --to 'whatsapp:team chat;ops@g.us' --file - --quiet",
    ]
