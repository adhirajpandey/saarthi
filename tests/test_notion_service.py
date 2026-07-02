"""Tests for Notion service helpers."""

from __future__ import annotations

import pytest

from app.services.notion.client import (
    NOTION_VERSION,
    NotionApiError,
    create_work_item,
    get_database_schema,
    list_work_item_projects,
    parse_database_id,
    query_database,
    update_work_item,
)
from shared.settings import get_notion_settings


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


def test_parse_database_id_accepts_raw_id_and_database_url() -> None:
    assert (
        parse_database_id("11111111111111111111111111111111")
        == "11111111-1111-1111-1111-111111111111"
    )
    assert (
        parse_database_id("11111111-1111-1111-1111-111111111111")
        == "11111111-1111-1111-1111-111111111111"
    )
    assert (
        parse_database_id(
            "https://www.notion.so/workspace/Links-11111111111111111111111111111111?pvs=4"
        )
        == "11111111-1111-1111-1111-111111111111"
    )


def test_parse_database_id_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="32-character database ID"):
        parse_database_id("https://www.notion.so/workspace/Links")


def test_get_database_schema_resolves_single_data_source(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/databases/11111111-1111-1111-1111-111111111111"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "11111111-1111-1111-1111-111111111111",
                    "data_sources": [{"id": "data-source-1", "name": "Links"}],
                }
            )
        return _FakeResponse(
            {
                "object": "data_source",
                "id": "data-source-1",
                "properties": {
                    "Name": {"id": "title", "type": "title", "title": {}},
                    "URL": {"id": "url", "type": "url", "url": {}},
                },
            }
        )

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    result = get_database_schema(settings=settings, database_key="links")

    assert result["success"] is True
    assert result["database_key"] == "links"
    assert result["data_source_id"] == "data-source-1"
    assert result["properties"]["URL"]["type"] == "url"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-notion-token"
    assert calls[0]["headers"]["Notion-Version"] == NOTION_VERSION
    assert calls[0]["timeout"] == 20


def test_get_database_schema_rejects_multiple_data_sources(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()

    monkeypatch.setattr(
        "app.services.notion.client.requests.request",
        lambda **_kwargs: _FakeResponse(
            {
                "object": "database",
                "data_sources": [{"id": "one"}, {"id": "two"}],
            }
        ),
    )

    with pytest.raises(NotionApiError, match="Expected exactly one Notion data source"):
        get_database_schema(settings=settings, database_key="links")


def test_query_database_posts_pagination_and_normalizes_pages(
    monkeypatch, runtime_config
) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/databases/22222222-2222-2222-2222-222222222222"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "22222222-2222-2222-2222-222222222222",
                    "data_sources": [{"id": "work-data-source"}],
                }
            )
        return _FakeResponse(
            {
                "object": "list",
                "has_more": True,
                "next_cursor": "next-page",
                "results": [
                    {
                        "id": "page-1",
                        "url": "https://notion.so/page-1",
                        "created_time": "2026-07-01T00:00:00.000Z",
                        "last_edited_time": "2026-07-02T00:00:00.000Z",
                        "archived": False,
                        "in_trash": False,
                        "properties": {
                            "Task": {
                                "id": "title",
                                "type": "title",
                                "title": [{"plain_text": "Ship Notion MCP"}],
                            },
                            "Project": {
                                "id": "project",
                                "type": "select",
                                "select": {"name": "Habitat"},
                            },
                            "Tags": {
                                "id": "tags",
                                "type": "multi_select",
                                "multi_select": [{"name": "backend"}, {"name": "mcp"}],
                            },
                            "Done": {"id": "done", "type": "checkbox", "checkbox": False},
                        },
                    }
                ],
            }
        )

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    result = query_database(
        settings=settings,
        database_key="work_items",
        start_cursor="cursor-1",
        page_size=5,
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["filters"]["database_key"] == "work_items"
    assert result["has_more"] is True
    assert result["next_cursor"] == "next-page"
    assert result["pages"][0]["properties"]["Task"]["value"] == "Ship Notion MCP"
    assert result["pages"][0]["properties"]["Project"]["value"] == "Habitat"
    assert result["pages"][0]["properties"]["Tags"]["value"] == ["backend", "mcp"]
    assert result["pages"][0]["properties"]["Done"]["value"] is False
    assert calls[1]["method"] == "POST"
    assert calls[1]["url"].endswith("/data_sources/work-data-source/query")
    assert calls[1]["json"] == {"page_size": 5, "start_cursor": "cursor-1"}


def test_query_database_applies_project_filter_for_work_items(
    monkeypatch, runtime_config
) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/databases/22222222-2222-2222-2222-222222222222"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "22222222-2222-2222-2222-222222222222",
                    "data_sources": [{"id": "work-data-source"}],
                }
            )
        return _FakeResponse({"object": "list", "has_more": False, "next_cursor": None, "results": []})

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    result = query_database(
        settings=settings,
        database_key="work_items",
        project="habitat",
    )

    assert result["filters"]["project"] == "Habitat"
    assert calls[1]["json"] == {
        "page_size": 25,
        "filter": {"property": "Project", "select": {"equals": "Habitat"}},
    }


def test_query_database_omits_filter_for_all_projects(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/databases/22222222-2222-2222-2222-222222222222"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "22222222-2222-2222-2222-222222222222",
                    "data_sources": [{"id": "work-data-source"}],
                }
            )
        return _FakeResponse({"object": "list", "has_more": False, "next_cursor": None, "results": []})

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    result = query_database(
        settings=settings,
        database_key="work_items",
        project="all",
    )

    assert result["filters"]["project"] == "all"
    assert calls[1]["json"] == {"page_size": 25}


def test_query_database_validates_database_key(runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()

    with pytest.raises(ValueError, match="database_key must be one of"):
        query_database(settings=settings, database_key="unknown")


def test_query_database_caps_page_size(runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()

    with pytest.raises(ValueError, match="less than or equal to 100"):
        query_database(settings=settings, database_key="links", page_size=101)


def test_query_database_rejects_invalid_project(runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()

    with pytest.raises(ValueError, match="project must be one of"):
        query_database(settings=settings, database_key="work_items", project="vidcraft")


def test_query_database_rejects_project_filter_for_links(runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()

    with pytest.raises(ValueError, match="only supported for work_items"):
        query_database(settings=settings, database_key="links", project="Habitat")


def test_create_work_item_posts_expected_properties(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/databases/22222222-2222-2222-2222-222222222222"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "22222222-2222-2222-2222-222222222222",
                    "data_sources": [{"id": "work-data-source"}],
                }
            )
        if kwargs["url"].endswith("/data_sources/work-data-source"):
            return _FakeResponse(
                {
                    "object": "data_source",
                    "id": "work-data-source",
                    "properties": {
                        "Name": {"id": "title", "type": "title"},
                        "Project": {"id": "project", "type": "select"},
                        "Status": {"id": "status", "type": "select"},
                        "Priority": {"id": "priority", "type": "select"},
                        "Category": {"id": "category", "type": "select"},
                        "Description": {"id": "description", "type": "rich_text"},
                    },
                }
            )
        return _FakeResponse(
            {
                "id": "page-1",
                "url": "https://notion.so/page-1",
                "created_time": "2026-07-01T00:00:00.000Z",
                "last_edited_time": "2026-07-02T00:00:00.000Z",
                "archived": False,
                "in_trash": False,
                "properties": {
                    "Name": {
                        "id": "title",
                        "type": "title",
                        "title": [{"plain_text": "Ship Notion writes"}],
                    },
                    "Project": {
                        "id": "project",
                        "type": "select",
                        "select": {"name": "Habitat"},
                    },
                    "Status": {
                        "id": "status",
                        "type": "status",
                        "status": {"name": "Pending"},
                    },
                    "Priority": {
                        "id": "priority",
                        "type": "select",
                        "select": {"name": "High"},
                    },
                    "Category": {
                        "id": "category",
                        "type": "select",
                        "select": {"name": "Backend"},
                    },
                    "Description": {
                        "id": "description",
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "MCP write path"}],
                    },
                },
            }
        )

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    result = create_work_item(
        settings=settings,
        name="Ship Notion writes",
        project="habitat",
        status="Pending",
        priority="High",
        category="Backend",
        description="MCP write path",
    )

    assert result["success"] is True
    assert result["page"]["properties"]["Name"]["value"] == "Ship Notion writes"
    assert result["page"]["properties"]["Project"]["value"] == "Habitat"
    assert calls[2]["method"] == "POST"
    assert calls[2]["url"].endswith("/pages")
    assert calls[2]["json"] == {
        "parent": {"data_source_id": "work-data-source"},
        "properties": {
            "Name": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "Ship Notion writes"},
                    }
                ]
            },
            "Project": {"select": {"name": "Habitat"}},
            "Status": {"select": {"name": "Pending"}},
            "Priority": {"select": {"name": "High"}},
            "Category": {"select": {"name": "Backend"}},
            "Description": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "MCP write path"},
                    }
                ]
            },
        },
    }


def test_update_work_item_patches_only_provided_fields(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/databases/22222222-2222-2222-2222-222222222222"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "22222222-2222-2222-2222-222222222222",
                    "data_sources": [{"id": "work-data-source"}],
                }
            )
        if kwargs["url"].endswith("/data_sources/work-data-source"):
            return _FakeResponse(
                {
                    "object": "data_source",
                    "id": "work-data-source",
                    "properties": {
                        "Name": {"id": "title", "type": "title"},
                        "Project": {"id": "project", "type": "select"},
                        "Status": {"id": "status", "type": "select"},
                        "Priority": {"id": "priority", "type": "select"},
                        "Category": {"id": "category", "type": "select"},
                        "Description": {"id": "description", "type": "rich_text"},
                    },
                }
            )
        return _FakeResponse(
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "url": "https://notion.so/page-1",
                "created_time": "2026-07-01T00:00:00.000Z",
                "last_edited_time": "2026-07-02T00:00:00.000Z",
                "archived": False,
                "in_trash": False,
                "properties": {
                    "Name": {
                        "id": "title",
                        "type": "title",
                        "title": [{"plain_text": "Ship Notion writes"}],
                    },
                    "Status": {
                        "id": "status",
                        "type": "status",
                        "status": {"name": "In Progress"},
                    },
                    "Description": {
                        "id": "description",
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "Updated copy"}],
                    },
                },
            }
        )

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    result = update_work_item(
        settings=settings,
        page_id="33333333-3333-3333-3333-333333333333",
        status="In Progress",
        description="Updated copy",
    )

    assert result["success"] is True
    assert result["page"]["properties"]["Status"]["value"] == "In Progress"
    assert calls[2]["method"] == "PATCH"
    assert calls[2]["url"].endswith("/pages/33333333-3333-3333-3333-333333333333")
    assert calls[2]["json"] == {
        "properties": {
            "Status": {"select": {"name": "In Progress"}},
            "Description": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "Updated copy"},
                    }
                ]
            },
        }
    }


def test_update_work_item_rejects_invalid_page_id(runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()

    with pytest.raises(ValueError, match="page_id must be a valid Notion page ID"):
        update_work_item(settings=settings, page_id="invalid-page-id", status="Done")


def test_update_work_item_requires_at_least_one_field(runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()

    with pytest.raises(ValueError, match="at least one field must be provided"):
        update_work_item(
            settings=settings,
            page_id="33333333-3333-3333-3333-333333333333",
        )


def test_create_work_item_surfaces_notion_api_errors(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls = {"count": 0}

    def _fake_request(**kwargs):
        calls["count"] += 1
        if kwargs["url"].endswith("/databases/22222222-2222-2222-2222-222222222222"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "22222222-2222-2222-2222-222222222222",
                    "data_sources": [{"id": "work-data-source"}],
                }
            )
        if kwargs["url"].endswith("/data_sources/work-data-source"):
            return _FakeResponse(
                {
                    "object": "data_source",
                    "id": "work-data-source",
                    "properties": {
                        "Name": {"id": "title", "type": "title"},
                        "Project": {"id": "project", "type": "select"},
                        "Status": {"id": "status", "type": "select"},
                        "Priority": {"id": "priority", "type": "select"},
                        "Category": {"id": "category", "type": "select"},
                        "Description": {"id": "description", "type": "rich_text"},
                    },
                }
            )
        return _FakeResponse(
            {
                "object": "error",
                "code": "validation_error",
                "message": "Status is invalid.",
            },
            status_code=400,
        )

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    with pytest.raises(NotionApiError, match="validation_error: Status is invalid"):
        create_work_item(
            settings=settings,
            name="Ship Notion writes",
            project="Habitat",
            status="Nope",
        )

    assert calls["count"] == 3


def test_list_work_item_projects_returns_projects_with_counts(
    monkeypatch, runtime_config
) -> None:
    runtime_config()
    settings = get_notion_settings()
    calls: list[dict[str, object]] = []

    def _fake_request(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/databases/22222222-2222-2222-2222-222222222222"):
            return _FakeResponse(
                {
                    "object": "database",
                    "id": "22222222-2222-2222-2222-222222222222",
                    "data_sources": [{"id": "work-data-source"}],
                }
            )
        if kwargs["url"].endswith("/data_sources/work-data-source/query") and kwargs["json"] == {
            "page_size": 100
        }:
            return _FakeResponse(
                {
                    "object": "list",
                    "has_more": True,
                    "next_cursor": "cursor-2",
                    "results": [
                        {
                            "id": "page-1",
                            "url": "https://notion.so/page-1",
                            "created_time": "2026-07-01T00:00:00.000Z",
                            "last_edited_time": "2026-07-02T00:00:00.000Z",
                            "archived": False,
                            "in_trash": False,
                            "properties": {
                                "Project": {
                                    "id": "project",
                                    "type": "select",
                                    "select": {"name": "Habitat"},
                                }
                            },
                        },
                        {
                            "id": "page-2",
                            "url": "https://notion.so/page-2",
                            "created_time": "2026-07-01T00:00:00.000Z",
                            "last_edited_time": "2026-07-02T00:00:00.000Z",
                            "archived": False,
                            "in_trash": False,
                            "properties": {
                                "Project": {
                                    "id": "project",
                                    "type": "select",
                                    "select": {"name": "Trackcrow"},
                                }
                            },
                        },
                    ],
                }
            )
        return _FakeResponse(
            {
                "object": "list",
                "has_more": False,
                "next_cursor": None,
                "results": [
                    {
                        "id": "page-3",
                        "url": "https://notion.so/page-3",
                        "created_time": "2026-07-01T00:00:00.000Z",
                        "last_edited_time": "2026-07-02T00:00:00.000Z",
                        "archived": False,
                        "in_trash": False,
                        "properties": {
                            "Project": {
                                "id": "project",
                                "type": "select",
                                "select": {"name": "Habitat"},
                            }
                        },
                    },
                    {
                        "id": "page-4",
                        "url": "https://notion.so/page-4",
                        "created_time": "2026-07-01T00:00:00.000Z",
                        "last_edited_time": "2026-07-02T00:00:00.000Z",
                        "archived": False,
                        "in_trash": False,
                        "properties": {},
                    },
                ],
            }
        )

    monkeypatch.setattr("app.services.notion.client.requests.request", _fake_request)

    result = list_work_item_projects(settings=settings)

    assert result == {
        "success": True,
        "count": 2,
        "projects": [
            {"name": "Habitat", "work_item_count": 2},
            {"name": "Trackcrow", "work_item_count": 1},
        ],
    }
    assert calls[1]["json"] == {"page_size": 100}
    assert calls[2]["json"] == {"page_size": 100, "start_cursor": "cursor-2"}


def test_notion_api_failure_raises_clear_error(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_notion_settings()
    response = _FakeResponse(
        {
            "object": "error",
            "code": "unauthorized",
            "message": "API token is invalid.",
        },
        status_code=401,
    )

    monkeypatch.setattr(
        "app.services.notion.client.requests.request",
        lambda **_kwargs: response,
    )

    with pytest.raises(NotionApiError, match="unauthorized: API token is invalid"):
        get_database_schema(settings=settings, database_key="links")

    assert response.raise_for_status_called is False
