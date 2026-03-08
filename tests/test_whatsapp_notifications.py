"""Unit tests for WhatsApp notification sender."""

import subprocess

from shared.notifications.whatsapp import send_whatsapp_message
from shared.settings import WhatsAppSettings


def test_send_whatsapp_message_success(monkeypatch) -> None:
    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("shared.notifications.whatsapp.subprocess.run", _fake_run)

    sent = send_whatsapp_message(
        message="hello",
        whatsapp_settings=WhatsAppSettings(
            ssh_host="pookie",
            remote_script_path="/remote/send.py",
            target="1203@g.us",
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
            remote_script_path="/remote/send.py",
            target="1203@g.us",
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
            remote_script_path="/remote/send.py",
            target="1203@g.us",
            timeout_seconds=5,
        ),
    )

    assert sent is False
