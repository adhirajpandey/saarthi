"""Tests for the Trackcrow transaction search service."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.services.trackcrow_transactions import (
    TransactionSearchFilters,
    search_trackcrow_transactions,
)
from shared.settings import get_mcp_settings

_HERMES_BIN = "/home/pookie/.local/bin/hermes"
_HERMES_DM_TARGET = "whatsapp:166601898885178@lid"


def _build_settings(runtime_config):
    runtime_config(
        {
            "WHATSAPP_ENABLED": True,
            "WHATSAPP_SSH_HOST": "ssh.example.com",
            "WHATSAPP_HERMES_COMMAND_PATH": _HERMES_BIN,
            "WHATSAPP_TARGET_PERSONAL": _HERMES_DM_TARGET,
        }
    )
    return get_mcp_settings()


def test_transaction_search_requires_at_least_one_filter(runtime_config) -> None:
    settings = _build_settings(runtime_config)

    with pytest.raises(ValueError, match="at least one filter"):
        search_trackcrow_transactions(settings=settings)


def test_transaction_search_rejects_invalid_start_date(runtime_config) -> None:
    settings = _build_settings(runtime_config)

    with pytest.raises(ValueError, match="start_date must be a valid ISO-8601"):
        search_trackcrow_transactions(settings=settings, start_date="today")


def test_transaction_search_rejects_descending_date_range(runtime_config) -> None:
    settings = _build_settings(runtime_config)

    with pytest.raises(ValueError, match="start_date must be earlier"):
        search_trackcrow_transactions(
            settings=settings,
            start_date="2026-01-02",
            end_date="2026-01-01",
        )


def test_transaction_search_passes_validated_filters_to_fetcher(monkeypatch, runtime_config) -> None:
    settings = _build_settings(runtime_config)
    captured: dict[str, object] = {}

    def _fake_fetch_transaction_rows(**kwargs):
        captured.update(kwargs)
        return [
            {
                "id": 41,
                "timestamp": datetime(2026, 1, 1, 12, 30, tzinfo=UTC),
                "amount": Decimal("120.50"),
                "recipient": "Push Medical Store",
                "recipient_name": "Push Medical Store",
                "category": "Health",
                "subcategory": "Medicine",
                "type": "UPI",
                "remarks": "cough syrup",
                "location": "Bangalore",
            }
        ]

    monkeypatch.setattr(
        "app.services.trackcrow_transactions._fetch_transaction_rows",
        _fake_fetch_transaction_rows,
    )

    result = search_trackcrow_transactions(
        settings=settings,
        recipient=" Push ",
        keyword=" syrup ",
        category="Health",
        start_date="2026-01-01",
        end_date="2026-01-31",
        limit=99,
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["transactions"][0]["amount"] == 120.5
    assert result["transactions"][0]["timestamp"] == "2026-01-01T12:30:00Z"
    assert captured["dsn"] == "postgres://trackcrow"
    assert captured["user_uuid"] == "trackcrow-user-uuid"
    assert captured["filters"] == TransactionSearchFilters(
        recipient="Push",
        keyword="syrup",
        category="Health",
        start_date="2026-01-01",
        end_date="2026-01-31",
        limit=50,
    )


def test_transaction_search_returns_safe_failure_on_fetch_error(monkeypatch, runtime_config) -> None:
    settings = _build_settings(runtime_config)

    def _boom(**_kwargs):
        raise RuntimeError("database offline")

    monkeypatch.setattr("app.services.trackcrow_transactions._fetch_transaction_rows", _boom)

    result = search_trackcrow_transactions(settings=settings, keyword="milk")

    assert result == {
        "success": False,
        "message": "Failed to search Trackcrow transactions",
    }
