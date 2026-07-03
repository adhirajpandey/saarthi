"""Minimal FastMCP server for Saarthi tools."""

from pathlib import Path
import sys

from fastmcp import FastMCP
from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.logging import setup_logging  # noqa: E402
from shared.notifications.whatsapp import send_whatsapp_message as send_whatsapp_transport  # noqa: E402
from shared.settings import (  # noqa: E402
    McpSettings,
    get_cloudflare_settings,
    get_google_tasks_settings,
    get_mcp_settings,
    get_notion_settings,
)
from app.services.trackcrow_transactions import search_trackcrow_transactions  # noqa: E402
from app.services.cloudflare import get_dns_record, list_dns_records, list_zones  # noqa: E402
from app.services.google_tasks import get_task, list_tasklists, list_tasks  # noqa: E402
from app.services.notion import (  # noqa: E402
    create_greenhouse_experiment as create_notion_greenhouse_experiment,
    create_work_item as create_notion_work_item,
    get_database_schema as get_notion_database_schema,
    list_work_item_projects as list_notion_work_item_projects,
    query_database as query_notion_database,
    update_greenhouse_experiment as update_notion_greenhouse_experiment,
    update_work_item as update_notion_work_item,
)


def build_mcp_auth(settings: McpSettings) -> MultiAuth:
    """Build bearer-token auth for the MCP server."""
    verifier = StaticTokenVerifier(
        tokens={
            settings.mcp_token: {
                "client_id": "saarthi",
                "scopes": ["saarthi:mcp"],
            }
        }
    )
    return MultiAuth(verifiers=[verifier])


mcp = FastMCP("saarthi-mcp", auth=build_mcp_auth(get_mcp_settings()))


def send_personal_whatsapp_message(message: str) -> dict[str, bool | str]:
    """Send a WhatsApp message to the configured personal target."""
    if not message.strip():
        raise ValueError("message must not be empty")

    settings = get_mcp_settings()
    setup_logging(settings.logging_settings())
    sent = send_whatsapp_transport(
        message=message,
        whatsapp_settings=settings.whatsapp_settings_for_mcp(),
    )
    if sent:
        return {"success": True, "message": "WhatsApp message sent"}
    return {"success": False, "message": "Failed to send WhatsApp message"}


@mcp.tool(name="send_whatsapp_message")
def send_whatsapp_message_tool(message: str) -> dict[str, bool | str]:
    """Send a WhatsApp message to the configured personal target."""
    return send_personal_whatsapp_message(message)


def search_personal_transactions(
    recipient: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
) -> dict[str, object]:
    """Search Trackcrow transactions for the configured MCP user."""
    settings = get_mcp_settings()
    setup_logging(settings.logging_settings())
    return search_trackcrow_transactions(
        settings=settings,
        recipient=recipient,
        category=category,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@mcp.tool(name="search_transactions")
def search_transactions_tool(
    recipient: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
) -> dict[str, object]:
    """Search Trackcrow transactions for the configured MCP user."""
    return search_personal_transactions(
        recipient=recipient,
        category=category,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


def list_personal_cloudflare_zones(
    name: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, object]:
    """List Cloudflare zones visible to the configured token."""
    settings = get_cloudflare_settings()
    setup_logging(settings.logging_settings())
    return list_zones(
        settings=settings,
        name=name,
        status=status,
        page=page,
        per_page=per_page,
    )


@mcp.tool(name="list_cloudflare_zones")
def list_cloudflare_zones_tool(
    name: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, object]:
    """List Cloudflare zones visible to the configured token."""
    return list_personal_cloudflare_zones(
        name=name,
        status=status,
        page=page,
        per_page=per_page,
    )


def search_personal_cloudflare_dns_records(
    zone_id: str | None = None,
    zone_name: str | None = None,
    type: str | None = None,
    name: str | None = None,
    content: str | None = None,
    proxied: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, object]:
    """List DNS records from a Cloudflare zone."""
    settings = get_cloudflare_settings()
    setup_logging(settings.logging_settings())
    return list_dns_records(
        settings=settings,
        zone_id=zone_id,
        zone_name=zone_name,
        type=type,
        name=name,
        content=content,
        proxied=proxied,
        page=page,
        per_page=per_page,
    )


@mcp.tool(name="search_cloudflare_dns_records")
def search_cloudflare_dns_records_tool(
    zone_id: str | None = None,
    zone_name: str | None = None,
    type: str | None = None,
    name: str | None = None,
    content: str | None = None,
    proxied: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, object]:
    """List DNS records from a Cloudflare zone."""
    return search_personal_cloudflare_dns_records(
        zone_id=zone_id,
        zone_name=zone_name,
        type=type,
        name=name,
        content=content,
        proxied=proxied,
        page=page,
        per_page=per_page,
    )


def get_personal_cloudflare_dns_record(
    record_id: str,
    zone_id: str | None = None,
    zone_name: str | None = None,
) -> dict[str, object]:
    """Get one DNS record from a Cloudflare zone."""
    settings = get_cloudflare_settings()
    setup_logging(settings.logging_settings())
    return get_dns_record(
        settings=settings,
        record_id=record_id,
        zone_id=zone_id,
        zone_name=zone_name,
    )


@mcp.tool(name="get_cloudflare_dns_record")
def get_cloudflare_dns_record_tool(
    record_id: str,
    zone_id: str | None = None,
    zone_name: str | None = None,
) -> dict[str, object]:
    """Get one DNS record from a Cloudflare zone."""
    return get_personal_cloudflare_dns_record(
        record_id=record_id,
        zone_id=zone_id,
        zone_name=zone_name,
    )


def list_personal_google_tasklists(
    page_token: str | None = None,
    max_results: int = 100,
) -> dict[str, object]:
    """List Google task lists for the configured personal account."""
    settings = get_google_tasks_settings()
    setup_logging(settings.logging_settings())
    return list_tasklists(
        settings=settings,
        page_token=page_token,
        max_results=max_results,
    )


@mcp.tool(name="list_google_tasklists")
def list_google_tasklists_tool(
    page_token: str | None = None,
    max_results: int = 100,
) -> dict[str, object]:
    """List Google task lists for the configured personal account."""
    return list_personal_google_tasklists(
        page_token=page_token,
        max_results=max_results,
    )


def list_personal_google_tasks(
    tasklist_id: str | None = None,
    tasklist_title: str | None = None,
    page_token: str | None = None,
    max_results: int = 20,
    show_completed: bool = True,
    show_hidden: bool = False,
    show_deleted: bool = False,
    show_assigned: bool = False,
) -> dict[str, object]:
    """List Google tasks from a selected task list."""
    settings = get_google_tasks_settings()
    setup_logging(settings.logging_settings())
    return list_tasks(
        settings=settings,
        tasklist_id=tasklist_id,
        tasklist_title=tasklist_title,
        page_token=page_token,
        max_results=max_results,
        show_completed=show_completed,
        show_hidden=show_hidden,
        show_deleted=show_deleted,
        show_assigned=show_assigned,
    )


@mcp.tool(name="list_google_tasks")
def list_google_tasks_tool(
    tasklist_id: str | None = None,
    tasklist_title: str | None = None,
    page_token: str | None = None,
    max_results: int = 20,
    show_completed: bool = True,
    show_hidden: bool = False,
    show_deleted: bool = False,
    show_assigned: bool = False,
) -> dict[str, object]:
    """List Google tasks from a selected task list."""
    return list_personal_google_tasks(
        tasklist_id=tasklist_id,
        tasklist_title=tasklist_title,
        page_token=page_token,
        max_results=max_results,
        show_completed=show_completed,
        show_hidden=show_hidden,
        show_deleted=show_deleted,
        show_assigned=show_assigned,
    )


def get_personal_google_task(
    task_id: str,
    tasklist_id: str | None = None,
    tasklist_title: str | None = None,
) -> dict[str, object]:
    """Get one Google task from a selected task list."""
    settings = get_google_tasks_settings()
    setup_logging(settings.logging_settings())
    return get_task(
        settings=settings,
        task_id=task_id,
        tasklist_id=tasklist_id,
        tasklist_title=tasklist_title,
    )


@mcp.tool(name="get_google_task")
def get_google_task_tool(
    task_id: str,
    tasklist_id: str | None = None,
    tasklist_title: str | None = None,
) -> dict[str, object]:
    """Get one Google task from a selected task list."""
    return get_personal_google_task(
        task_id=task_id,
        tasklist_id=tasklist_id,
        tasklist_title=tasklist_title,
    )


def get_personal_notion_database_schema(database_key: str) -> dict[str, object]:
    """Get schema metadata for a configured Notion database."""
    settings = get_notion_settings()
    setup_logging(settings.logging_settings())
    return get_notion_database_schema(settings=settings, database_key=database_key)


@mcp.tool(name="get_notion_database_schema")
def get_notion_database_schema_tool(database_key: str) -> dict[str, object]:
    """Get schema metadata for a configured Notion database."""
    return get_personal_notion_database_schema(database_key=database_key)


def query_personal_notion_database(
    database_key: str,
    start_cursor: str | None = None,
    page_size: int = 25,
    project: str | None = None,
) -> dict[str, object]:
    """Query rows from a configured Notion database. Use project only with work_items; use all or omit it for every project."""
    settings = get_notion_settings()
    setup_logging(settings.logging_settings())
    return query_notion_database(
        settings=settings,
        database_key=database_key,
        start_cursor=start_cursor,
        page_size=page_size,
        project=project,
    )


@mcp.tool(name="query_notion_database")
def query_notion_database_tool(
    database_key: str,
    start_cursor: str | None = None,
    page_size: int = 25,
    project: str | None = None,
) -> dict[str, object]:
    """Query rows from a configured Notion database. Use project only with work_items; use all or omit it for every project."""
    return query_personal_notion_database(
        database_key=database_key,
        start_cursor=start_cursor,
        page_size=page_size,
        project=project,
    )


def get_links_database_schema() -> dict[str, object]:
    """Get schema metadata for the saved links Notion database."""
    return get_personal_notion_database_schema(database_key="links")


@mcp.tool(name="get_links_database_schema")
def get_links_database_schema_tool() -> dict[str, object]:
    """Get schema metadata for the saved links Notion database."""
    return get_links_database_schema()


def list_saved_links(
    start_cursor: str | None = None,
    page_size: int = 25,
) -> dict[str, object]:
    """List saved links from Notion with pagination."""
    return query_personal_notion_database(
        database_key="links",
        start_cursor=start_cursor,
        page_size=page_size,
    )


@mcp.tool(name="list_saved_links")
def list_saved_links_tool(
    start_cursor: str | None = None,
    page_size: int = 25,
) -> dict[str, object]:
    """List saved links from Notion with pagination."""
    return list_saved_links(start_cursor=start_cursor, page_size=page_size)


def get_work_items_database_schema() -> dict[str, object]:
    """Get schema metadata for the work items Notion database."""
    return get_personal_notion_database_schema(database_key="work_items")


@mcp.tool(name="get_work_items_database_schema")
def get_work_items_database_schema_tool() -> dict[str, object]:
    """Get schema metadata for the work items Notion database."""
    return get_work_items_database_schema()


def list_work_items(
    start_cursor: str | None = None,
    page_size: int = 25,
    project: str | None = None,
) -> dict[str, object]:
    """List Notion work items. Filter by project with Vidwiz, Trackcrow, or Habitat; use all for every project."""
    return query_personal_notion_database(
        database_key="work_items",
        start_cursor=start_cursor,
        page_size=page_size,
        project=project,
    )


@mcp.tool(name="list_work_items")
def list_work_items_tool(
    start_cursor: str | None = None,
    page_size: int = 25,
    project: str | None = None,
) -> dict[str, object]:
    """List Notion work items. Filter by project with Vidwiz, Trackcrow, or Habitat; use all for every project."""
    return list_work_items(start_cursor=start_cursor, page_size=page_size, project=project)


def list_work_item_projects() -> dict[str, object]:
    """List project names that currently have Notion work items, with item counts."""
    settings = get_notion_settings()
    setup_logging(settings.logging_settings())
    return list_notion_work_item_projects(settings=settings)


@mcp.tool(name="list_work_item_projects")
def list_work_item_projects_tool() -> dict[str, object]:
    """List project names that currently have Notion work items, with item counts."""
    return list_work_item_projects()


def create_personal_work_item(
    name: str,
    project: str,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Create one Notion work item in the configured work items database."""
    settings = get_notion_settings()
    setup_logging(settings.logging_settings())
    return create_notion_work_item(
        settings=settings,
        name=name,
        project=project,
        status=status,
        priority=priority,
        category=category,
        description=description,
    )


@mcp.tool(name="create_work_item")
def create_work_item_tool(
    name: str,
    project: str,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Create one Notion work item in the configured work items database."""
    return create_personal_work_item(
        name=name,
        project=project,
        status=status,
        priority=priority,
        category=category,
        description=description,
    )


def update_personal_work_item(
    page_id: str,
    name: str | None = None,
    project: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Update one Notion work item by page ID."""
    settings = get_notion_settings()
    setup_logging(settings.logging_settings())
    return update_notion_work_item(
        settings=settings,
        page_id=page_id,
        name=name,
        project=project,
        status=status,
        priority=priority,
        category=category,
        description=description,
    )


@mcp.tool(name="update_work_item")
def update_work_item_tool(
    page_id: str,
    name: str | None = None,
    project: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Update one Notion work item by page ID."""
    return update_personal_work_item(
        page_id=page_id,
        name=name,
        project=project,
        status=status,
        priority=priority,
        category=category,
        description=description,
    )


def get_greenhouse_experiments_schema() -> dict[str, object]:
    """Get schema metadata for the Greenhouse experiments Notion database."""
    return get_personal_notion_database_schema(database_key="greenhouse_experiments")


@mcp.tool(name="get_greenhouse_experiments_schema")
def get_greenhouse_experiments_schema_tool() -> dict[str, object]:
    """Get schema metadata for the Greenhouse experiments Notion database."""
    return get_greenhouse_experiments_schema()


def list_greenhouse_experiments(
    start_cursor: str | None = None,
    page_size: int = 25,
) -> dict[str, object]:
    """List Greenhouse experiments from Notion with pagination."""
    return query_personal_notion_database(
        database_key="greenhouse_experiments",
        start_cursor=start_cursor,
        page_size=page_size,
    )


@mcp.tool(name="list_greenhouse_experiments")
def list_greenhouse_experiments_tool(
    start_cursor: str | None = None,
    page_size: int = 25,
) -> dict[str, object]:
    """List Greenhouse experiments from Notion with pagination."""
    return list_greenhouse_experiments(start_cursor=start_cursor, page_size=page_size)


def create_greenhouse_experiment(
    name: str,
    status: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Create one Greenhouse experiment in the configured Notion database."""
    settings = get_notion_settings()
    setup_logging(settings.logging_settings())
    return create_notion_greenhouse_experiment(
        settings=settings,
        name=name,
        status=status,
        priority=priority,
        description=description,
    )


@mcp.tool(name="create_greenhouse_experiment")
def create_greenhouse_experiment_tool(
    name: str,
    status: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Create one Greenhouse experiment in the configured Notion database."""
    return create_greenhouse_experiment(
        name=name,
        status=status,
        priority=priority,
        description=description,
    )


def update_greenhouse_experiment(
    page_id: str,
    name: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Update one Greenhouse experiment by Notion page ID."""
    settings = get_notion_settings()
    setup_logging(settings.logging_settings())
    return update_notion_greenhouse_experiment(
        settings=settings,
        page_id=page_id,
        name=name,
        status=status,
        priority=priority,
        description=description,
    )


@mcp.tool(name="update_greenhouse_experiment")
def update_greenhouse_experiment_tool(
    page_id: str,
    name: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    """Update one Greenhouse experiment by Notion page ID."""
    return update_greenhouse_experiment(
        page_id=page_id,
        name=name,
        status=status,
        priority=priority,
        description=description,
    )


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")
