# Claude Agent SDK Reference

This document details the Claude Agent SDK APIs used in hexagonal agent applications.

---

## Installation

```bash
# With pip
pip install claude-agent-sdk

# With uv
uv add claude-agent-sdk

# Current version (as of January 2025): 0.1.22
```

**Prerequisites:**
- Python 3.11+
- Claude Code CLI installed (`npm install -g @anthropic-ai/claude-code`)
- `ANTHROPIC_API_KEY` environment variable set

---

## Core Classes

### ClaudeSDKClient

The main client for interacting with Claude.

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt="Your skill file content here",
    mcp_servers={"server_name": mcp_server},
    allowed_tools=["mcp__server_name__tool_name"],
    permission_mode="acceptEdits",
)

client = ClaudeSDKClient(options=options)
await client.connect()
```

**ClaudeAgentOptions parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `system_prompt` | `str` | The skill file content (UI vocabulary, tool docs) |
| `mcp_servers` | `dict[str, MCPServer]` | MCP servers keyed by name |
| `allowed_tools` | `list[str]` | Tool names the agent can call |
| `permission_mode` | `str` | `"acceptEdits"` auto-approves tool calls |
| `model` | `str` | Model to use (default: claude-sonnet-4-20250514) |

**Methods:**

```python
# Connect to Claude
await client.connect()

# Send a user message
await client.query("show my books")

# Receive response (async generator)
async for message in client.receive_response():
    # Process messages

# Disconnect
await client.disconnect()
```

---

## Message Types

### AssistantMessage

Model's response containing text and/or tool calls.

```python
from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock

async for msg in client.receive_response():
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"Text: {block.text}")
            elif isinstance(block, ToolUseBlock):
                print(f"Tool: {block.name}")
                print(f"Input: {block.input}")
                print(f"ID: {block.id}")
```

### TextBlock

Contains text content from the model.

```python
class TextBlock:
    type: str = "text"
    text: str  # The actual text content
```

### ToolUseBlock

Represents a tool call by the model.

```python
class ToolUseBlock:
    type: str = "tool_use"
    id: str           # Unique identifier for this tool call
    name: str         # Tool name (e.g., "mcp__app_tools__list_books")
    input: dict       # Arguments passed to the tool
```

### ResultMessage

Contains the result of a tool call.

```python
from claude_agent_sdk import ResultMessage

if isinstance(msg, ResultMessage):
    print(f"Tool result: {msg.content}")
    print(f"Tool use ID: {msg.tool_use_id}")
    if msg.is_error:
        print("Tool returned an error")
```

---

## Tool Definition

### @tool Decorator

Defines an MCP tool.

```python
from claude_agent_sdk import tool

@tool(
    "tool_name",           # Name (verb_noun format recommended)
    "Description",         # When to use this tool
    {"param": type}        # Parameter schema
)
async def tool_name(args: dict[str, Any]) -> dict[str, Any]:
    # Implementation
    return {"content": [{"type": "text", "text": "..."}]}
```

**Parameter Schema Types:**

```python
# Required string
{"name": str}

# Required integer
{"count": int}

# Required float
{"price": float}

# Required boolean
{"active": bool}

# Optional (can be None)
{"description": str | None}

# Lists (documented in description)
{"items": list}
```

**Return Format:**

```python
# Success
{
    "content": [
        {"type": "text", "text": json.dumps(data)}
    ]
}

# Error
{
    "content": [
        {"type": "text", "text": json.dumps({"error": "message"})}
    ],
    "is_error": True
}
```

### create_sdk_mcp_server

Creates an MCP server from decorated tool functions.

```python
from claude_agent_sdk import create_sdk_mcp_server

def create_tools_server():
    return create_sdk_mcp_server(
        name="app_tools",     # Server name (used in allowed_tools)
        version="1.0.0",
        tools=[
            list_books,
            create_book,
            # ... all tool functions
        ]
    )
```

---

## MCP Server Naming Convention

Tool names in `allowed_tools` must follow this exact pattern:

```
mcp__{server_key}__{tool_name}
```

**Both separators are double underscores (`__`).**

**Example:**

```python
# Server created with name "app_tools"
server = create_sdk_mcp_server(name="app_tools", ...)

# Client uses "app_tools" as the key
client = ClaudeSDKClient(
    options=ClaudeAgentOptions(
        mcp_servers={"app_tools": server},  # ← Key matches
        allowed_tools=[
            "mcp__app_tools__list_books",   # ← mcp__{key}__{tool}
            "mcp__app_tools__create_book",
        ],
    )
)
```

**Debugging mismatches:**

```python
# Print registered tool names
server = create_tools_server()
print("Registered tools:", list(server.tools.keys()))

# Verify allowed tools format
for name in allowed_tools:
    parts = name.split("__")
    print(f"Format: mcp__{parts[1]}__{parts[2]}")
```

---

## Response Processing

### Extracting HTML

```python
async def process(self, message: str) -> str:
    await self.client.query(message)

    html_parts: list[str] = []

    async for msg in self.client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    html_parts.append(block.text)

    return "\n".join(html_parts)
```

### Tracking Tool Calls

```python
async def process_with_logging(self, message: str) -> tuple[str, list[dict]]:
    await self.client.query(message)

    html_parts: list[str] = []
    tool_calls: list[dict] = []

    async for msg in self.client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    html_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_calls.append({
                        "name": block.name,
                        "input": block.input,
                        "id": block.id,
                    })

    return "\n".join(html_parts), tool_calls
```

---

## Error Handling

### Tool Errors

Return errors with `is_error: True`:

```python
@tool("get_book", "Get a book by ID", {"id": str})
async def get_book(args):
    book = find_book(args["id"])
    if not book:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": "Book not found"})}],
            "is_error": True
        }
    return {"content": [{"type": "text", "text": json.dumps(book)}]}
```

### Client Errors

Wrap client operations in try/except:

```python
async def process(self, message: str) -> str:
    try:
        await self._ensure_connected()
        await self.client.query(message)
        # ... process response
    except Exception as e:
        return self._error_html(f"Error: {e}")
```

---

## Connection Management

### Lazy Connection

Connect only when first message arrives:

```python
class Agent:
    def __init__(self):
        self.client = None
        self._connected = False

    async def _ensure_connected(self):
        if self._connected:
            return

        self.client = ClaudeSDKClient(options=...)
        await self.client.connect()
        self._connected = True
```

### Cleanup

Always disconnect on shutdown:

```python
async def close(self):
    if self.client:
        await self.client.disconnect()
        self.client = None
        self._connected = False
```

With FastAPI:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await agent.close()

app = FastAPI(lifespan=lifespan)
```

---

## Best Practices

### 1. Single Responsibility Tools

Each tool does ONE thing:

```python
# Good
@tool("list_books", "Get all books", {})
@tool("search_books", "Search books by query", {"query": str})

# Bad
@tool("get_books", "Get books, optionally filtered", {"query": str | None})
```

### 2. Rich Tool Descriptions

Tell the agent WHEN to use the tool:

```python
# Good
@tool("create_book", "Create a new book. Use when user wants to add a book to their collection.", {...})

# Bad
@tool("create_book", "Creates book", {...})
```

### 3. Complete Return Data

Include everything needed for UI:

```python
# Good
return {"book": book, "message": "Book created", "total_books": len(books)}

# Bad
return {"id": book_id}
```

### 4. Consistent Error Format

Always use the same error structure:

```python
def _error(message: str) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message})}],
        "is_error": True
    }
```

---

## Version History

| Version | Key Changes |
|---------|-------------|
| 0.1.22 | Current stable |
| 0.1.0 | Initial release |

Check for updates:

```bash
uv add claude-agent-sdk --upgrade
```
