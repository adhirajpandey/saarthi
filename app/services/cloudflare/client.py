"""Read-only Cloudflare zone and DNS record helpers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import requests
from pydantic import BaseModel, Field, ValidationError, model_validator

from shared.settings import CloudflareSettings

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.cloudflare.com/client/v4"
DEFAULT_TIMEOUT_SECONDS = 20


class CloudflareApiError(RuntimeError):
    """Raised when the Cloudflare API returns an invalid or failed response."""


class ZoneFilters(BaseModel):
    """Validated zone-list filters."""

    name: str | None = None
    status: str | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("name", "status"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                stripped = field_value.strip()
                payload[field] = stripped or None
        return payload


class DnsRecordFilters(BaseModel):
    """Validated DNS record list filters."""

    zone_id: str | None = None
    zone_name: str | None = None
    record_type: str | None = Field(default=None, alias="type")
    name: str | None = None
    content: str | None = None
    proxied: bool | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("zone_id", "zone_name", "type", "name", "content"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                stripped = field_value.strip()
                payload[field] = stripped or None
        if isinstance(payload.get("type"), str):
            payload["type"] = payload["type"].upper()
        return payload

    @model_validator(mode="after")
    def _validate_zone_selector(self) -> "DnsRecordFilters":
        if bool(self.zone_id) == bool(self.zone_name):
            raise ValueError("exactly one of zone_id or zone_name must be provided")
        return self


class DnsRecordLookup(BaseModel):
    """Validated DNS record lookup filters."""

    zone_id: str | None = None
    zone_name: str | None = None
    record_id: str

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("zone_id", "zone_name", "record_id"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                stripped = field_value.strip()
                payload[field] = stripped or None
        return payload

    @model_validator(mode="after")
    def _validate_required(self) -> "DnsRecordLookup":
        if bool(self.zone_id) == bool(self.zone_name):
            raise ValueError("exactly one of zone_id or zone_name must be provided")
        if not self.record_id:
            raise ValueError("record_id is required")
        return self


def _build_headers(settings: CloudflareSettings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.cloudflare_api_token}",
        "Content-Type": "application/json",
    }


def _request_json(
    settings: CloudflareSettings,
    *,
    method: str,
    path: str,
    params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = requests.request(
        method=method,
        url=f"{API_BASE_URL}{path}",
        headers=_build_headers(settings),
        params=params,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )

    try:
        payload = response.json()
    except ValueError as exc:
        response.raise_for_status()
        raise CloudflareApiError("Cloudflare API returned an invalid JSON response") from exc

    if not isinstance(payload, dict):
        raise CloudflareApiError("Cloudflare API returned a non-object response")
    if payload.get("success") is not True:
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            message = ", ".join(
                error.get("message", "Cloudflare API request failed")
                for error in errors
                if isinstance(error, dict)
            )
        else:
            message = "Cloudflare API request failed"
        raise CloudflareApiError(message)
    response.raise_for_status()
    return payload


def _normalize_zone(zone: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": zone.get("id"),
        "name": zone.get("name"),
        "status": zone.get("status"),
        "paused": zone.get("paused"),
        "type": zone.get("type"),
        "created_on": zone.get("created_on"),
        "modified_on": zone.get("modified_on"),
        "name_servers": zone.get("name_servers") or [],
    }


def _normalize_record(record: Mapping[str, Any], zone_name: str | None = None) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "zone_id": record.get("zone_id"),
        "zone_name": zone_name or record.get("zone_name"),
        "name": record.get("name"),
        "type": record.get("type"),
        "content": record.get("content"),
        "proxied": record.get("proxied"),
        "ttl": record.get("ttl"),
        "comment": record.get("comment"),
        "created_on": record.get("created_on"),
        "modified_on": record.get("modified_on"),
    }


def _normalize_result_list(payload: dict[str, Any]) -> list[Mapping[str, Any]]:
    result = payload.get("result")
    if not isinstance(result, list):
        raise CloudflareApiError("Cloudflare API response did not include a result list")
    return [item for item in result if isinstance(item, Mapping)]


def _normalize_result_object(payload: dict[str, Any]) -> Mapping[str, Any]:
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise CloudflareApiError("Cloudflare API response did not include a result object")
    return result


def _resolve_zone_id(
    settings: CloudflareSettings,
    *,
    zone_id: str | None,
    zone_name: str | None,
) -> tuple[str, str | None]:
    if zone_id:
        return zone_id, zone_name

    payload = _request_json(
        settings,
        method="GET",
        path="/zones",
        params={"name": zone_name, "page": 1, "per_page": 2},
    )
    zones = _normalize_result_list(payload)
    if not zones:
        raise CloudflareApiError(f"Zone not found: {zone_name}")
    if len(zones) > 1:
        raise CloudflareApiError(f"Multiple zones matched: {zone_name}")
    zone = zones[0]
    resolved_zone_id = zone.get("id")
    if not isinstance(resolved_zone_id, str) or not resolved_zone_id:
        raise CloudflareApiError(f"Zone ID missing for zone: {zone_name}")
    resolved_zone_name = zone.get("name")
    return resolved_zone_id, resolved_zone_name if isinstance(resolved_zone_name, str) else zone_name


def list_zones(
    *,
    settings: CloudflareSettings,
    name: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """List zones visible to the configured Cloudflare token."""

    try:
        filters = ZoneFilters.model_validate(
            {"name": name, "status": status, "page": page, "per_page": per_page}
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid zone filters"
        raise ValueError(message) from exc

    params = filters.model_dump(exclude_none=True)
    payload = _request_json(settings, method="GET", path="/zones", params=params)
    zones = [_normalize_zone(zone) for zone in _normalize_result_list(payload)]
    return {
        "success": True,
        "count": len(zones),
        "filters": filters.model_dump(),
        "zones": zones,
    }


def list_dns_records(
    *,
    settings: CloudflareSettings,
    zone_id: str | None = None,
    zone_name: str | None = None,
    type: str | None = None,
    name: str | None = None,
    content: str | None = None,
    proxied: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """List DNS records for a zone."""

    try:
        filters = DnsRecordFilters.model_validate(
            {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "type": type,
                "name": name,
                "content": content,
                "proxied": proxied,
                "page": page,
                "per_page": per_page,
            }
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid DNS record filters"
        raise ValueError(message) from exc

    resolved_zone_id, resolved_zone_name = _resolve_zone_id(
        settings,
        zone_id=filters.zone_id,
        zone_name=filters.zone_name,
    )
    params: dict[str, Any] = {
        "page": filters.page,
        "per_page": filters.per_page,
    }
    if filters.record_type:
        params["type"] = filters.record_type
    if filters.name:
        params["name.exact"] = filters.name
    if filters.content:
        params["content.exact"] = filters.content
    if filters.proxied is not None:
        params["proxied"] = filters.proxied

    payload = _request_json(
        settings,
        method="GET",
        path=f"/zones/{resolved_zone_id}/dns_records",
        params=params,
    )
    records = [
        _normalize_record(record, zone_name=resolved_zone_name)
        for record in _normalize_result_list(payload)
    ]
    return {
        "success": True,
        "count": len(records),
        "filters": {
            "zone_id": resolved_zone_id,
            "zone_name": resolved_zone_name,
            "type": filters.record_type,
            "name": filters.name,
            "content": filters.content,
            "proxied": filters.proxied,
            "page": filters.page,
            "per_page": filters.per_page,
        },
        "records": records,
    }


def get_dns_record(
    *,
    settings: CloudflareSettings,
    record_id: str,
    zone_id: str | None = None,
    zone_name: str | None = None,
) -> dict[str, Any]:
    """Fetch a single DNS record by ID."""

    try:
        lookup = DnsRecordLookup.model_validate(
            {"zone_id": zone_id, "zone_name": zone_name, "record_id": record_id}
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid DNS record lookup"
        raise ValueError(message) from exc

    resolved_zone_id, resolved_zone_name = _resolve_zone_id(
        settings,
        zone_id=lookup.zone_id,
        zone_name=lookup.zone_name,
    )
    payload = _request_json(
        settings,
        method="GET",
        path=f"/zones/{resolved_zone_id}/dns_records/{lookup.record_id}",
    )
    record = _normalize_record(_normalize_result_object(payload), zone_name=resolved_zone_name)
    return {
        "success": True,
        "record": record,
    }
