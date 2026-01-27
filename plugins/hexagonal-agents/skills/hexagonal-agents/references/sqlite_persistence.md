# SQLite Persistence

This reference documents how to migrate from JSON file storage to SQLite for proper ACID-compliant persistence.

## Why SQLite Over JSON?

| Feature | JSON Files | SQLite |
|---------|-----------|--------|
| ACID compliance | No | Yes |
| Concurrent access | Prone to corruption | Safe |
| Query capabilities | Load all, filter in Python | SQL queries |
| Data integrity | None | Constraints, foreign keys |
| Performance at scale | Degrades | Consistent |
| Migration support | Manual | Alembic integration |

## When to Migrate

Migrate to SQLite when you need:
- Multiple users or processes accessing data
- Reliable persistence (no data loss on crashes)
- Query capabilities (search, filter, aggregate)
- Data relationships (foreign keys)
- Data validation (constraints)

## Implementation

### Database Module

```python
# ABOUTME: SQLite database layer for persistent storage.
# ABOUTME: Provides async CRUD operations and handles schema initialization.

"""
Database layer using SQLite for persistent storage.

This replaces the JSON file approach for better reliability
and proper ACID compliance.
"""

import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Any

DATABASE_PATH = Path("data/app.db")


async def init_db():
    """Initialize the database schema."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        await db.commit()


async def get_all_items() -> list[dict]:
    """Get all items from the database."""
    await init_db()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM items ORDER BY id") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_item(item_id: int) -> dict | None:
    """Get a single item by ID."""
    await init_db()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_item(
    name: str,
    description: str = "",
    status: str = "active",
    metadata: dict | None = None,
) -> dict:
    """Create a new item and return it."""
    await init_db()

    created_at = datetime.now().isoformat()
    metadata_json = json.dumps(metadata or {})

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO items (name, description, status, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, description, status, metadata_json, created_at)
        )
        await db.commit()
        item_id = cursor.lastrowid

    return {
        "id": item_id,
        "name": name,
        "description": description,
        "status": status,
        "metadata": metadata or {},
        "created_at": created_at,
        "updated_at": None
    }


async def update_item(item_id: int, **updates) -> dict | None:
    """Update an item and return the updated record."""
    await init_db()

    # Get existing item
    item = await get_item(item_id)
    if not item:
        return None

    # Apply updates
    if "name" in updates and updates["name"]:
        item["name"] = updates["name"]
    if "description" in updates:
        item["description"] = updates["description"] or ""
    if "status" in updates and updates["status"]:
        item["status"] = updates["status"]
    if "metadata" in updates:
        item["metadata"] = updates["metadata"] or {}

    item["updated_at"] = datetime.now().isoformat()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE items
            SET name = ?, description = ?, status = ?, metadata = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                item["name"],
                item["description"],
                item["status"],
                json.dumps(item["metadata"]),
                item["updated_at"],
                item_id
            )
        )
        await db.commit()

    return item


async def delete_item(item_id: int) -> dict | None:
    """Delete an item and return the deleted record."""
    await init_db()

    # Get existing item first
    item = await get_item(item_id)
    if not item:
        return None

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()

    return item


async def search_items(query: str) -> list[dict]:
    """Search items by name or description."""
    await init_db()

    search_term = f"%{query}%"

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM items
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY id
            """,
            (search_term, search_term)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_stats() -> dict:
    """Get aggregate statistics."""
    await init_db()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Total count
        async with db.execute("SELECT COUNT(*) FROM items") as cursor:
            total = (await cursor.fetchone())[0]

        # Count by status
        by_status = {}
        async with db.execute(
            "SELECT status, COUNT(*) FROM items GROUP BY status"
        ) as cursor:
            async for row in cursor:
                by_status[row[0]] = row[1]

    return {
        "total": total,
        "by_status": by_status,
    }
```

### Migration from JSON

Include a one-time migration function:

```python
async def migrate_from_json():
    """Migrate existing JSON data to SQLite (one-time operation)."""
    import json

    json_path = Path("data/items.json")
    if not json_path.exists():
        return

    # Check if we already have data in SQLite
    items = await get_all_items()
    if items:
        return  # Already migrated

    try:
        data = json.loads(json_path.read_text())
        for item in data.get("items", []):
            await create_item(
                name=item.get("name", ""),
                description=item.get("description", ""),
                status=item.get("status", "active"),
                metadata=item.get("metadata", {}),
            )
        print(f"Migrated {len(data.get('items', []))} items from JSON to SQLite")
    except Exception as e:
        print(f"Migration error: {e}")
```

### FastAPI Lifespan Integration

```python
from contextlib import asynccontextmanager
from app import database as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - init database and cleanup on shutdown."""
    # Initialize database and migrate from JSON if needed
    await db.init_db()
    await db.migrate_from_json()
    yield
    # Cleanup on shutdown (if needed)


app = FastAPI(lifespan=lifespan)
```

### Updated Tools

Update MCP tools to use the database module:

```python
# ABOUTME: MCP tool definitions using SQLite database.
# ABOUTME: Each tool handles one data operation, returns structured JSON.

from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any
import json

from app import database as db


def _success(data: Any) -> dict:
    """Format successful tool response."""
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(data, default=str)
        }]
    }


def _error(message: str) -> dict:
    """Format error tool response."""
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({"error": message})
        }],
        "is_error": True
    }


@tool(
    "list_items",
    "Get all items. Returns array with id, name, description, status.",
    {}
)
async def list_items(args: dict[str, Any]) -> dict[str, Any]:
    """List all items."""
    items = await db.get_all_items()
    return _success({"items": items, "count": len(items)})


@tool(
    "get_item",
    "Get a specific item by ID.",
    {"id": str}
)
async def get_item(args: dict[str, Any]) -> dict[str, Any]:
    """Get a single item."""
    try:
        item_id = int(args["id"])
    except (ValueError, TypeError):
        return _error(f"Invalid item ID: {args.get('id')}")

    item = await db.get_item(item_id)
    if item:
        return _success({"item": item})
    return _error(f"Item not found: {args['id']}")


@tool(
    "create_item",
    "Create a new item. Requires: name. Optional: description, status.",
    {"name": str, "description": str | None, "status": str | None}
)
async def create_item(args: dict[str, Any]) -> dict[str, Any]:
    """Create a new item."""
    name = args.get("name", "").strip()
    if not name:
        return _error("Name is required")

    item = await db.create_item(
        name=name,
        description=args.get("description", "") or "",
        status=args.get("status", "active") or "active",
    )

    return _success({"item": item, "message": "Item created"})


@tool(
    "update_item",
    "Update an existing item. Requires: id. Optional: name, description, status.",
    {"id": str, "name": str | None, "description": str | None, "status": str | None}
)
async def update_item(args: dict[str, Any]) -> dict[str, Any]:
    """Update an item."""
    try:
        item_id = int(args["id"])
    except (ValueError, TypeError):
        return _error(f"Invalid item ID: {args.get('id')}")

    updates = {}
    if args.get("name"):
        updates["name"] = args["name"]
    if args.get("description") is not None:
        updates["description"] = args["description"]
    if args.get("status"):
        updates["status"] = args["status"]

    item = await db.update_item(item_id, **updates)
    if item:
        return _success({"item": item, "message": "Item updated"})
    return _error(f"Item not found: {args['id']}")


@tool(
    "delete_item",
    "Delete an item by ID. This is permanent.",
    {"id": str}
)
async def delete_item(args: dict[str, Any]) -> dict[str, Any]:
    """Delete an item."""
    try:
        item_id = int(args["id"])
    except (ValueError, TypeError):
        return _error(f"Invalid item ID: {args.get('id')}")

    deleted = await db.delete_item(item_id)
    if deleted:
        return _success({"deleted": deleted, "message": "Item deleted"})
    return _error(f"Item not found: {args['id']}")


@tool(
    "search_items",
    "Search items by keyword in name or description.",
    {"query": str}
)
async def search_items(args: dict[str, Any]) -> dict[str, Any]:
    """Search items."""
    query = args.get("query", "").strip()
    if not query:
        return _error("Search query is required")

    matches = await db.search_items(query)
    return _success({"items": matches, "count": len(matches), "query": query})


@tool(
    "get_stats",
    "Get statistics. Returns total count and count by status.",
    {}
)
async def get_stats(args: dict[str, Any]) -> dict[str, Any]:
    """Get statistics."""
    stats = await db.get_stats()
    return _success({"stats": stats})


def create_tools_server():
    """Create the MCP server with all tools."""
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
            get_stats,
        ]
    )
```

## Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "aiosqlite>=0.19.0",
    # ... other dependencies
]
```

## Directory Structure

```
app/
├── database.py       # SQLite operations
├── tools.py          # MCP tools (use database module)
└── main.py           # FastAPI with lifespan
data/
├── app.db            # SQLite database (created at runtime)
├── items.json        # Legacy JSON (kept for migration)
└── saved_views.json  # Saved views (can stay JSON)
```

## Advanced Patterns

### Transactions

```python
async def transfer_item(from_id: int, to_id: int) -> bool:
    """Example of a transaction spanning multiple operations."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # Start transaction
            await db.execute("BEGIN")

            # Do multiple operations
            await db.execute(
                "UPDATE items SET status = 'transferred' WHERE id = ?",
                (from_id,)
            )
            await db.execute(
                "UPDATE items SET received_from = ? WHERE id = ?",
                (from_id, to_id)
            )

            # Commit if all succeeded
            await db.commit()
            return True
        except Exception:
            # Rollback on any error
            await db.rollback()
            return False
```

### Relationships

```python
async def init_db():
    """Initialize with related tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)

        await db.commit()


async def get_items_with_category() -> list[dict]:
    """Join items with their categories."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT i.*, c.name as category_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            ORDER BY i.id
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
```

### Indexes for Performance

```python
async def init_db():
    """Initialize with indexes for common queries."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)

        # Index for status filtering
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_status
            ON items(status)
        """)

        # Index for search
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_name
            ON items(name)
        """)

        await db.commit()
```

## Testing

```python
import pytest
import aiosqlite
from pathlib import Path

# Use in-memory database for tests
TEST_DB = ":memory:"


@pytest.fixture
async def test_db():
    """Create a test database."""
    async with aiosqlite.connect(TEST_DB) as db:
        await db.execute("""
            CREATE TABLE items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()
        yield db


async def test_create_item(test_db):
    """Test item creation."""
    cursor = await test_db.execute(
        "INSERT INTO items (name, created_at) VALUES (?, ?)",
        ("Test Item", "2024-01-01")
    )
    await test_db.commit()

    assert cursor.lastrowid == 1


async def test_get_item(test_db):
    """Test item retrieval."""
    await test_db.execute(
        "INSERT INTO items (name, created_at) VALUES (?, ?)",
        ("Test Item", "2024-01-01")
    )
    await test_db.commit()

    async with test_db.execute(
        "SELECT * FROM items WHERE id = 1"
    ) as cursor:
        row = await cursor.fetchone()
        assert row[1] == "Test Item"
```

## Migration Tips

1. **Keep JSON as backup** - Don't delete JSON files until SQLite is proven stable
2. **Run migration on startup** - Use FastAPI lifespan to auto-migrate
3. **Log migration progress** - Print how many records were migrated
4. **Handle edge cases** - Empty fields, missing keys, invalid data
5. **Test migration** - Create test JSON with edge cases

## Benefits of SQLite

1. **ACID Compliance** - No data corruption on crashes
2. **Concurrent Access** - Safe for multiple processes
3. **Query Power** - SQL for complex filtering/aggregation
4. **Single File** - Easy backup (just copy the .db file)
5. **No Server** - Embedded, no separate process needed
6. **Async Support** - aiosqlite works with FastAPI's async model
