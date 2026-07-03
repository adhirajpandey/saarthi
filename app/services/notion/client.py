"""Notion database helpers for MCP tools."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field, ValidationError, model_validator

from shared.settings import NotionSettings

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.notion.com/v1"
DEFAULT_TIMEOUT_SECONDS = 20
NOTION_VERSION = "2026-03-11"
_COMPACT_ID_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class NotionApiError(RuntimeError):
    """Raised when the Notion API returns an invalid or failed response."""


class DatabaseSelector(BaseModel):
    """Validated Notion database selector."""

    database_key: str

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        database_key = payload.get("database_key")
        if isinstance(database_key, str):
            payload["database_key"] = database_key.strip().lower()
        return payload

    @model_validator(mode="after")
    def _validate_database_key(self) -> "DatabaseSelector":
        if self.database_key not in {"links", "work_items", "greenhouse_experiments"}:
            raise ValueError("database_key must be one of: links, work_items, greenhouse_experiments")
        return self


class QueryFilters(DatabaseSelector):
    """Validated Notion data source query filters."""

    start_cursor: str | None = None
    page_size: int = Field(default=25, ge=1, le=100)
    project: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        value = super()._normalize(value)
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("start_cursor", "project"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                payload[field] = field_value.strip() or None
        return payload

    @model_validator(mode="after")
    def _validate_project(self) -> "QueryFilters":
        if not self.project:
            return self
        if self.database_key != "work_items":
            raise ValueError("project filtering is only supported for work_items")

        normalized_project = self.project.lower()
        project_names = {
            "all": None,
            "vidwiz": "Vidwiz",
            "trackcrow": "Trackcrow",
            "habitat": "Habitat",
        }
        if normalized_project not in project_names:
            raise ValueError("project must be one of: all, Vidwiz, Trackcrow, Habitat")
        self.project = project_names[normalized_project]
        return self


class WorkItemCreateInput(BaseModel):
    """Validated payload for creating a work item."""

    name: str
    project: str
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("name", "project", "status", "priority", "category", "description"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                payload[field] = field_value.strip() or None
        return payload

    @model_validator(mode="after")
    def _validate_fields(self) -> "WorkItemCreateInput":
        if not self.name:
            raise ValueError("name must not be empty")
        self.project = _normalize_work_item_project(self.project)
        return self


class WorkItemUpdateInput(BaseModel):
    """Validated payload for updating a work item."""

    page_id: str
    name: str | None = None
    project: str | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("page_id", "name", "project", "status", "priority", "category", "description"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                payload[field] = field_value.strip() or None
        return payload

    @model_validator(mode="after")
    def _validate_fields(self) -> "WorkItemUpdateInput":
        self.page_id = parse_page_id(self.page_id)
        if self.project:
            self.project = _normalize_work_item_project(self.project)
        if not any(
            value is not None
            for value in (
                self.name,
                self.project,
                self.status,
                self.priority,
                self.category,
                self.description,
            )
        ):
            raise ValueError("at least one field must be provided")
        return self


class GreenhouseExperimentCreateInput(BaseModel):
    """Validated payload for creating a Greenhouse experiment."""

    name: str
    status: str | None = None
    priority: str | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("name", "status", "priority", "description"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                payload[field] = field_value.strip() or None
        return payload

    @model_validator(mode="after")
    def _validate_fields(self) -> "GreenhouseExperimentCreateInput":
        if not self.name:
            raise ValueError("name must not be empty")
        return self


class GreenhouseExperimentUpdateInput(BaseModel):
    """Validated payload for updating a Greenhouse experiment."""

    page_id: str
    name: str | None = None
    status: str | None = None
    priority: str | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("page_id", "name", "status", "priority", "description"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                payload[field] = field_value.strip() or None
        return payload

    @model_validator(mode="after")
    def _validate_fields(self) -> "GreenhouseExperimentUpdateInput":
        self.page_id = parse_page_id(self.page_id)
        if not any(
            value is not None
            for value in (
                self.name,
                self.status,
                self.priority,
                self.description,
            )
        ):
            raise ValueError("at least one field must be provided")
        return self


def _build_headers(settings: NotionSettings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _request_json(
    settings: NotionSettings,
    *,
    method: str,
    path: str,
    json_body: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = requests.request(
        method=method,
        url=f"{API_BASE_URL}{path}",
        headers=_build_headers(settings),
        json=dict(json_body) if json_body is not None else None,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )

    try:
        payload = response.json()
    except ValueError as exc:
        response.raise_for_status()
        raise NotionApiError("Notion API returned an invalid JSON response") from exc

    if not isinstance(payload, dict):
        raise NotionApiError("Notion API returned a non-object response")
    if response.status_code >= 400:
        message = payload.get("message")
        code = payload.get("code")
        if isinstance(code, str) and isinstance(message, str):
            raise NotionApiError(f"{code}: {message}")
        if isinstance(message, str):
            raise NotionApiError(message)
        response.raise_for_status()
    response.raise_for_status()
    return payload


def _format_database_id(compact_id: str) -> str:
    return (
        f"{compact_id[0:8]}-{compact_id[8:12]}-{compact_id[12:16]}-"
        f"{compact_id[16:20]}-{compact_id[20:32]}"
    ).lower()


def parse_database_id(value: str) -> str:
    """Extract a Notion database ID from a raw ID or database URL."""
    candidate = value.strip()
    if _UUID_RE.fullmatch(candidate):
        return candidate.lower()
    if _COMPACT_ID_RE.fullmatch(candidate):
        return _format_database_id(candidate)

    parsed = urlparse(candidate)
    path = parsed.path if parsed.scheme and parsed.netloc else candidate
    for segment in reversed([part for part in path.split("/") if part]):
        compact_match = re.search(r"([0-9a-fA-F]{32})", segment)
        if compact_match:
            return _format_database_id(compact_match.group(1))

    raise ValueError("Notion database URL or ID did not include a 32-character database ID")


def parse_page_id(value: str) -> str:
    """Validate and normalize a Notion page ID."""
    candidate = value.strip()
    if _UUID_RE.fullmatch(candidate):
        return candidate.lower()
    if _COMPACT_ID_RE.fullmatch(candidate):
        return _format_database_id(candidate)
    raise ValueError("page_id must be a valid Notion page ID")


def _database_url_for_key(settings: NotionSettings, database_key: str) -> str:
    if database_key == "links":
        return settings.notion_links_database_url
    if database_key == "work_items":
        return settings.notion_work_items_database_url
    if database_key == "greenhouse_experiments":
        return settings.notion_greenhouse_experiments_database_url
    raise ValueError("database_key must be one of: links, work_items, greenhouse_experiments")


def _resolve_database_id(settings: NotionSettings, database_key: str) -> str:
    return parse_database_id(_database_url_for_key(settings, database_key))


def _plain_text(rich_text_items: object) -> str | None:
    if not isinstance(rich_text_items, list):
        return None
    text_parts = [
        item.get("plain_text")
        for item in rich_text_items
        if isinstance(item, Mapping) and isinstance(item.get("plain_text"), str)
    ]
    return "".join(text_parts) if text_parts else None


def _normalize_property_value(property_value: Mapping[str, Any]) -> dict[str, Any]:
    property_type = property_value.get("type")
    if not isinstance(property_type, str):
        property_type = None

    value: Any = None
    if property_type == "title":
        value = _plain_text(property_value.get("title"))
    elif property_type == "rich_text":
        value = _plain_text(property_value.get("rich_text"))
    elif property_type == "select":
        select_value = property_value.get("select")
        value = select_value.get("name") if isinstance(select_value, Mapping) else None
    elif property_type == "status":
        status_value = property_value.get("status")
        value = status_value.get("name") if isinstance(status_value, Mapping) else None
    elif property_type == "multi_select":
        multi_select = property_value.get("multi_select")
        value = [
            item.get("name")
            for item in multi_select or []
            if isinstance(item, Mapping) and isinstance(item.get("name"), str)
        ]
    elif property_type in {
        "checkbox",
        "date",
        "email",
        "files",
        "number",
        "phone_number",
        "url",
        "created_time",
        "last_edited_time",
        "created_by",
        "last_edited_by",
        "people",
        "relation",
        "rollup",
        "formula",
        "unique_id",
        "verification",
    }:
        value = property_value.get(property_type)

    return {
        "id": property_value.get("id"),
        "type": property_type,
        "value": value,
        "raw": dict(property_value),
    }


def _normalize_properties(properties: object) -> dict[str, Any]:
    if not isinstance(properties, Mapping):
        return {}
    return {
        name: _normalize_property_value(property_value)
        for name, property_value in properties.items()
        if isinstance(name, str) and isinstance(property_value, Mapping)
    }


def _normalize_page(page: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "page_id": page.get("id"),
        "url": page.get("url"),
        "created_time": page.get("created_time"),
        "last_edited_time": page.get("last_edited_time"),
        "archived": page.get("archived"),
        "in_trash": page.get("in_trash"),
        "properties": _normalize_properties(page.get("properties")),
    }


def _normalize_work_item_project(value: str | None) -> str:
    if not value:
        raise ValueError("project must be one of: Vidwiz, Trackcrow, Habitat")
    project_names = {
        "vidwiz": "Vidwiz",
        "trackcrow": "Trackcrow",
        "habitat": "Habitat",
    }
    normalized_value = value.lower()
    if normalized_value not in project_names:
        raise ValueError("project must be one of: Vidwiz, Trackcrow, Habitat")
    return project_names[normalized_value]


def _build_title_property(value: str) -> dict[str, Any]:
    return {
        "title": [
            {
                "type": "text",
                "text": {"content": value},
            }
        ]
    }


def _build_rich_text_property(value: str) -> dict[str, Any]:
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": value},
            }
        ]
    }


def _build_select_property(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


def _build_status_property(value: str) -> dict[str, Any]:
    return {"status": {"name": value}}


def _build_property_value(property_type: str, value: str) -> dict[str, Any]:
    if property_type == "title":
        return _build_title_property(value)
    if property_type == "rich_text":
        return _build_rich_text_property(value)
    if property_type == "select":
        return _build_select_property(value)
    if property_type == "status":
        return _build_status_property(value)
    raise NotionApiError(f"Unsupported Notion property type for writes: {property_type}")


def _build_work_item_properties(
    schema_properties: Mapping[str, Any],
    *,
    name: str | None = None,
    project: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    field_values = {
        "Name": name,
        "Project": project,
        "Status": status,
        "Priority": priority,
        "Category": category,
        "Description": description,
    }
    properties: dict[str, Any] = {}
    for property_name, value in field_values.items():
        if value is None:
            continue
        property_schema = schema_properties.get(property_name)
        if not isinstance(property_schema, Mapping):
            raise NotionApiError(f"Notion data source is missing expected property: {property_name}")
        property_type = property_schema.get("type")
        if not isinstance(property_type, str) or not property_type:
            raise NotionApiError(
                f"Notion data source property has invalid type metadata: {property_name}"
            )
        properties[property_name] = _build_property_value(property_type, value)
    return properties


def _build_greenhouse_experiment_properties(
    schema_properties: Mapping[str, Any],
    *,
    name: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    field_values = {
        "Name": name,
        "Status": status,
        "Priority": priority,
        "Description": description,
    }
    properties: dict[str, Any] = {}
    for property_name, value in field_values.items():
        if value is None:
            continue
        property_schema = schema_properties.get(property_name)
        if not isinstance(property_schema, Mapping):
            raise NotionApiError(f"Notion data source is missing expected property: {property_name}")
        property_type = property_schema.get("type")
        if not isinstance(property_type, str) or not property_type:
            raise NotionApiError(
                f"Notion data source property has invalid type metadata: {property_name}"
            )
        properties[property_name] = _build_property_value(property_type, value)
    return properties


def _resolve_data_source(
    settings: NotionSettings,
    *,
    database_id: str,
) -> Mapping[str, Any]:
    database = _request_json(settings, method="GET", path=f"/databases/{database_id}")
    data_sources = database.get("data_sources")
    if not isinstance(data_sources, list):
        data_sources = []
    if len(data_sources) != 1:
        raise NotionApiError(
            f"Expected exactly one Notion data source for database {database_id}; "
            f"found {len(data_sources)}"
        )
    data_source = data_sources[0]
    if not isinstance(data_source, Mapping):
        raise NotionApiError(f"Notion data source reference is invalid for database {database_id}")
    data_source_id = data_source.get("id")
    if not isinstance(data_source_id, str) or not data_source_id:
        raise NotionApiError(f"Notion data source ID missing for database {database_id}")
    return data_source


def _get_data_source_properties(
    settings: NotionSettings,
    *,
    data_source_id: str,
) -> Mapping[str, Any]:
    schema = _request_json(settings, method="GET", path=f"/data_sources/{data_source_id}")
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise NotionApiError("Notion data source response did not include properties")
    return properties


def _query_data_source(
    settings: NotionSettings,
    *,
    data_source_id: str,
    start_cursor: str | None = None,
    page_size: int = 25,
    project: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"page_size": page_size}
    if start_cursor:
        body["start_cursor"] = start_cursor
    if project:
        body["filter"] = {
            "property": "Project",
            "select": {"equals": project},
        }
    return _request_json(
        settings,
        method="POST",
        path=f"/data_sources/{data_source_id}/query",
        json_body=body,
    )


def _query_all_data_source_pages(
    settings: NotionSettings,
    *,
    data_source_id: str,
) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload = _query_data_source(
            settings,
            data_source_id=data_source_id,
            start_cursor=cursor,
            page_size=100,
        )
        results = payload.get("results")
        if not isinstance(results, list):
            raise NotionApiError("Notion data source query response did not include results")
        pages.extend(item for item in results if isinstance(item, Mapping))
        if not payload.get("has_more"):
            break
        next_cursor = payload.get("next_cursor")
        if not isinstance(next_cursor, str) or not next_cursor:
            raise NotionApiError("Notion data source query returned has_more without next_cursor")
        cursor = next_cursor
    return [_normalize_page(item) for item in pages]


def get_database_schema(
    *,
    settings: NotionSettings,
    database_key: str,
) -> dict[str, Any]:
    """Retrieve schema metadata for a configured Notion database."""
    try:
        selector = DatabaseSelector.model_validate({"database_key": database_key})
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid Notion database selector"
        raise ValueError(message) from exc

    database_id = _resolve_database_id(settings, selector.database_key)
    data_source = _resolve_data_source(settings, database_id=database_id)
    data_source_id = data_source["id"]
    schema = _request_json(settings, method="GET", path=f"/data_sources/{data_source_id}")
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise NotionApiError("Notion data source response did not include properties")

    return {
        "success": True,
        "database_key": selector.database_key,
        "database_id": database_id,
        "data_source_id": data_source_id,
        "properties": dict(properties),
    }


def query_database(
    *,
    settings: NotionSettings,
    database_key: str,
    start_cursor: str | None = None,
    page_size: int = 25,
    project: str | None = None,
) -> dict[str, Any]:
    """Query rows from a configured Notion database."""
    try:
        filters = QueryFilters.model_validate(
            {
                "database_key": database_key,
                "start_cursor": start_cursor,
                "page_size": page_size,
                "project": project,
            }
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid Notion database query"
        raise ValueError(message) from exc

    database_id = _resolve_database_id(settings, filters.database_key)
    data_source = _resolve_data_source(settings, database_id=database_id)
    data_source_id = data_source["id"]
    payload = _query_data_source(
        settings,
        data_source_id=data_source_id,
        start_cursor=filters.start_cursor,
        page_size=filters.page_size,
        project=filters.project,
    )
    results = payload.get("results")
    if not isinstance(results, list):
        raise NotionApiError("Notion data source query response did not include results")
    pages = [_normalize_page(item) for item in results if isinstance(item, Mapping)]

    return {
        "success": True,
        "count": len(pages),
        "filters": {
            "database_key": filters.database_key,
            "database_id": database_id,
            "data_source_id": data_source_id,
            "start_cursor": filters.start_cursor,
            "page_size": filters.page_size,
            "project": filters.project or "all",
        },
        "has_more": payload.get("has_more"),
        "next_cursor": payload.get("next_cursor"),
        "pages": pages,
    }


def list_work_item_projects(
    *,
    settings: NotionSettings,
) -> dict[str, Any]:
    """List project names that currently have Notion work items, with item counts."""
    database_id = _resolve_database_id(settings, "work_items")
    data_source = _resolve_data_source(settings, database_id=database_id)
    data_source_id = data_source["id"]
    pages = _query_all_data_source_pages(settings, data_source_id=data_source_id)

    project_counts: dict[str, int] = {}
    known_projects = {"Vidwiz", "Trackcrow", "Habitat"}
    for page in pages:
        project_value = page["properties"].get("Project", {}).get("value")
        if isinstance(project_value, str) and project_value in known_projects:
            project_counts[project_value] = project_counts.get(project_value, 0) + 1

    projects = [
        {"name": name, "work_item_count": project_counts[name]}
        for name in sorted(project_counts)
    ]
    return {
        "success": True,
        "count": len(projects),
        "projects": projects,
    }


def create_work_item(
    *,
    settings: NotionSettings,
    name: str,
    project: str,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create one page in the configured Notion work items data source."""
    try:
        payload = WorkItemCreateInput.model_validate(
            {
                "name": name,
                "project": project,
                "status": status,
                "priority": priority,
                "category": category,
                "description": description,
            }
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid work item create payload"
        raise ValueError(message) from exc

    database_id = _resolve_database_id(settings, "work_items")
    data_source = _resolve_data_source(settings, database_id=database_id)
    data_source_id = data_source["id"]
    schema_properties = _get_data_source_properties(settings, data_source_id=data_source_id)
    page = _request_json(
        settings,
        method="POST",
        path="/pages",
        json_body={
            "parent": {"data_source_id": data_source_id},
            "properties": _build_work_item_properties(
                schema_properties,
                name=payload.name,
                project=payload.project,
                status=payload.status,
                priority=payload.priority,
                category=payload.category,
                description=payload.description,
            ),
        },
    )
    return {
        "success": True,
        "page": _normalize_page(page),
    }


def update_work_item(
    *,
    settings: NotionSettings,
    page_id: str,
    name: str | None = None,
    project: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Patch properties on one existing Notion work item page."""
    try:
        payload = WorkItemUpdateInput.model_validate(
            {
                "page_id": page_id,
                "name": name,
                "project": project,
                "status": status,
                "priority": priority,
                "category": category,
                "description": description,
            }
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid work item update payload"
        raise ValueError(message) from exc

    database_id = _resolve_database_id(settings, "work_items")
    data_source = _resolve_data_source(settings, database_id=database_id)
    data_source_id = data_source["id"]
    schema_properties = _get_data_source_properties(settings, data_source_id=data_source_id)
    page = _request_json(
        settings,
        method="PATCH",
        path=f"/pages/{payload.page_id}",
        json_body={
            "properties": _build_work_item_properties(
                schema_properties,
                name=payload.name,
                project=payload.project,
                status=payload.status,
                priority=payload.priority,
                category=payload.category,
                description=payload.description,
            )
        },
    )
    return {
        "success": True,
        "page": _normalize_page(page),
    }


def create_greenhouse_experiment(
    *,
    settings: NotionSettings,
    name: str,
    status: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create one page in the configured Greenhouse experiments data source."""
    try:
        payload = GreenhouseExperimentCreateInput.model_validate(
            {
                "name": name,
                "status": status,
                "priority": priority,
                "description": description,
            }
        )
    except ValidationError as exc:
        message = (
            exc.errors()[0]["msg"] if exc.errors() else "invalid Greenhouse experiment create payload"
        )
        raise ValueError(message) from exc

    database_id = _resolve_database_id(settings, "greenhouse_experiments")
    data_source = _resolve_data_source(settings, database_id=database_id)
    data_source_id = data_source["id"]
    schema_properties = _get_data_source_properties(settings, data_source_id=data_source_id)
    page = _request_json(
        settings,
        method="POST",
        path="/pages",
        json_body={
            "parent": {"data_source_id": data_source_id},
            "properties": _build_greenhouse_experiment_properties(
                schema_properties,
                name=payload.name,
                status=payload.status,
                priority=payload.priority,
                description=payload.description,
            ),
        },
    )
    return {
        "success": True,
        "page": _normalize_page(page),
    }


def update_greenhouse_experiment(
    *,
    settings: NotionSettings,
    page_id: str,
    name: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Patch properties on one existing Greenhouse experiment page."""
    try:
        payload = GreenhouseExperimentUpdateInput.model_validate(
            {
                "page_id": page_id,
                "name": name,
                "status": status,
                "priority": priority,
                "description": description,
            }
        )
    except ValidationError as exc:
        message = (
            exc.errors()[0]["msg"] if exc.errors() else "invalid Greenhouse experiment update payload"
        )
        raise ValueError(message) from exc

    database_id = _resolve_database_id(settings, "greenhouse_experiments")
    data_source = _resolve_data_source(settings, database_id=database_id)
    data_source_id = data_source["id"]
    schema_properties = _get_data_source_properties(settings, data_source_id=data_source_id)
    page = _request_json(
        settings,
        method="PATCH",
        path=f"/pages/{payload.page_id}",
        json_body={
            "properties": _build_greenhouse_experiment_properties(
                schema_properties,
                name=payload.name,
                status=payload.status,
                priority=payload.priority,
                description=payload.description,
            )
        },
    )
    return {
        "success": True,
        "page": _normalize_page(page),
    }
