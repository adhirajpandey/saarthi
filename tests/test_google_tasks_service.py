"""Tests for Google Tasks service helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.google_tasks.client import (
    GoogleTasksApiError,
    get_task,
    list_tasklists,
    list_tasks,
    run_oauth_bootstrap,
)
from shared.settings import get_google_tasks_settings


class _FakeExecute:
    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class _FakeTasklistsResource:
    def __init__(self, items):
        self.items = items
        self.calls: list[dict[str, object]] = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeExecute({"items": self.items, "nextPageToken": "next-token"})


class _FakeTasksResource:
    def __init__(self, items=None, item=None):
        self.items = items or []
        self.item = item or {}
        self.list_calls: list[dict[str, object]] = []
        self.get_calls: list[dict[str, object]] = []

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return _FakeExecute({"items": self.items, "nextPageToken": "task-token"})

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        return _FakeExecute(self.item)


class _FakeService:
    def __init__(self, tasklists_resource, tasks_resource):
        self._tasklists_resource = tasklists_resource
        self._tasks_resource = tasks_resource
        self.closed = False

    def tasklists(self):
        return self._tasklists_resource

    def tasks(self):
        return self._tasks_resource

    def close(self) -> None:
        self.closed = True


class _FakeCredentials:
    def __init__(self, token_json: str) -> None:
        self.valid = True
        self.expired = False
        self.refresh_token = "refresh-token"
        self._token_json = token_json

    def to_json(self) -> str:
        return self._token_json


def test_list_tasklists_normalizes_response(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_google_tasks_settings()
    tasklists_resource = _FakeTasklistsResource(
        [
            {
                "id": "list-1",
                "title": "Personal",
                "updated": "2026-06-01T00:00:00.000Z",
                "selfLink": "https://example.com/list-1",
            }
        ]
    )
    service = _FakeService(tasklists_resource, _FakeTasksResource())

    monkeypatch.setattr(
        "app.services.google_tasks.client._build_tasks_service",
        lambda _settings: service,
    )

    result = list_tasklists(settings=settings, max_results=5)

    assert result["success"] is True
    assert result["count"] == 1
    assert result["filters"] == {"page_token": None, "max_results": 5}
    assert result["next_page_token"] == "next-token"
    assert result["tasklists"][0]["self_link"] == "https://example.com/list-1"
    assert tasklists_resource.calls[0] == {"maxResults": 5}
    assert service.closed is True


def test_list_tasks_resolves_tasklist_title_and_normalizes_response(
    monkeypatch, runtime_config
) -> None:
    runtime_config()
    settings = get_google_tasks_settings()
    tasklists_resource = _FakeTasklistsResource([{"id": "list-1", "title": "Personal"}])
    tasks_resource = _FakeTasksResource(
        items=[
            {
                "id": "task-1",
                "title": "Buy milk",
                "status": "needsAction",
                "notes": "2 liters",
                "due": "2026-06-14T00:00:00.000Z",
                "completed": None,
                "updated": "2026-06-13T00:00:00.000Z",
                "deleted": False,
                "hidden": False,
                "parent": "parent-1",
                "position": "0001",
                "webViewLink": "https://tasks.google.com/task-1",
                "selfLink": "https://example.com/task-1",
                "links": [{"type": "email", "link": "mailto:test@example.com"}],
                "assignmentInfo": {"surfaceType": "DOCS"},
            }
        ]
    )
    service = _FakeService(tasklists_resource, tasks_resource)

    monkeypatch.setattr(
        "app.services.google_tasks.client._build_tasks_service",
        lambda _settings: service,
    )

    result = list_tasks(
        settings=settings,
        tasklist_title="Personal",
        max_results=5,
        show_completed=False,
        show_hidden=True,
        show_deleted=True,
        show_assigned=True,
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["filters"]["tasklist_id"] == "list-1"
    assert result["filters"]["tasklist_title"] == "Personal"
    assert result["next_page_token"] == "task-token"
    assert result["tasks"][0]["web_view_link"] == "https://tasks.google.com/task-1"
    assert result["tasks"][0]["assignment_info"] == {"surfaceType": "DOCS"}
    assert tasks_resource.list_calls[0] == {
        "tasklist": "list-1",
        "maxResults": 5,
        "showCompleted": False,
        "showHidden": True,
        "showDeleted": True,
        "showAssigned": True,
    }
    assert service.closed is True


def test_get_task_uses_tasklist_id_without_lookup(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_google_tasks_settings()
    tasks_resource = _FakeTasksResource(
        item={
            "id": "task-1",
            "title": "Buy milk",
            "status": "completed",
            "selfLink": "https://example.com/task-1",
        }
    )
    service = _FakeService(_FakeTasklistsResource([]), tasks_resource)

    monkeypatch.setattr(
        "app.services.google_tasks.client._build_tasks_service",
        lambda _settings: service,
    )

    result = get_task(settings=settings, task_id="task-1", tasklist_id="list-1")

    assert result["success"] is True
    assert result["task"]["id"] == "task-1"
    assert tasks_resource.get_calls[0] == {"tasklist": "list-1", "task": "task-1"}
    assert service.closed is True


def test_list_tasks_requires_exactly_one_tasklist_selector(runtime_config) -> None:
    runtime_config()
    settings = get_google_tasks_settings()

    with pytest.raises(ValueError, match="exactly one of tasklist_id or tasklist_title"):
        list_tasks(settings=settings, tasklist_id="list-1", tasklist_title="Personal")


def test_get_task_requires_task_id(runtime_config) -> None:
    runtime_config()
    settings = get_google_tasks_settings()

    with pytest.raises(ValueError, match="task_id is required"):
        get_task(settings=settings, task_id=" ", tasklist_id="list-1")


def test_list_tasks_raises_for_missing_tasklist_title(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_google_tasks_settings()
    service = _FakeService(_FakeTasklistsResource([]), _FakeTasksResource())

    monkeypatch.setattr(
        "app.services.google_tasks.client._build_tasks_service",
        lambda _settings: service,
    )

    with pytest.raises(GoogleTasksApiError, match="Task list not found: Personal"):
        list_tasks(settings=settings, tasklist_title="Personal")


def test_list_tasks_raises_for_ambiguous_tasklist_title(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_google_tasks_settings()
    service = _FakeService(
        _FakeTasklistsResource(
            [{"id": "list-1", "title": "Personal"}, {"id": "list-2", "title": "Personal"}]
        ),
        _FakeTasksResource(),
    )

    monkeypatch.setattr(
        "app.services.google_tasks.client._build_tasks_service",
        lambda _settings: service,
    )

    with pytest.raises(GoogleTasksApiError, match="Multiple task lists matched: Personal"):
        list_tasks(settings=settings, tasklist_title="Personal")


def test_list_tasklists_wraps_google_api_errors(monkeypatch, runtime_config) -> None:
    runtime_config()
    settings = get_google_tasks_settings()

    def _raise(_settings):
        raise RuntimeError("google boom")

    monkeypatch.setattr("app.services.google_tasks.client._build_tasks_service", _raise)

    with pytest.raises(GoogleTasksApiError, match="google boom"):
        list_tasklists(settings=settings)


def test_list_tasklists_raises_for_missing_token_file(monkeypatch, runtime_config, test_workspace: Path) -> None:
    runtime_config()
    token_path = test_workspace / "missing-token.json"
    monkeypatch.setenv("GOOGLE_TASKS_TOKEN_PATH", str(token_path))
    settings = get_google_tasks_settings()

    with pytest.raises(GoogleTasksApiError, match="Google Tasks token file not found"):
        list_tasklists(settings=settings)


def test_run_oauth_bootstrap_writes_token_file_atomically(
    monkeypatch, runtime_config, test_workspace: Path
) -> None:
    runtime_config()
    token_path = test_workspace / "google-token.json"
    monkeypatch.setenv("GOOGLE_TASKS_TOKEN_PATH", str(token_path))
    settings = get_google_tasks_settings()
    credentials = _FakeCredentials(
        json.dumps(
            {
                "token": "access-token",
                "refresh_token": "refresh-token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test-google-client-id",
                "client_secret": "test-google-client-secret",
                "scopes": ["https://www.googleapis.com/auth/tasks.readonly"],
            }
        )
    )

    monkeypatch.setattr(
        "app.services.google_tasks.client._run_local_oauth_flow",
        lambda _settings: credentials,
    )

    result = run_oauth_bootstrap(settings=settings)

    assert result == token_path
    assert json.loads(token_path.read_text(encoding="utf-8"))["refresh_token"] == "refresh-token"


def test_run_oauth_bootstrap_preserves_existing_token_file_on_failure(
    monkeypatch, runtime_config, test_workspace: Path
) -> None:
    runtime_config()
    token_path = test_workspace / "google-token.json"
    token_path.write_text('{"refresh_token":"existing"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_TASKS_TOKEN_PATH", str(token_path))
    settings = get_google_tasks_settings()

    monkeypatch.setattr(
        "app.services.google_tasks.client._run_local_oauth_flow",
        lambda _settings: (_ for _ in ()).throw(RuntimeError("oauth failed")),
    )

    with pytest.raises(RuntimeError, match="oauth failed"):
        run_oauth_bootstrap(settings=settings)

    assert json.loads(token_path.read_text(encoding="utf-8"))["refresh_token"] == "existing"


def test_run_oauth_bootstrap_headless_writes_token_file(
    monkeypatch, runtime_config, test_workspace: Path
) -> None:
    runtime_config()
    token_path = test_workspace / "google-token.json"
    monkeypatch.setenv("GOOGLE_TASKS_TOKEN_PATH", str(token_path))
    settings = get_google_tasks_settings()
    credentials = _FakeCredentials(
        json.dumps(
            {
                "token": "access-token",
                "refresh_token": "refresh-token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test-google-client-id",
                "client_secret": "test-google-client-secret",
                "scopes": ["https://www.googleapis.com/auth/tasks.readonly"],
            }
        )
    )

    monkeypatch.setattr(
        "app.services.google_tasks.client._run_headless_oauth_flow",
        lambda _settings, *, prompt_for_redirect: credentials,
    )

    result = run_oauth_bootstrap(
        settings=settings,
        headless=True,
        prompt_for_redirect=lambda _prompt: "http://127.0.0.1:1/?code=abc&state=xyz",
    )

    assert result == token_path
    assert json.loads(token_path.read_text(encoding="utf-8"))["refresh_token"] == "refresh-token"
