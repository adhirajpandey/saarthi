"""Unit tests for geofence notification service behavior."""

import asyncio

from app.services.geofence import send_geofence_notification
from shared.settings import SmtpSettings


class DummySettings:
    email_enabled = True
    whatsapp_enabled = False
    geofence_subject_template = "Area update: {area}"
    geofence_email_template = "Area={area}; Event={event}"
    geofence_whatsapp_entered_template = "WA entered {area}"
    geofence_whatsapp_exited_template = "WA exited {area}"
    geofence_updates_recipient = "alerts@example.com"
    geofence_sender_name = "Saarthi"

    def smtp_settings(self) -> SmtpSettings:
        return SmtpSettings(
            email="smtp@example.com",
            app_password="secret",
            host="smtp.gmail.com",
            port=465,
        )

    def whatsapp_settings_for_geofence(self):
        raise AssertionError("whatsapp_settings should not be called in this test")


def test_send_geofence_notification_success(monkeypatch) -> None:
    monkeypatch.setattr("app.services.geofence.send_email", lambda **_: True)

    result = asyncio.run(
        send_geofence_notification(
            settings=DummySettings(),  # type: ignore[arg-type]
            area="Home",
            event="entered",
        )
    )

    assert result.success is True
    assert "Home" in result.message


def test_send_geofence_notification_template_error_email() -> None:
    settings = DummySettings()
    settings.geofence_subject_template = "Area update: {missing}"

    result = asyncio.run(
        send_geofence_notification(
            settings=settings,  # type: ignore[arg-type]
            area="Home",
            event="entered",
        )
    )

    assert result.success is False
    assert "Failed to send geofence notifications" in result.message


def test_send_geofence_notification_template_error_whatsapp() -> None:
    settings = DummySettings()
    settings.email_enabled = False
    settings.whatsapp_enabled = True
    settings.geofence_whatsapp_entered_template = "WA Area={missing}"
    settings.whatsapp_settings_for_geofence = lambda: object()

    result = asyncio.run(
        send_geofence_notification(
            settings=settings,  # type: ignore[arg-type]
            area="Home",
            event="entered",
        )
    )

    assert result.success is False
    assert "Failed to send geofence notifications" in result.message


def test_send_geofence_notification_ignores_disabled_whatsapp_template(monkeypatch) -> None:
    settings = DummySettings()
    settings.whatsapp_enabled = False
    settings.geofence_whatsapp_entered_template = "WA Area={missing}"

    monkeypatch.setattr("app.services.geofence.send_email", lambda **_: True)

    result = asyncio.run(
        send_geofence_notification(
            settings=settings,  # type: ignore[arg-type]
            area="Home",
            event="entered",
        )
    )

    assert result.success is True
    assert "Home" in result.message


def test_send_geofence_notification_any_success_with_whatsapp(monkeypatch) -> None:
    settings = DummySettings()
    settings.whatsapp_enabled = True
    settings.whatsapp_settings_for_geofence = lambda: object()
    sent_messages: list[str] = []

    monkeypatch.setattr("app.services.geofence.send_email", lambda **_: False)
    monkeypatch.setattr(
        "app.services.geofence.send_whatsapp_message",
        lambda **kwargs: sent_messages.append(kwargs["message"]) or True,
    )

    result = asyncio.run(
        send_geofence_notification(
            settings=settings,  # type: ignore[arg-type]
            area="Office",
            event="exited",
        )
    )

    assert result.success is True
    assert "Office" in result.message
    assert sent_messages == ["WA exited Office"]


def test_send_geofence_notification_uses_entered_whatsapp_template(monkeypatch) -> None:
    settings = DummySettings()
    settings.email_enabled = False
    settings.whatsapp_enabled = True
    settings.whatsapp_settings_for_geofence = lambda: object()
    sent_messages: list[str] = []

    monkeypatch.setattr(
        "app.services.geofence.send_whatsapp_message",
        lambda **kwargs: sent_messages.append(kwargs["message"]) or True,
    )

    result = asyncio.run(
        send_geofence_notification(
            settings=settings,  # type: ignore[arg-type]
            area="Office",
            event="entered",
        )
    )

    assert result.success is True
    assert sent_messages == ["WA entered Office"]


def test_send_geofence_notification_all_fail(monkeypatch) -> None:
    settings = DummySettings()
    settings.whatsapp_enabled = True
    settings.whatsapp_settings_for_geofence = lambda: object()

    monkeypatch.setattr("app.services.geofence.send_email", lambda **_: False)
    monkeypatch.setattr("app.services.geofence.send_whatsapp_message", lambda **_: False)

    result = asyncio.run(
        send_geofence_notification(
            settings=settings,  # type: ignore[arg-type]
            area="Office",
            event="exited",
        )
    )

    assert result.success is False
    assert "Failed to send geofence notifications" in result.message
