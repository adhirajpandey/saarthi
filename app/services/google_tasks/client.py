"""Read-only Google Tasks helpers and OAuth bootstrap."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError, model_validator

from shared.settings import GoogleTasksSettings

logger = logging.getLogger(__name__)

TASKS_READONLY_SCOPE = "https://www.googleapis.com/auth/tasks.readonly"
SCOPES = (TASKS_READONLY_SCOPE,)
TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"


class GoogleTasksApiError(RuntimeError):
    """Raised when Google Tasks auth or API calls fail."""


class TasklistsFilters(BaseModel):
    """Validated Google task list filters."""

    page_token: str | None = None
    max_results: int = Field(default=100, ge=1, le=100)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        page_token = payload.get("page_token")
        if isinstance(page_token, str):
            payload["page_token"] = page_token.strip() or None
        return payload


class TasksFilters(BaseModel):
    """Validated Google task filters."""

    tasklist_id: str | None = None
    tasklist_title: str | None = None
    page_token: str | None = None
    max_results: int = Field(default=20, ge=1, le=100)
    show_completed: bool = True
    show_hidden: bool = False
    show_deleted: bool = False
    show_assigned: bool = False

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("tasklist_id", "tasklist_title", "page_token"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                payload[field] = field_value.strip() or None
        return payload

    @model_validator(mode="after")
    def _validate_tasklist_selector(self) -> "TasksFilters":
        if bool(self.tasklist_id) == bool(self.tasklist_title):
            raise ValueError("exactly one of tasklist_id or tasklist_title must be provided")
        return self


class TaskLookup(BaseModel):
    """Validated Google task lookup filters."""

    task_id: str | None = None
    tasklist_id: str | None = None
    tasklist_title: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("task_id", "tasklist_id", "tasklist_title"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                payload[field] = field_value.strip() or None
        return payload

    @model_validator(mode="after")
    def _validate_lookup(self) -> "TaskLookup":
        if not self.task_id:
            raise ValueError("task_id is required")
        if bool(self.tasklist_id) == bool(self.tasklist_title):
            raise ValueError("exactly one of tasklist_id or tasklist_title must be provided")
        return self


def _import_google_client_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ModuleNotFoundError as exc:
        raise GoogleTasksApiError(
            "Google Tasks dependencies are not installed. Run `uv sync --group dev`."
        ) from exc
    return Request, Credentials, InstalledAppFlow, build


def _read_token_info(settings: GoogleTasksSettings) -> dict[str, Any]:
    token_path = settings.token_path()
    if not token_path.is_file():
        raise GoogleTasksApiError(f"Google Tasks token file not found: {token_path}")

    try:
        payload = json.loads(token_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoogleTasksApiError(
            f"Google Tasks token file is not valid JSON: {token_path}"
        ) from exc

    if not isinstance(payload, dict):
        raise GoogleTasksApiError(f"Google Tasks token file must contain a JSON object: {token_path}")
    return payload


def _write_token_file(token_path: Path, token_json: str) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=token_path.parent,
        prefix=f"{token_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp_file:
        tmp_file.write(token_json)
        tmp_path = Path(tmp_file.name)
    os.replace(tmp_path, token_path)


def _load_credentials(settings: GoogleTasksSettings) -> Any:
    Request, Credentials, _InstalledAppFlow, _build = _import_google_client_dependencies()
    token_info = _read_token_info(settings)
    token_info["client_id"] = settings.google_tasks_client_id
    token_info["client_secret"] = settings.google_tasks_client_secret
    token_info.setdefault("token_uri", TOKEN_URI)

    try:
        credentials = Credentials.from_authorized_user_info(token_info, scopes=list(SCOPES))
    except ValueError as exc:
        raise GoogleTasksApiError(
            f"Failed to load authorized user credentials from {settings.token_path()}"
        ) from exc

    if not credentials.valid:
        if not credentials.refresh_token:
            raise GoogleTasksApiError(
                "Google Tasks credentials are invalid and do not include a refresh token. "
                "Run `uv run google-tasks-auth` again."
            )
        try:
            credentials.refresh(Request())
        except Exception as exc:  # pragma: no cover - exercised via wrapper tests
            raise GoogleTasksApiError(f"Failed to refresh Google Tasks credentials: {exc}") from exc
        _write_token_file(settings.token_path(), credentials.to_json())

    return credentials


def _build_tasks_service(settings: GoogleTasksSettings) -> Any:
    _Request, _Credentials, _InstalledAppFlow, build = _import_google_client_dependencies()
    credentials = _load_credentials(settings)
    try:
        return build("tasks", "v1", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        raise GoogleTasksApiError(f"Failed to build Google Tasks client: {exc}") from exc


def _run_local_oauth_flow(settings: GoogleTasksSettings) -> Any:
    _Request, _Credentials, InstalledAppFlow, _build = _import_google_client_dependencies()
    client_config = {
        "installed": {
            "client_id": settings.google_tasks_client_id,
            "client_secret": settings.google_tasks_client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
        }
    }
    try:
        flow = InstalledAppFlow.from_client_config(client_config, scopes=list(SCOPES))
        return flow.run_local_server(port=0, open_browser=True, access_type="offline", prompt="consent")
    except Exception as exc:
        raise GoogleTasksApiError(f"Failed to authorize Google Tasks: {exc}") from exc


def _run_headless_oauth_flow(
    settings: GoogleTasksSettings,
    *,
    prompt_for_redirect: Any = input,
) -> Any:
    _Request, _Credentials, InstalledAppFlow, _build = _import_google_client_dependencies()
    client_config = {
        "installed": {
            "client_id": settings.google_tasks_client_id,
            "client_secret": settings.google_tasks_client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
        }
    }
    try:
        flow = InstalledAppFlow.from_client_config(client_config, scopes=list(SCOPES))
        flow.redirect_uri = "http://127.0.0.1:1/"
        auth_url, _state = flow.authorization_url(access_type="offline", prompt="consent")
        print("Open this URL in a browser and complete Google sign-in:")
        print(auth_url)
        redirect_url = prompt_for_redirect(
            "Paste the full redirect URL from the browser address bar: "
        ).strip()
        parsed = urlparse(redirect_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise GoogleTasksApiError("Pasted redirect URL is not valid")
        authorization_response = redirect_url.replace("http://", "https://", 1)
        flow.fetch_token(authorization_response=authorization_response)
        return flow.credentials
    except GoogleTasksApiError:
        raise
    except Exception as exc:
        raise GoogleTasksApiError(f"Failed to authorize Google Tasks: {exc}") from exc


def _close_service(service: Any) -> None:
    close = getattr(service, "close", None)
    if callable(close):
        close()


def _normalize_tasklist(tasklist: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": tasklist.get("id"),
        "title": tasklist.get("title"),
        "updated": tasklist.get("updated"),
        "self_link": tasklist.get("selfLink"),
    }


def _normalize_task(task: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "status": task.get("status"),
        "notes": task.get("notes"),
        "due": task.get("due"),
        "completed": task.get("completed"),
        "updated": task.get("updated"),
        "deleted": task.get("deleted"),
        "hidden": task.get("hidden"),
        "parent": task.get("parent"),
        "position": task.get("position"),
        "web_view_link": task.get("webViewLink"),
        "self_link": task.get("selfLink"),
        "links": task.get("links") or [],
        "assignment_info": task.get("assignmentInfo"),
    }


def _resolve_tasklist_id(
    service: Any,
    *,
    tasklist_id: str | None,
    tasklist_title: str | None,
) -> tuple[str, str | None]:
    if tasklist_id:
        return tasklist_id, tasklist_title

    payload = service.tasklists().list(maxResults=100).execute()
    items = payload.get("items")
    if not isinstance(items, list):
        items = []
    matches = [
        item
        for item in items
        if isinstance(item, Mapping) and item.get("title") == tasklist_title
    ]
    if not matches:
        raise GoogleTasksApiError(f"Task list not found: {tasklist_title}")
    if len(matches) > 1:
        raise GoogleTasksApiError(f"Multiple task lists matched: {tasklist_title}")
    resolved_tasklist_id = matches[0].get("id")
    if not isinstance(resolved_tasklist_id, str) or not resolved_tasklist_id:
        raise GoogleTasksApiError(f"Task list ID missing for: {tasklist_title}")
    resolved_title = matches[0].get("title")
    return resolved_tasklist_id, resolved_title if isinstance(resolved_title, str) else tasklist_title


def run_oauth_bootstrap(
    *,
    settings: GoogleTasksSettings,
    headless: bool = False,
    prompt_for_redirect: Any = input,
) -> Path:
    """Run the installed-app OAuth flow and persist token state."""
    credentials = (
        _run_headless_oauth_flow(settings, prompt_for_redirect=prompt_for_redirect)
        if headless
        else _run_local_oauth_flow(settings)
    )
    token_path = settings.token_path()
    _write_token_file(token_path, credentials.to_json())
    return token_path


def list_tasklists(
    *,
    settings: GoogleTasksSettings,
    page_token: str | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    """List Google task lists for the configured personal account."""
    try:
        filters = TasklistsFilters.model_validate(
            {"page_token": page_token, "max_results": max_results}
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid task list filters"
        raise ValueError(message) from exc

    try:
        service = _build_tasks_service(settings)
        params: dict[str, Any] = {"maxResults": filters.max_results}
        if filters.page_token:
            params["pageToken"] = filters.page_token
        payload = service.tasklists().list(**params).execute()
    except GoogleTasksApiError:
        raise
    except Exception as exc:
        raise GoogleTasksApiError(str(exc)) from exc
    finally:
        if "service" in locals():
            _close_service(service)

    items = payload.get("items")
    tasklists = [_normalize_tasklist(item) for item in items or [] if isinstance(item, Mapping)]
    return {
        "success": True,
        "count": len(tasklists),
        "filters": filters.model_dump(),
        "next_page_token": payload.get("nextPageToken"),
        "tasklists": tasklists,
    }


def list_tasks(
    *,
    settings: GoogleTasksSettings,
    tasklist_id: str | None = None,
    tasklist_title: str | None = None,
    page_token: str | None = None,
    max_results: int = 20,
    show_completed: bool = True,
    show_hidden: bool = False,
    show_deleted: bool = False,
    show_assigned: bool = False,
) -> dict[str, Any]:
    """List Google tasks from a selected task list."""
    try:
        filters = TasksFilters.model_validate(
            {
                "tasklist_id": tasklist_id,
                "tasklist_title": tasklist_title,
                "page_token": page_token,
                "max_results": max_results,
                "show_completed": show_completed,
                "show_hidden": show_hidden,
                "show_deleted": show_deleted,
                "show_assigned": show_assigned,
            }
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid task filters"
        raise ValueError(message) from exc

    try:
        service = _build_tasks_service(settings)
        resolved_tasklist_id, resolved_tasklist_title = _resolve_tasklist_id(
            service,
            tasklist_id=filters.tasklist_id,
            tasklist_title=filters.tasklist_title,
        )
        params: dict[str, Any] = {
            "tasklist": resolved_tasklist_id,
            "maxResults": filters.max_results,
            "showCompleted": filters.show_completed,
            "showHidden": filters.show_hidden,
            "showDeleted": filters.show_deleted,
            "showAssigned": filters.show_assigned,
        }
        if filters.page_token:
            params["pageToken"] = filters.page_token
        payload = service.tasks().list(**params).execute()
    except GoogleTasksApiError:
        raise
    except Exception as exc:
        raise GoogleTasksApiError(str(exc)) from exc
    finally:
        if "service" in locals():
            _close_service(service)

    items = payload.get("items")
    tasks = [_normalize_task(item) for item in items or [] if isinstance(item, Mapping)]
    return {
        "success": True,
        "count": len(tasks),
        "filters": {
            "tasklist_id": resolved_tasklist_id,
            "tasklist_title": resolved_tasklist_title,
            "page_token": filters.page_token,
            "max_results": filters.max_results,
            "show_completed": filters.show_completed,
            "show_hidden": filters.show_hidden,
            "show_deleted": filters.show_deleted,
            "show_assigned": filters.show_assigned,
        },
        "next_page_token": payload.get("nextPageToken"),
        "tasks": tasks,
    }


def get_task(
    *,
    settings: GoogleTasksSettings,
    task_id: str,
    tasklist_id: str | None = None,
    tasklist_title: str | None = None,
) -> dict[str, Any]:
    """Fetch a single Google task by ID."""
    try:
        lookup = TaskLookup.model_validate(
            {
                "task_id": task_id,
                "tasklist_id": tasklist_id,
                "tasklist_title": tasklist_title,
            }
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid task lookup"
        raise ValueError(message) from exc

    try:
        service = _build_tasks_service(settings)
        resolved_tasklist_id, _resolved_tasklist_title = _resolve_tasklist_id(
            service,
            tasklist_id=lookup.tasklist_id,
            tasklist_title=lookup.tasklist_title,
        )
        payload = service.tasks().get(tasklist=resolved_tasklist_id, task=lookup.task_id).execute()
    except GoogleTasksApiError:
        raise
    except Exception as exc:
        raise GoogleTasksApiError(str(exc)) from exc
    finally:
        if "service" in locals():
            _close_service(service)

    if not isinstance(payload, Mapping):
        raise GoogleTasksApiError("Google Tasks API response did not include a task object")
    return {
        "success": True,
        "task": _normalize_task(payload),
    }
