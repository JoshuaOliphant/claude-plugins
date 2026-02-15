"""
ABOUTME: Tool definitions for hexagonal agent applications.
ABOUTME: Defines MCP tools that the agent can call to read/modify state.

Each tool should:
1. Do ONE thing
2. Return structured JSON data (not formatted strings)
3. Include everything the agent needs for UI generation
4. Handle errors gracefully
"""

from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any
import json
from pathlib import Path
from datetime import datetime

# === Data Persistence ===
# Simple JSON file storage. Replace with database for production.

DATA_FILE = Path("data/store.json")


def _load_data() -> dict:
    """Load data from JSON file."""
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, default=str))


# === Tool Response Helpers ===
#
# IMPORTANT: Tool return format must be exactly:
# {
#     "content": [
#         {"type": "text", "text": "JSON string here"}
#     ]
# }
#
# For errors, add "is_error": True


def _success(data: Any) -> dict:
    """Helper to format successful tool response."""
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(data, default=str)
        }]
    }


def _error(message: str) -> dict:
    """Helper to format error tool response."""
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({"error": message})
        }],
        "is_error": True
    }


# === Tool Definitions ===


@tool(
    "list_items",
    "Get all items. Returns array of items with id, name, status, and created_at.",
    {}  # No parameters needed
)
async def list_items(args: dict[str, Any]) -> dict[str, Any]:
    """List all items."""
    data = _load_data()
    items = data.get("items", [])
    return _success({"items": items, "count": len(items)})


@tool(
    "get_item",
    "Get details for a specific item by ID. Use when user asks about a specific item.",
    {"item_id": str}
)
async def get_item(args: dict[str, Any]) -> dict[str, Any]:
    """Get a single item by ID."""
    data = _load_data()
    items = data.get("items", [])

    for item in items:
        if item["id"] == args["item_id"]:
            return _success({"item": item})

    return _error(f"Item not found: {args['item_id']}")


@tool(
    "create_item",
    "Create a new item. Requires name. Optional: description, priority (low/medium/high).",
    {"name": str, "description": str | None, "priority": str | None}
)
async def create_item(args: dict[str, Any]) -> dict[str, Any]:
    """Create a new item."""
    data = _load_data()
    items = data.setdefault("items", [])

    # Generate ID
    item_id = str(len(items) + 1)

    # Create item with all fields
    item = {
        "id": item_id,
        "name": args["name"],
        "description": args.get("description", ""),
        "priority": args.get("priority", "medium"),
        "status": "active",
        "created_at": datetime.now().isoformat()
    }

    items.append(item)
    _save_data(data)

    return _success({"item": item, "message": "Item created successfully"})


@tool(
    "update_item",
    "Update an existing item. Provide item_id and any fields to change.",
    {"item_id": str, "name": str | None, "description": str | None, "priority": str | None, "status": str | None}
)
async def update_item(args: dict[str, Any]) -> dict[str, Any]:
    """Update an item."""
    data = _load_data()
    items = data.get("items", [])

    for item in items:
        if item["id"] == args["item_id"]:
            # Update only provided fields
            if args.get("name"):
                item["name"] = args["name"]
            if args.get("description"):
                item["description"] = args["description"]
            if args.get("priority"):
                item["priority"] = args["priority"]
            if args.get("status"):
                item["status"] = args["status"]

            item["updated_at"] = datetime.now().isoformat()
            _save_data(data)
            return _success({"item": item, "message": "Item updated"})

    return _error(f"Item not found: {args['item_id']}")


@tool(
    "delete_item",
    "Delete an item by ID. This is permanent.",
    {"item_id": str}
)
async def delete_item(args: dict[str, Any]) -> dict[str, Any]:
    """Delete an item."""
    data = _load_data()
    items = data.get("items", [])

    for i, item in enumerate(items):
        if item["id"] == args["item_id"]:
            deleted = items.pop(i)
            _save_data(data)
            return _success({"deleted": deleted, "message": "Item deleted"})

    return _error(f"Item not found: {args['item_id']}")


@tool(
    "search_items",
    "Search items by keyword. Searches name and description.",
    {"query": str}
)
async def search_items(args: dict[str, Any]) -> dict[str, Any]:
    """Search items."""
    data = _load_data()
    items = data.get("items", [])
    query = args["query"].lower()

    matches = [
        item for item in items
        if query in item["name"].lower()
        or query in item.get("description", "").lower()
    ]

    return _success({"items": matches, "count": len(matches), "query": args["query"]})


# === MCP Server Creation ===


def create_tools_server():
    """
    Create the MCP server with all tools.

    This is called by the agent to register tools.
    Add all your @tool decorated functions to the tools list.
    """
    return create_sdk_mcp_server(
        name="app_tools",
        version="1.0.0",
        tools=[
            list_items,
            get_item,
            create_item,
            update_item,
            delete_item,
            search_items,
            # Add more tools here
        ]
    )
