"""Unit tests for notification transport clients."""

from shared.notifications.email import send_email
from shared.settings import SmtpSettings


def test_send_email_success(monkeypatch) -> None:
    observed: dict[str, str] = {}

    class _FakeServer:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def login(self, email: str, password: str) -> None:
            observed["login_email"] = email
            observed["login_password"] = password

        def sendmail(self, sender: str, recipient: str, _raw: str) -> None:
            observed["sender"] = sender
            observed["recipient"] = recipient

    monkeypatch.setattr("shared.notifications.email.smtplib.SMTP_SSL", lambda *_: _FakeServer())

    sent = send_email(
        recipient="alerts@example.com",
        subject="Test",
        body="Body",
        smtp_settings=SmtpSettings(
            email="smtp@example.com",
            app_password="secret",
            host="smtp.example.com",
            port=465,
        ),
        sender_name="Saarthi",
    )

    assert sent is True
    assert observed["login_email"] == "smtp@example.com"
    assert observed["login_password"] == "secret"
    assert observed["recipient"] == "alerts@example.com"


def test_send_email_returns_false_on_error(monkeypatch) -> None:
    class _BoomServer:
        def __init__(self, *_args, **_kwargs):
            raise OSError("smtp down")

    monkeypatch.setattr("shared.notifications.email.smtplib.SMTP_SSL", _BoomServer)

    sent = send_email(
        recipient="alerts@example.com",
        subject="Test",
        body="Body",
        smtp_settings=SmtpSettings(
            email="smtp@example.com",
            app_password="secret",
            host="smtp.example.com",
            port=465,
        ),
    )

    assert sent is False
