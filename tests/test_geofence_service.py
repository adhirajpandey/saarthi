"""Unit tests for geofence notification service behavior."""

import asyncio

from app.services.geofence import send_geofence_notification
from shared.settings import SmtpSettings


class DummySettings:
    geofence_subject_template = "Area update: {area}"
    geofence_email_template = "Area={area}; Event={event}"
    geofence_updates_recipient = "alerts@example.com"
    geofence_sender_name = "Saarthi"

    def smtp_settings(self) -> SmtpSettings:
        return SmtpSettings(
            email="smtp@example.com",
            app_password="secret",
            host="smtp.gmail.com",
            port=465,
        )


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


def test_send_geofence_notification_template_error() -> None:
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
    assert "template configuration is invalid" in result.message


def test_send_geofence_notification_unexpected_send_error(monkeypatch) -> None:
    def _raise_error(**_kwargs):
        raise RuntimeError("smtp exploded")

    monkeypatch.setattr("app.services.geofence.send_email", _raise_error)

    result = asyncio.run(
        send_geofence_notification(
            settings=DummySettings(),  # type: ignore[arg-type]
            area="Office",
            event="exited",
        )
    )

    assert result.success is False
    assert "Unexpected error while sending geofence notification" == result.message
