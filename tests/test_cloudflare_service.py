"""Tests for Cloudflare service helpers."""

from __future__ import annotations

import pytest

from app.services.cloudflare.client import (
    CloudflareApiError,
    get_dns_record,
    list_dns_records,
    list_zones,
)
from shared.settings import get_cloudflare_settings


class _FakeResponse:
    def __init__(self, payload, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True
        if self.status_code >= 400:
            raise RuntimeError(f"http-{self.status_code}")

    def json(self):
        return self._payload


def test_list_zones_normalizes_response(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_cloudflare_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        return _FakeResponse(
            {
                "success": True,
                "result": [
                    {
                        "id": "zone-1",
                        "name": "example.com",
                        "status": "active",
                        "paused": False,
                        "type": "full",
                        "created_on": "2026-01-01T00:00:00Z",
                        "modified_on": "2026-01-02T00:00:00Z",
                        "name_servers": ["ns1", "ns2"],
                    }
                ],
            }
        )

    monkeypatch.setattr("app.services.cloudflare.client.requests.request", _fake_request)

    result = list_zones(settings=settings, name="example.com", page=2, per_page=10)

    assert result["success"] is True
    assert result["count"] == 1
    assert result["zones"][0]["name"] == "example.com"
    assert calls[0]["params"] == {"name": "example.com", "page": 2, "per_page": 10}
    assert calls[0]["headers"]["Authorization"] == "Bearer test-cloudflare-token"
    assert calls[0]["timeout"] == 20


def test_list_dns_records_resolves_zone_name_and_normalizes_records(
    monkeypatch, runtime_config
) -> None:
    runtime_config()
    settings = get_cloudflare_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/zones"):
            return _FakeResponse(
                {
                    "success": True,
                    "result": [{"id": "zone-1", "name": "example.com"}],
                }
            )
        return _FakeResponse(
            {
                "success": True,
                "result": [
                    {
                        "id": "record-1",
                        "zone_id": "zone-1",
                        "name": "api.example.com",
                        "type": "A",
                        "content": "1.2.3.4",
                        "proxied": True,
                        "ttl": 1,
                        "comment": "edge",
                        "created_on": "2026-01-01T00:00:00Z",
                        "modified_on": "2026-01-02T00:00:00Z",
                    }
                ],
            }
        )

    monkeypatch.setattr("app.services.cloudflare.client.requests.request", _fake_request)

    result = list_dns_records(
        settings=settings,
        zone_name="example.com",
        type="a",
        name="api.example.com",
        content="1.2.3.4",
        proxied=True,
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["filters"]["zone_id"] == "zone-1"
    assert result["records"][0]["zone_name"] == "example.com"
    assert calls[1]["params"] == {
        "page": 1,
        "per_page": 20,
        "type": "A",
        "name.exact": "api.example.com",
        "content.exact": "1.2.3.4",
        "proxied": True,
    }


def test_get_dns_record_uses_zone_id_without_lookup(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_cloudflare_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        return _FakeResponse(
            {
                "success": True,
                "result": {
                    "id": "record-1",
                    "zone_id": "zone-1",
                    "name": "api.example.com",
                    "type": "A",
                    "content": "1.2.3.4",
                    "proxied": True,
                    "ttl": 1,
                    "comment": None,
                    "created_on": "2026-01-01T00:00:00Z",
                    "modified_on": "2026-01-02T00:00:00Z",
                },
            }
        )

    monkeypatch.setattr("app.services.cloudflare.client.requests.request", _fake_request)

    result = get_dns_record(settings=settings, zone_id="zone-1", record_id="record-1")

    assert result["success"] is True
    assert result["record"]["id"] == "record-1"
    assert calls[0]["url"].endswith("/zones/zone-1/dns_records/record-1")


def test_list_dns_records_requires_exactly_one_zone_selector(runtime_config) -> None:
    runtime_config()
    settings = get_cloudflare_settings()

    with pytest.raises(ValueError, match="exactly one of zone_id or zone_name"):
        list_dns_records(settings=settings, zone_id="zone-1", zone_name="example.com")


def test_cloudflare_api_failure_raises_clear_error(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_cloudflare_settings()

    monkeypatch.setattr(
        "app.services.cloudflare.client.requests.request",
        lambda **_kwargs: _FakeResponse(
            {
                "success": False,
                "errors": [{"message": "Authentication error"}],
            }
        ),
    )

    with pytest.raises(CloudflareApiError, match="Authentication error"):
        list_zones(settings=settings)


def test_cloudflare_http_4xx_preserves_json_error_message(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_cloudflare_settings()
    response = _FakeResponse(
        {
            "success": False,
            "errors": [{"message": "Invalid request headers"}],
        },
        status_code=403,
    )

    monkeypatch.setattr(
        "app.services.cloudflare.client.requests.request",
        lambda **_kwargs: response,
    )

    with pytest.raises(CloudflareApiError, match="Invalid request headers"):
        list_zones(settings=settings)

    assert response.raise_for_status_called is False
