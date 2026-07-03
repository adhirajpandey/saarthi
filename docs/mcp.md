# MCP

## General

Saarthi exposes authenticated local tool access through a separate FastMCP
runtime. This is not part of the FastAPI app and is not exposed through the
HTTP API docs.

Runtime entrypoint:

- `mcp-server/server.py`

Docker service:

- `saarthi-mcp`

Default endpoint:

```text
http://localhost:8001/mcp
```

## Auth

MCP requests require:

- Header: `Authorization: Bearer <MCP_TOKEN>`

Codex should connect to the configured `saarthi` MCP server and supply the
bearer token from `MCP_TOKEN`.

Expected Codex MCP config:

```toml
[mcp_servers.saarthi]
url = "http://127.0.0.1:8001/mcp"
bearer_token_env_var = "MCP_TOKEN"
```

The Saarthi MCP container and the Codex process must see the same `MCP_TOKEN`
value.

## Tools

### `send_whatsapp_message`

Short description:
Sends a WhatsApp message through the shared SSH WhatsApp sender.

Expected input:

```json
{
  "message": "Hello from Saarthi"
}
```

Expected output:

Success:

```json
{
  "success": true,
  "message": "WhatsApp message sent"
}
```

Failure:

```json
{
  "success": false,
  "message": "Failed to send WhatsApp message"
}
```

Remarks:

- Empty or whitespace-only messages are rejected.
- The recipient is fixed to `WHATSAPP_TARGET_PERSONAL`.
- The MCP server defines the tool boundary; actual sending is performed by
  `shared.notifications.whatsapp`.

### `search_transactions`

Short description:
Searches Trackcrow transactions for the configured MCP user and returns
structured rows for agents.

Expected input:

```json
{
  "recipient": "medical store",
  "category": "Health",
  "keyword": "syrup",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31",
  "limit": 10
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "recipient": "medical store",
    "category": "Health",
    "keyword": "syrup",
    "start_date": "2026-01-01",
    "end_date": "2026-01-31",
    "limit": 10
  },
  "transactions": [
    {
      "id": 41,
      "timestamp": "2026-01-01T12:30:00Z",
      "amount": 120.5,
      "recipient": "Push Medical Store",
      "recipient_name": "Push Medical Store",
      "category": "Health",
      "subcategory": "Medicine",
      "type": "UPI",
      "remarks": "cough syrup",
      "location": "Bangalore"
    }
  ]
}
```

Failure:

```json
{
  "success": false,
  "message": "Failed to search Trackcrow transactions"
}
```

Remarks:

- At least one filter is required.
- `limit` defaults to `10` and is capped at `50`.
- `start_date` and `end_date` accept ISO-8601 date or datetime strings.
- Searches are always scoped to the configured `TRACKCROW_MCP_USER_UUID`.
- This tool reads Trackcrow data directly from Postgres; it does not call a
  Trackcrow HTTP API.

### `list_cloudflare_zones`

Short description:
Lists Cloudflare zones visible to the configured API token and returns
normalized rows for agents.

Expected input:

```json
{
  "name": "adhirajpandey.tech",
  "status": "active",
  "page": 1,
  "per_page": 10
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "name": "adhirajpandey.tech",
    "status": "active",
    "page": 1,
    "per_page": 10
  },
  "zones": [
    {
      "id": "8ed154052fec209b922b5f9877d4c6c5",
      "name": "adhirajpandey.tech",
      "status": "active",
      "paused": false,
      "type": "full",
      "created_on": "2026-01-01T00:00:00Z",
      "modified_on": "2026-01-02T00:00:00Z",
      "name_servers": ["kenneth.ns.cloudflare.com", "molly.ns.cloudflare.com"]
    }
  ]
}
```

Remarks:

- This tool is read-only.
- `page` defaults to `1`.
- `per_page` defaults to `20` and is capped at `100`.

### `search_cloudflare_dns_records`

Short description:
Lists DNS records from a Cloudflare zone and returns normalized rows for
agents.

Expected input:

```json
{
  "zone_name": "adhirajpandey.tech",
  "type": "CNAME",
  "proxied": true,
  "page": 1,
  "per_page": 20
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "zone_id": "8ed154052fec209b922b5f9877d4c6c5",
    "zone_name": "adhirajpandey.tech",
    "type": "CNAME",
    "name": null,
    "content": null,
    "proxied": true,
    "page": 1,
    "per_page": 20
  },
  "records": [
    {
      "id": "0cbc6033384a922aba0c768da8390e81",
      "zone_id": "8ed154052fec209b922b5f9877d4c6c5",
      "zone_name": "adhirajpandey.tech",
      "name": "saarthi.adhirajpandey.tech",
      "type": "CNAME",
      "content": "fc13605b-9729-4162-bd26-679a6fd134ff.cfargotunnel.com",
      "proxied": true,
      "ttl": 1,
      "comment": null,
      "created_on": "2026-01-01T00:00:00Z",
      "modified_on": "2026-01-02T00:00:00Z"
    }
  ]
}
```

Remarks:

- This tool is read-only.
- Exactly one of `zone_id` or `zone_name` is required.
- `zone_name` is resolved to a zone ID before DNS record lookup.

### `get_cloudflare_dns_record`

Short description:
Fetches one DNS record from a Cloudflare zone by record ID.

Expected input:

```json
{
  "zone_name": "adhirajpandey.tech",
  "record_id": "0cbc6033384a922aba0c768da8390e81"
}
```

Expected output:

Success:

```json
{
  "success": true,
  "record": {
    "id": "0cbc6033384a922aba0c768da8390e81",
    "zone_id": "8ed154052fec209b922b5f9877d4c6c5",
    "zone_name": "adhirajpandey.tech",
    "name": "saarthi.adhirajpandey.tech",
    "type": "CNAME",
    "content": "fc13605b-9729-4162-bd26-679a6fd134ff.cfargotunnel.com",
    "proxied": true,
    "ttl": 1,
    "comment": null,
    "created_on": "2026-01-01T00:00:00Z",
    "modified_on": "2026-01-02T00:00:00Z"
  }
}
```

Remarks:

- This tool is read-only.
- Exactly one of `zone_id` or `zone_name` is required.

### `list_google_tasklists`

Short description:
Lists Google task lists for the configured personal account and returns
normalized rows for agents.

Expected input:

```json
{
  "page_token": null,
  "max_results": 10
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "page_token": null,
    "max_results": 10
  },
  "next_page_token": null,
  "tasklists": [
    {
      "id": "MTUyMjg3MTU1OTQ5ODAxNzE1MDU6MDow",
      "title": "My Tasks",
      "updated": "2026-06-11T21:02:33.729Z",
      "self_link": "https://www.googleapis.com/tasks/v1/users/@me/lists/MTUyMjg3MTU1OTQ5ODAxNzE1MDU6MDow"
    }
  ]
}
```

Remarks:

- This tool is read-only.
- `max_results` defaults to `100` and is capped at `100`.
- This tool reads task lists for the single Google account authorized through
  `google-tasks-auth`.

### `list_google_tasks`

Short description:
Lists tasks from one Google task list and returns normalized rows for agents.

Expected input:

```json
{
  "tasklist_title": "My Tasks",
  "page_token": null,
  "max_results": 20,
  "show_completed": true,
  "show_hidden": false,
  "show_deleted": false,
  "show_assigned": false
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "tasklist_id": "MTUyMjg3MTU1OTQ5ODAxNzE1MDU6MDow",
    "tasklist_title": "My Tasks",
    "page_token": null,
    "max_results": 20,
    "show_completed": true,
    "show_hidden": false,
    "show_deleted": false,
    "show_assigned": false
  },
  "next_page_token": null,
  "tasks": [
    {
      "id": "task-1",
      "title": "Buy milk",
      "status": "needsAction",
      "notes": "2 liters",
      "due": "2026-06-14T00:00:00.000Z",
      "completed": null,
      "updated": "2026-06-13T00:00:00.000Z",
      "deleted": false,
      "hidden": false,
      "parent": null,
      "position": "00000000000000000001",
      "web_view_link": "https://tasks.google.com/task/...",
      "self_link": "https://www.googleapis.com/tasks/v1/lists/.../tasks/task-1",
      "links": [],
      "assignment_info": null
    }
  ]
}
```

Remarks:

- This tool is read-only.
- Exactly one of `tasklist_id` or `tasklist_title` is required.
- `tasklist_title` is resolved to a single task list before task lookup.
- Title-based task list resolution only searches the first `100` Google task
  lists returned by the API.
- `show_assigned` defaults to `false`; assigned tasks are not returned unless
  explicitly requested.

### `get_google_task`

Short description:
Fetches one Google task by ID from one Google task list.

Expected input:

```json
{
  "tasklist_title": "My Tasks",
  "task_id": "task-1"
}
```

Expected output:

Success:

```json
{
  "success": true,
  "task": {
    "id": "task-1",
    "title": "Buy milk",
    "status": "needsAction",
    "notes": "2 liters",
    "due": "2026-06-14T00:00:00.000Z",
    "completed": null,
    "updated": "2026-06-13T00:00:00.000Z",
    "deleted": false,
    "hidden": false,
    "parent": null,
    "position": "00000000000000000001",
    "web_view_link": "https://tasks.google.com/task/...",
    "self_link": "https://www.googleapis.com/tasks/v1/lists/.../tasks/task-1",
    "links": [],
    "assignment_info": null
  }
}
```

Remarks:

- This tool is read-only.
- Exactly one of `tasklist_id` or `tasklist_title` is required.
- Title-based task list resolution only searches the first `100` Google task
  lists returned by the API.

### `get_notion_database_schema`

Short description:
Returns schema metadata for one configured Notion database.

Expected input:

```json
{
  "database_key": "work_items"
}
```

Expected output:

Success:

```json
{
  "success": true,
  "database_key": "work_items",
  "database_id": "391fad61-8b95-8066-a51f-d4ba580730da",
  "data_source_id": "391fad61-8b95-80f6-a358-000c9bc03d00",
  "properties": {
    "Name": { "id": "title", "name": "Name", "type": "title" },
    "Project": { "id": "...", "name": "Project", "type": "select" }
  }
}
```

Remarks:

- This tool is read-only.
- `database_key` must be `links`, `work_items`, or
  `greenhouse_experiments`.
- The MCP response returns the resolved Notion `database_id` and `data_source_id`
  so agents can reason about the backing resource shape.

### `query_notion_database`

Short description:
Queries rows from one configured Notion database and returns normalized pages.

Expected input:

```json
{
  "database_key": "work_items",
  "page_size": 25,
  "project": "Habitat",
  "start_cursor": null
}
```

Expected output:

Success:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "database_key": "work_items",
    "database_id": "391fad61-8b95-8066-a51f-d4ba580730da",
    "data_source_id": "391fad61-8b95-80f6-a358-000c9bc03d00",
    "start_cursor": null,
    "page_size": 25,
    "project": "Habitat"
  },
  "has_more": false,
  "next_cursor": null,
  "pages": [
    {
      "page_id": "391fad61-8b95-81e6-8b8c-000b12345678",
      "url": "https://www.notion.so/...",
      "created_time": "2026-07-02T00:00:00.000Z",
      "last_edited_time": "2026-07-02T00:00:00.000Z",
      "archived": false,
      "in_trash": false,
      "properties": {
        "Name": { "type": "title", "value": "Fix webhook retry handling" },
        "Project": { "type": "select", "value": "Habitat" },
        "Status": { "type": "select", "value": "Pending" }
      }
    }
  ]
}
```

Remarks:

- This tool is read-only.
- `database_key` must be `links`, `work_items`, or
  `greenhouse_experiments`.
- `page_size` defaults to `25` and is capped at `100`.
- `project` is only valid when `database_key` is `work_items`.
- Accepted `project` values are `Vidwiz`, `Trackcrow`, `Habitat`, and `all`.
- Omitting `project`, or passing `all`, returns work items across all projects.
- Each normalized property includes `id`, `type`, `value`, and the original
  `raw` Notion property object.

### `get_links_database_schema`

Short description:
Returns schema metadata for the saved links Notion database.

Expected input:

```json
{}
```

Expected output:

```json
{
  "success": true,
  "database_key": "links",
  "database_id": "384fad61-8b95-8012-acc3-edaacf69eeed",
  "data_source_id": "384fad61-8b95-8170-8541-000bae41081a",
  "properties": {
    "Description": { "id": "...", "name": "Description", "type": "rich_text" },
    "Link": { "id": "...", "name": "Link", "type": "url" }
  }
}
```

Remarks:

- This tool is read-only.
- This is a convenience wrapper around `get_notion_database_schema` for
  `database_key="links"`.

### `list_saved_links`

Short description:
Lists saved links from the configured Notion links database.

Expected input:

```json
{
  "page_size": 25,
  "start_cursor": null
}
```

Expected output:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "database_key": "links",
    "database_id": "384fad61-8b95-8012-acc3-edaacf69eeed",
    "data_source_id": "384fad61-8b95-8170-8541-000bae41081a",
    "start_cursor": null,
    "page_size": 25,
    "project": "all"
  },
  "has_more": false,
  "next_cursor": null,
  "pages": [
    {
      "page_id": "384fad61-8b95-80d3-b4f5-000b12345678",
      "url": "https://www.notion.so/...",
      "properties": {
        "Description": { "type": "rich_text", "value": "Interesting article" },
        "Link": { "type": "url", "value": "https://example.com/article" },
        "Link Type": { "type": "select", "value": "Article" }
      }
    }
  ]
}
```

Remarks:

- This tool is read-only.
- This is a convenience wrapper around `query_notion_database` for
  `database_key="links"`.

### `get_work_items_database_schema`

Short description:
Returns schema metadata for the work items Notion database.

Expected input:

```json
{}
```

Expected output:

```json
{
  "success": true,
  "database_key": "work_items",
  "database_id": "391fad61-8b95-8066-a51f-d4ba580730da",
  "data_source_id": "391fad61-8b95-80f6-a358-000c9bc03d00",
  "properties": {
    "Name": { "id": "title", "name": "Name", "type": "title" },
    "Project": { "id": "...", "name": "Project", "type": "select" },
    "Description": { "id": "...", "name": "Description", "type": "rich_text" },
    "Status": { "id": "...", "name": "Status", "type": "select" },
    "Priority": { "id": "...", "name": "Priority", "type": "select" },
    "Category": { "id": "...", "name": "Category", "type": "select" }
  }
}
```

Remarks:

- This tool is read-only.
- This is a convenience wrapper around `get_notion_database_schema` for
  `database_key="work_items"`.
- The work items database is expected to use a `Project` select with `Vidwiz`,
  `Trackcrow`, and `Habitat`.
- The returned schema is also used by the work-item write tools to serialize
  typed fields to the actual Notion property types configured in the live data
  source.

### `list_work_items`

Short description:
Lists work items from the Notion work items database.

Expected input:

```json
{
  "page_size": 25,
  "project": "all",
  "start_cursor": null
}
```

Expected output:

```json
{
  "success": true,
  "count": 2,
  "filters": {
    "database_key": "work_items",
    "database_id": "391fad61-8b95-8066-a51f-d4ba580730da",
    "data_source_id": "391fad61-8b95-80f6-a358-000c9bc03d00",
    "start_cursor": null,
    "page_size": 25,
    "project": "all"
  },
  "has_more": false,
  "next_cursor": null,
  "pages": [
    {
      "page_id": "391fad61-8b95-81e6-8b8c-000b12345678",
      "url": "https://www.notion.so/...",
      "properties": {
        "Name": { "type": "title", "value": "Fix webhook retry handling" },
        "Project": { "type": "select", "value": "Habitat" }
      }
    },
    {
      "page_id": "391fad61-8b95-81d5-9f11-000b87654321",
      "url": "https://www.notion.so/...",
      "properties": {
        "Name": { "type": "title", "value": "Refine editor onboarding copy" },
        "Project": { "type": "select", "value": "Vidwiz" }
      }
    }
  ]
}
```

Remarks:

- This tool is read-only.
- This is a convenience wrapper around `query_notion_database` for
  `database_key="work_items"`.
- `project` accepts `Vidwiz`, `Trackcrow`, `Habitat`, or `all`.
- Omitting `project`, or passing `all`, returns work items across all projects.

### `create_work_item`

Short description:
Creates one work item in the Notion work items database.

Expected input:

```json
{
  "name": "Add notion integration",
  "project": "Habitat",
  "status": "Pending",
  "priority": "High",
  "category": "Backend",
  "description": "Wire Saarthi MCP tools to Notion work items"
}
```

Expected output:

```json
{
  "success": true,
  "page": {
    "page_id": "391fad61-8b95-8139-9948-d93d9bc737ee",
    "url": "https://www.notion.so/...",
    "created_time": "2026-07-03T00:00:00.000Z",
    "last_edited_time": "2026-07-03T00:00:00.000Z",
    "archived": false,
    "in_trash": false,
    "properties": {
      "Name": { "type": "title", "value": "Add notion integration" },
      "Project": { "type": "select", "value": "Habitat" },
      "Status": { "type": "select", "value": "Pending" },
      "Priority": { "type": "select", "value": "High" },
      "Category": { "type": "select", "value": "Backend" },
      "Description": {
        "type": "rich_text",
        "value": "Wire Saarthi MCP tools to Notion work items"
      }
    }
  }
}
```

Remarks:

- This tool is write-capable.
- `name` and `project` are required.
- `status`, `priority`, `category`, and `description` are optional.
- `project` accepts `Vidwiz`, `Trackcrow`, or `Habitat`; project names are
  normalized case-insensitively.
- Only the supported work-item fields are exposed through this MCP contract:
  `Name`, `Project`, `Status`, `Priority`, `Category`, and `Description`.
- The tool creates a page under the configured `work_items` data source.
- Property serialization is schema-driven; Saarthi maps typed inputs to the
  actual Notion property types exposed by the live data-source schema.

### `update_work_item`

Short description:
Updates one work item in the Notion work items database by page ID.

Expected input:

```json
{
  "page_id": "391fad61-8b95-8139-9948-d93d9bc737ee",
  "status": "Completed",
  "description": "Marked complete from the Saarthi MCP client"
}
```

Expected output:

```json
{
  "success": true,
  "page": {
    "page_id": "391fad61-8b95-8139-9948-d93d9bc737ee",
    "url": "https://www.notion.so/...",
    "created_time": "2026-07-03T00:00:00.000Z",
    "last_edited_time": "2026-07-03T00:05:00.000Z",
    "archived": false,
    "in_trash": false,
    "properties": {
      "Name": { "type": "title", "value": "Add notion integration" },
      "Project": { "type": "select", "value": "Habitat" },
      "Status": { "type": "select", "value": "Completed" },
      "Description": {
        "type": "rich_text",
        "value": "Marked complete from the Saarthi MCP client"
      }
    }
  }
}
```

Remarks:

- This tool is write-capable.
- `page_id` is required and must be a valid Notion page ID.
- At least one of `name`, `project`, `status`, `priority`, `category`, or
  `description` must be provided.
- Only the provided fields are patched.
- `project` accepts `Vidwiz`, `Trackcrow`, or `Habitat`; project names are
  normalized case-insensitively.
- Property serialization is schema-driven; for example, Saarthi does not assume
  the `Status` field uses the Notion `status` property type.

### `get_greenhouse_experiments_schema`

Short description:
Returns schema metadata for the Greenhouse experiments Notion database.

Expected input:

```json
{}
```

Expected output:

```json
{
  "success": true,
  "database_key": "greenhouse_experiments",
  "database_id": "391fad61-8b95-8091-a375-e80219bc6c2f",
  "data_source_id": "391fad61-8b95-80fd-b699-000b01d7ae5d",
  "properties": {
    "Name": { "id": "title", "name": "Name", "type": "title" },
    "Status": { "id": "...", "name": "Status", "type": "select" },
    "Priority": { "id": "...", "name": "Priority", "type": "select" },
    "Description": { "id": "...", "name": "Description", "type": "rich_text" }
  }
}
```

Remarks:

- This tool is read-only.
- This is a convenience wrapper around `get_notion_database_schema` for
  `database_key="greenhouse_experiments"`.
- The Greenhouse experiments database intentionally does not expose `Project`
  or `Category`.

### `list_greenhouse_experiments`

Short description:
Lists Greenhouse experiments from the configured Notion database.

Expected input:

```json
{
  "page_size": 25,
  "start_cursor": null
}
```

Expected output:

```json
{
  "success": true,
  "count": 1,
  "filters": {
    "database_key": "greenhouse_experiments",
    "database_id": "391fad61-8b95-8091-a375-e80219bc6c2f",
    "data_source_id": "391fad61-8b95-80fd-b699-000b01d7ae5d",
    "start_cursor": null,
    "page_size": 25,
    "project": "all"
  },
  "has_more": false,
  "next_cursor": null,
  "pages": [
    {
      "page_id": "391fad61-8b95-81c2-8870-d5618f920e73",
      "url": "https://www.notion.so/...",
      "properties": {
        "Name": { "type": "title", "value": "Postgres read-capacity benchmarking" },
        "Status": { "type": "select", "value": "Pending" },
        "Priority": { "type": "select", "value": "P2" },
        "Description": {
          "type": "rich_text",
          "value": "Measure how many reads the current setup can sustain."
        }
      }
    }
  ]
}
```

Remarks:

- This tool is read-only.
- This is a convenience wrapper around `query_notion_database` for
  `database_key="greenhouse_experiments"`.
- `page_size` defaults to `25` and is capped at `100`.

### `create_greenhouse_experiment`

Short description:
Creates one Greenhouse experiment in the configured Notion database.

Expected input:

```json
{
  "name": "Postgres read-capacity benchmarking",
  "status": "Pending",
  "priority": "P2",
  "description": "Measure how many reads the current setup can sustain."
}
```

Expected output:

```json
{
  "success": true,
  "page": {
    "page_id": "391fad61-8b95-8139-9948-d93d9bc737ee",
    "url": "https://www.notion.so/...",
    "properties": {
      "Name": { "type": "title", "value": "Postgres read-capacity benchmarking" },
      "Status": { "type": "select", "value": "Pending" },
      "Priority": { "type": "select", "value": "P2" },
      "Description": {
        "type": "rich_text",
        "value": "Measure how many reads the current setup can sustain."
      }
    }
  }
}
```

Remarks:

- This tool is write-capable.
- `name` is required.
- `status`, `priority`, and `description` are optional.
- Greenhouse experiments intentionally do not accept `project` or `category`.
- Property serialization is schema-driven.

### `update_greenhouse_experiment`

Short description:
Updates one Greenhouse experiment by Notion page ID.

Expected input:

```json
{
  "page_id": "391fad61-8b95-8139-9948-d93d9bc737ee",
  "status": "Completed",
  "description": "Benchmark finished and notes captured."
}
```

Expected output:

```json
{
  "success": true,
  "page": {
    "page_id": "391fad61-8b95-8139-9948-d93d9bc737ee",
    "url": "https://www.notion.so/...",
    "properties": {
      "Status": { "type": "select", "value": "Completed" },
      "Description": {
        "type": "rich_text",
        "value": "Benchmark finished and notes captured."
      }
    }
  }
}
```

Remarks:

- This tool is write-capable.
- `page_id` is required and must be a valid Notion page ID.
- At least one of `name`, `status`, `priority`, or `description` must be
  provided.
- Only the provided fields are patched.
- Greenhouse experiments intentionally do not accept `project` or `category`.
- Property serialization is schema-driven.

### `list_work_item_projects`

Short description:
Lists project names that currently have work items, with per-project counts.

Expected input:

```json
{}
```

Expected output:

```json
{
  "success": true,
  "count": 3,
  "projects": [
    { "name": "Habitat", "work_item_count": 59 },
    { "name": "Trackcrow", "work_item_count": 12 },
    { "name": "Vidwiz", "work_item_count": 75 }
  ]
}
```

Remarks:

- This tool is read-only.
- Only projects that currently have at least one work item are returned.
- The list is sorted by project name.

## Configuration

Secrets / auth (`.env`):

- `MCP_TOKEN`
- `CLOUDFLARE_API_TOKEN`
- `GOOGLE_TASKS_CLIENT_ID`
- `GOOGLE_TASKS_CLIENT_SECRET`
- `GOOGLE_TASKS_TOKEN_PATH`
- `NOTION_API_KEY`
- `NOTION_LINKS_DATABASE_URL`
- `NOTION_WORK_ITEMS_DATABASE_URL`
- `NOTION_GREENHOUSE_EXPERIMENTS_DATABASE_URL`
- `TRACKCROW_DB_URL`
- `TRACKCROW_MCP_USER_UUID`

Configuration (`app/config/config.py`):

- `WHATSAPP_ENABLED`
- `WHATSAPP_SSH_HOST`
- `WHATSAPP_HERMES_COMMAND_PATH`
- `WHATSAPP_TARGET_PERSONAL`
- `WHATSAPP_TIMEOUT_SECONDS`

Remarks:

- `WHATSAPP_ENABLED` must be enabled for the MCP runtime.
- `WHATSAPP_TARGET_PERSONAL` is required because MCP messages are sent to the
  personal target, not the geofence family target.
- `CLOUDFLARE_API_TOKEN` is required for the Cloudflare MCP tools.
- `GOOGLE_TASKS_CLIENT_ID` and `GOOGLE_TASKS_CLIENT_SECRET` must reference a
  Google OAuth Desktop app client with the Google Tasks API enabled.
- `GOOGLE_TASKS_TOKEN_PATH` must point to an authorized-user token JSON file
  created by `uv run google-tasks-auth` or
  `uv run google-tasks-auth --headless`.
- `NOTION_API_KEY` must belong to a Notion integration with read/write access
  to the configured `work_items` and `greenhouse_experiments` databases, and
  read access to any databases used by read-only tools.
- `NOTION_LINKS_DATABASE_URL` must reference the saved links database.
- `NOTION_WORK_ITEMS_DATABASE_URL` must reference the work items database.
- `NOTION_GREENHOUSE_EXPERIMENTS_DATABASE_URL` must reference the Greenhouse
  experiments database.
- The Notion integration must be shared with all configured Notion databases.
- `TRACKCROW_MCP_USER_UUID` fixes the Trackcrow user scope for transaction
  searches.
- The SSH private key is mounted into the `saarthi-mcp` container by
  `docker-compose.yml`.

## Verify

```bash
docker compose logs saarthi-mcp
codex mcp get saarthi
uv run google-tasks-auth --headless
```

Useful Notion verification calls after deploy:

```text
get_links_database_schema()
list_saved_links(page_size=5)
get_work_items_database_schema()
list_work_items(project="all", page_size=5)
list_work_item_projects()
create_work_item(name="Saarthi MCP verification item", project="Habitat")
update_work_item(page_id="<page_id from create_work_item>", status="Completed")
get_greenhouse_experiments_schema()
list_greenhouse_experiments(page_size=5)
create_greenhouse_experiment(name="Saarthi MCP verification experiment")
update_greenhouse_experiment(
    page_id="<page_id from create_greenhouse_experiment>",
    status="Completed",
)
```

## Runtime Boundaries

- MCP tools are exposed by FastMCP on `/mcp`.
- HTTP endpoints are documented in `api.md`.
- Operational CLIs are documented in `scripts.md`.
- MCP is served by `mcp-server/server.py`; it is not a `pyproject.toml` script
  entry point.
