# Hexagonal Agent Application: Complete Implementation Guide

A step-by-step guide for building applications where an AI agent generates UI dynamically. Designed to be followable by an AI assistant or human developer.

---

## Prerequisites

```bash
# Install Claude Code CLI (required for Agent SDK)
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version

# Set API key
export ANTHROPIC_API_KEY=your_key_here
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Browser                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Base HTML Template (static shell)                   │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  #content (HTMX swap target)                │    │   │
│  │  │  ← Agent-generated HTML goes here           │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  Input form: hx-post="/agent"               │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ POST /agent {message: "..."}
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Server                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  @app.post("/agent")                                │   │
│  │  → agent.process(message)                           │   │
│  │  ← returns HTML string                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent (ClaudeSDKClient)                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  System Prompt = skill file + HTML output rules     │   │
│  │  MCP Server = your tool definitions                 │   │
│  │                                                     │   │
│  │  Loop:                                              │   │
│  │    1. Send user message                             │   │
│  │    2. Agent may call tools (handled by SDK)         │   │
│  │    3. Agent generates response                      │   │
│  │    4. Extract text content as HTML                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Tools (MCP Server)                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  @tool("name", "description", {schema})             │   │
│  │  async def name(args) -> {"content": [...]}         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
myapp/
├── app/
│   ├── __init__.py          # Empty, makes it a package
│   ├── main.py              # FastAPI application
│   ├── agent.py             # Agent wrapper class
│   ├── tools.py             # Tool definitions
│   └── skills/
│       └── ui.md            # Skill file (UI vocabulary)
├── data/                    # For persistence (created at runtime)
├── requirements.txt
└── README.md
```

---

## Step 1: Requirements

Create `requirements.txt`:

```
claude-agent-sdk>=0.1.0
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
```

Install:

```bash
pip install -r requirements.txt
```

---

## Step 2: Tool Definitions (`app/tools.py`)

Tools define what the agent can do. Each tool:
- Has a name (verb_noun format)
- Has a description (tells agent when to use it)
- Has an input schema (parameters)
- Returns a specific format

### Complete Tool File Template

```python
"""
Tool definitions for the application.

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
        return {}  # Return empty dict, tools define their own structure
    try:
        return json.loads(DATA_FILE.read_text())
    except json.JSONDecodeError:
        return {}

def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, default=str))


# === Tool Definitions ===
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


# --- Example: List Tool ---
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


# --- Example: Get Single Item Tool ---
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


# --- Example: Create Tool ---
@tool(
    "create_item",
    "Create a new item. Requires name. Optional: description, priority (low/medium/high).",
    {"name": str, "description": str, "priority": str}
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


# --- Example: Update Tool ---
@tool(
    "update_item",
    "Update an existing item. Provide item_id and any fields to change.",
    {"item_id": str, "name": str, "description": str, "priority": str, "status": str}
)
async def update_item(args: dict[str, Any]) -> dict[str, Any]:
    """Update an item."""
    data = _load_data()
    items = data.get("items", [])
    
    for item in items:
        if item["id"] == args["item_id"]:
            # Update only provided fields
            if "name" in args and args["name"]:
                item["name"] = args["name"]
            if "description" in args and args["description"]:
                item["description"] = args["description"]
            if "priority" in args and args["priority"]:
                item["priority"] = args["priority"]
            if "status" in args and args["status"]:
                item["status"] = args["status"]
            
            item["updated_at"] = datetime.now().isoformat()
            _save_data(data)
            return _success({"item": item, "message": "Item updated"})
    
    return _error(f"Item not found: {args['item_id']}")


# --- Example: Delete Tool ---
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


# --- Example: Search Tool ---
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
```

### Tool Design Checklist

- [ ] Each tool does ONE thing
- [ ] Tool names are verb_noun format
- [ ] Descriptions explain WHEN to use the tool
- [ ] Returns include ALL fields needed for display
- [ ] Errors return `is_error: True`
- [ ] All tools added to `create_tools_server()`

---

## Step 3: Skill File (`app/skills/ui.md`)

The skill file teaches the agent how to generate UI. This is injected into the system prompt.

### Critical Requirements

1. **Must specify raw HTML output** — LLMs default to markdown
2. **Must show complete component patterns** — Not just class names
3. **Must include HTMX attributes** — For interactivity
4. **Must map tools to UI patterns** — When to use what

### Complete Skill File Template

```markdown
# Application UI Skill

You are an AI application that generates user interfaces. You receive natural language requests and respond with HTML that will be displayed to the user.

## Critical Output Rules

1. Output ONLY raw HTML — never wrap in markdown code fences
2. Never include ```html or ``` markers
3. Never include explanations outside of HTML
4. All output must be valid HTML fragments
5. Always use the component patterns below
6. Always include HTMX attributes for interactive elements

## Design System

### Colors (Tailwind classes)
- Background: bg-slate-900 (page), bg-slate-800 (cards)
- Text: text-white (headings), text-slate-300 (body), text-slate-400 (muted)
- Primary action: bg-indigo-600 hover:bg-indigo-700
- Danger: bg-red-600 hover:bg-red-700, text-red-400
- Success: bg-emerald-600, text-emerald-400
- Warning: text-amber-400
- Borders: border-slate-700

### Typography
- Page heading: text-2xl font-bold text-white
- Section heading: text-xl font-semibold text-white
- Card heading: text-lg font-medium text-white
- Body: text-slate-300
- Small/muted: text-sm text-slate-400

## Component Patterns

### Card Container
Use for any distinct content section:
```html
<div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
  <!-- content -->
</div>
```

### Card with Header and Actions
```html
<div class="bg-slate-800 rounded-lg border border-slate-700">
  <div class="flex justify-between items-center p-4 border-b border-slate-700">
    <h3 class="text-lg font-medium text-white">Title</h3>
    <div class="flex gap-2">
      <!-- action buttons -->
    </div>
  </div>
  <div class="p-4">
    <!-- content -->
  </div>
</div>
```

### Primary Button
```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action description"}'
        class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors">
  Button Text
</button>
```

### Secondary Button
```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action description"}'
        class="px-3 py-1.5 text-sm text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors">
  Button Text
</button>
```

### Danger Button
```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"delete item 123"}'
        class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded transition-colors">
  Delete
</button>
```

### Form (for collecting user input)
IMPORTANT: Forms must POST to /agent with a hidden message field that describes the action.
```html
<form hx-post="/agent" hx-target="#content" class="space-y-4">
  <div>
    <label class="block text-sm font-medium text-slate-300 mb-1">Field Label</label>
    <input type="text" name="fieldname" required
           class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
  </div>
  
  <!-- Hidden message tells agent what to do with form data -->
  <input type="hidden" name="message" value="create item with name {fieldname}">
  
  <div class="flex justify-end gap-2">
    <button type="button" hx-post="/agent" hx-target="#content" hx-vals='{"message":"cancel, show list"}'
            class="px-4 py-2 text-slate-400 hover:text-white">Cancel</button>
    <button type="submit" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg">
      Submit
    </button>
  </div>
</form>
```

### Item List
```html
<div class="space-y-2">
  <!-- Repeat for each item -->
  <div class="flex items-center justify-between p-3 bg-slate-800 rounded-lg border border-slate-700">
    <div>
      <p class="font-medium text-white">Item Name</p>
      <p class="text-sm text-slate-400">Description or metadata</p>
    </div>
    <div class="flex gap-2">
      <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"show item 123"}'
              class="text-sm text-slate-400 hover:text-white">View</button>
      <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"delete item 123"}'
              class="text-sm text-red-400 hover:text-red-300">Delete</button>
    </div>
  </div>
</div>
```

### Empty State
```html
<div class="text-center py-12">
  <p class="text-slate-400 mb-4">No items yet</p>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"create new item"}'
          class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg">
    Create First Item
  </button>
</div>
```

### Success Alert
```html
<div class="p-4 bg-emerald-900/30 border border-emerald-700 rounded-lg mb-4">
  <p class="text-emerald-300">✓ Success message here</p>
</div>
```

### Error Alert
```html
<div class="p-4 bg-red-900/30 border border-red-700 rounded-lg mb-4">
  <p class="text-red-300">✗ Error message here</p>
</div>
```

### Page Header with Action
```html
<div class="flex justify-between items-center mb-6">
  <h1 class="text-2xl font-bold text-white">Page Title</h1>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"create new"}'
          class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg">
    + New Item
  </button>
</div>
```

## Available Tools

Use these tools to read and modify data:

1. **list_items** — Get all items. Call when user wants to see their items.
2. **get_item** — Get one item by ID. Call when user asks about a specific item.
3. **create_item** — Create new item. Requires: name. Optional: description, priority.
4. **update_item** — Update item. Requires: item_id. Optional: name, description, priority, status.
5. **delete_item** — Delete item. Requires: item_id.
6. **search_items** — Search items by keyword.

## Response Patterns

### User wants to see items ("show my items", "list", "what do I have")
1. Call list_items tool
2. If items exist: render with Page Header + Item List
3. If no items: render Empty State

### User wants to create something ("add", "create", "new")
If user provides the name: 
1. Call create_item with the name
2. Show Success Alert + the created item

If user doesn't provide details:
1. Show Form to collect name (and optionally description, priority)

### User wants to see one item ("show item 3", "details for...")
1. Call get_item with the ID
2. Render detailed card view with edit/delete actions

### User wants to delete ("delete item 3", "remove...")
1. Call delete_item with the ID
2. Show Success Alert + link to view all items

### User wants to update ("change", "edit", "update")
If user provides what to change:
1. Call update_item with item_id and new values
2. Show Success Alert + updated item

If user doesn't specify changes:
1. Call get_item first
2. Show Form pre-filled with current values

### User asks conversational question
Respond in a Card Container with helpful text. Include action buttons for likely next steps.

## Form Data Handling

When a form is submitted, you receive the form fields AND the hidden message field.
Parse the message to understand the intent, then use form field values.

Example: Form with name="title" and message="create item with name {title}"
When user enters "Buy groceries", you receive: message="create item with name {title}", title="Buy groceries"
Action: Call create_item with name="Buy groceries"
```

### Skill File Checklist

- [ ] Output rules clearly state "raw HTML only"
- [ ] Complete HTML examples for every component
- [ ] All examples include Tailwind classes
- [ ] All interactive elements have hx-post, hx-target, hx-vals
- [ ] All tools listed with when to use them
- [ ] Response patterns cover: view list, view one, create, update, delete
- [ ] Form handling pattern explained

---

## Step 4: Agent Wrapper (`app/agent.py`)

The agent wrapper connects the SDK to your application.

### Complete Agent Implementation

```python
"""
Agent wrapper that handles communication with Claude via the Agent SDK.

Key responsibilities:
1. Load skill file into system prompt
2. Connect tools via MCP server
3. Process messages and extract HTML responses
4. Handle errors gracefully
"""

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from pathlib import Path
from app.tools import create_tools_server

# Load skill file
SKILL_PATH = Path(__file__).parent / "skills" / "ui.md"


def _load_skill_file() -> str:
    """Load the skill file content."""
    if SKILL_PATH.exists():
        return SKILL_PATH.read_text()
    return ""


def _build_system_prompt() -> str:
    """
    Build the complete system prompt.
    
    The system prompt must:
    1. Include the skill file (UI patterns and tool usage)
    2. Reinforce raw HTML output requirement
    3. Explain how form data arrives
    """
    skill_content = _load_skill_file()
    
    return f"""{skill_content}

## Final Reminders

- Output ONLY raw HTML. No markdown. No code fences. No explanations.
- Every interactive element needs hx-post="/agent" and hx-target="#content"
- Use hx-vals to pass the message describing what action to take
- When you receive form submissions, field values come as separate parameters alongside the message
"""


class Agent:
    """
    Wrapper around ClaudeSDKClient for the hexagonal agent pattern.
    
    Usage:
        agent = Agent()
        html = await agent.process("show my tasks")
    """
    
    def __init__(self):
        self.tools_server = create_tools_server()
        self.client: ClaudeSDKClient | None = None
        self._connected = False
        
        # Build list of allowed tool names
        # Format: mcp__{server_name}__{tool_name}
        self._allowed_tools = [
            "mcp__app_tools__list_items",
            "mcp__app_tools__get_item",
            "mcp__app_tools__create_item",
            "mcp__app_tools__update_item",
            "mcp__app_tools__delete_item",
            "mcp__app_tools__search_items",
            # Add more as you add tools
        ]
    
    async def _ensure_connected(self) -> None:
        """Initialize and connect the client if not already connected."""
        if self._connected and self.client:
            return
        
        options = ClaudeAgentOptions(
            system_prompt=_build_system_prompt(),
            mcp_servers={"app_tools": self.tools_server},
            allowed_tools=self._allowed_tools,
            permission_mode="acceptEdits",  # Auto-accept tool calls
        )
        
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()
        self._connected = True
    
    async def process(self, message: str) -> str:
        """
        Process a user message and return HTML.
        
        Args:
            message: Natural language from user (may include form field data)
            
        Returns:
            HTML string to render
        """
        await self._ensure_connected()
        
        # Send the message to the agent
        await self.client.query(message)
        
        # Collect response
        html_parts: list[str] = []
        error_occurred = False
        
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Collect text content (should be HTML)
                        html_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        # Tool calls are handled automatically by SDK
                        # We just observe them for debugging
                        pass
            
            elif isinstance(msg, ResultMessage):
                if msg.is_error:
                    error_occurred = True
        
        if error_occurred and not html_parts:
            return self._error_html("Something went wrong. Please try again.")
        
        html = "\n".join(html_parts)
        return self._clean_html(html)
    
    def _clean_html(self, html: str) -> str:
        """
        Clean up the HTML response.
        
        Sometimes the LLM wraps HTML in markdown code fences despite instructions.
        This strips those if present.
        """
        html = html.strip()
        
        # Remove markdown code fences if present
        if html.startswith("```html"):
            html = html[7:]
        elif html.startswith("```"):
            html = html[3:]
        
        if html.endswith("```"):
            html = html[:-3]
        
        return html.strip()
    
    def _error_html(self, message: str) -> str:
        """Generate error display HTML."""
        return f'''
<div class="p-4 bg-red-900/30 border border-red-700 rounded-lg">
    <p class="text-red-300">✗ {message}</p>
    <button hx-post="/agent" hx-target="#content" hx-vals='{{"message":"show items"}}'
            class="mt-3 text-sm text-slate-400 hover:text-white">
        ← Back to list
    </button>
</div>
'''
    
    async def reset(self) -> None:
        """Reset the conversation state."""
        if self.client:
            await self.client.disconnect()
            self.client = None
            self._connected = False
    
    async def close(self) -> None:
        """Clean up resources."""
        await self.reset()
```

### Agent Checklist

- [ ] Skill file loaded into system prompt
- [ ] Tools server created and registered
- [ ] All tool names added to allowed_tools list (format: `mcp__{server}__{tool}`)
- [ ] HTML extraction handles TextBlock content
- [ ] Markdown fence cleanup implemented
- [ ] Error handling returns valid HTML
- [ ] Reset and close methods implemented

---

## Step 5: FastAPI Application (`app/main.py`)

The HTTP adapter that users interact with.

### Complete FastAPI Implementation

```python
"""
FastAPI application - the HTTP adapter for the hexagonal agent pattern.

Key responsibilities:
1. Serve the base HTML template (the "shell")
2. Handle /agent POST requests (user messages)
3. Return HTML fragments for HTMX to swap
"""

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from typing import Optional
import html as html_lib

from app.agent import Agent

# Create the agent instance
agent = Agent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - cleanup on shutdown."""
    yield
    await agent.close()


app = FastAPI(lifespan=lifespan)


# === Base HTML Template ===
# This is the "shell" that wraps agent-generated content.
# It includes: CSS (Tailwind), HTMX, persistent UI elements.

BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Loading state styles -->
    <style>
        .htmx-request .loading-indicator {{ display: flex; }}
        .htmx-request #content {{ opacity: 0.6; }}
        .loading-indicator {{ display: none; }}
    </style>
</head>
<body class="min-h-screen bg-slate-900 text-slate-100">
    <!-- Header -->
    <nav class="bg-slate-800 border-b border-slate-700">
        <div class="max-w-4xl mx-auto px-4 py-3 flex justify-between items-center">
            <h1 class="text-xl font-bold">{title}</h1>
            <button hx-post="/reset" hx-target="#content" 
                    class="text-sm text-slate-400 hover:text-white transition-colors">
                Reset
            </button>
        </div>
    </nav>
    
    <!-- Main content area - HTMX swaps content here -->
    <main class="max-w-4xl mx-auto p-4">
        <!-- Loading indicator -->
        <div class="loading-indicator items-center justify-center py-8">
            <svg class="animate-spin h-8 w-8 text-indigo-500" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
        </div>
        
        <!-- Content target -->
        <div id="content">
            {content}
        </div>
    </main>
    
    <!-- Input area (fixed at bottom) -->
    <footer class="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700">
        <form hx-post="/agent" hx-target="#content" class="max-w-4xl mx-auto p-4 flex gap-3">
            <input type="text" name="message" 
                   placeholder="What would you like to do?"
                   autocomplete="off"
                   class="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg 
                          text-white placeholder-slate-400 
                          focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
            <button type="submit" 
                    class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 
                           text-white font-medium rounded-lg transition-colors">
                Send
            </button>
        </form>
    </footer>
    
    <!-- Spacer for fixed footer -->
    <div class="h-24"></div>
    
    <!-- Scripts -->
    <script>
        // Clear input after submission
        document.body.addEventListener('htmx:afterRequest', function(event) {{
            if (event.detail.elt.matches('form')) {{
                const input = event.detail.elt.querySelector('input[name="message"]');
                if (input) input.value = '';
            }}
        }});
        
        // Focus input on load
        document.querySelector('input[name="message"]')?.focus();
    </script>
</body>
</html>'''


# Welcome content shown on initial load
WELCOME_CONTENT = '''
<div class="text-center py-16">
    <h2 class="text-2xl font-bold text-white mb-4">Welcome</h2>
    <p class="text-slate-400 mb-8">What would you like to do today?</p>
    <div class="flex flex-wrap justify-center gap-3">
        <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"show my items"}'
                class="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors">
            View Items
        </button>
        <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"create a new item"}'
                class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors">
            Create Item
        </button>
    </div>
</div>
'''


# === Routes ===

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page."""
    return BASE_TEMPLATE.format(
        title="My App",
        content=WELCOME_CONTENT
    )


@app.post("/agent", response_class=HTMLResponse)
async def handle_message(request: Request):
    """
    Handle user messages sent to the agent.
    
    This receives:
    - message: The user's text input OR hidden message from buttons/forms
    - Other form fields: Any additional data from forms
    
    Returns:
    - HTML fragment to be swapped into #content by HTMX
    """
    # Get all form data
    form_data = await request.form()
    
    # Extract the message
    message = form_data.get("message", "")
    if not message or not str(message).strip():
        return '<p class="text-amber-400">Please enter a message.</p>'
    
    message = str(message).strip()
    
    # If there are additional form fields, append them to the message
    # This handles form submissions with field values
    extra_fields = []
    for key, value in form_data.items():
        if key != "message" and value:
            extra_fields.append(f"{key}={value}")
    
    if extra_fields:
        message = f"{message} [{', '.join(extra_fields)}]"
    
    try:
        html = await agent.process(message)
        return html
    except Exception as e:
        # Log the error in production
        print(f"Agent error: {e}")
        return f'''
<div class="p-4 bg-red-900/30 border border-red-700 rounded-lg">
    <p class="text-red-300">✗ An error occurred. Please try again.</p>
</div>
'''


@app.post("/reset", response_class=HTMLResponse)
async def reset():
    """Reset conversation state and return to welcome screen."""
    await agent.reset()
    return WELCOME_CONTENT
```

### HTTP Adapter Checklist

- [ ] Base template includes Tailwind and HTMX
- [ ] Loading indicator styled with htmx-request class
- [ ] #content div exists as HTMX swap target
- [ ] Input form posts to /agent with name="message"
- [ ] Form data extracted including extra fields
- [ ] Error responses return valid HTML
- [ ] Reset endpoint clears agent state

---

## Step 6: Running the Application

```bash
# Make sure you're in the project directory
cd myapp

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Run with uvicorn
uvicorn app.main:app --reload

# Open browser to http://localhost:8000
```

---

## Debugging

### Agent outputs markdown instead of HTML

**Symptom:** Response wrapped in ```html ... ```

**Fix:** 
1. Check skill file has "Output ONLY raw HTML" rule
2. Add to system prompt: "Never use markdown code fences"
3. The agent.py `_clean_html` method should strip fences as fallback

### Tool not being called

**Symptom:** Agent responds conversationally instead of calling tools

**Fix:**
1. Check tool is in `allowed_tools` list (exact format: `mcp__servername__toolname`)
2. Check tool description clearly states when to use it
3. Add explicit instruction in skill file: "When user asks X, call tool Y"

### HTMX not working

**Symptom:** Buttons/forms cause full page reload or nothing happens

**Fix:**
1. Check HTMX script is loaded in base template
2. Check hx-post, hx-target, hx-vals are all present
3. hx-vals must be valid JSON with escaped quotes: `hx-vals='{"message":"..."}'`
4. hx-target must match an element ID: `hx-target="#content"`

### Form data not reaching agent

**Symptom:** Agent doesn't see form field values

**Fix:**
1. Form fields need `name` attribute
2. Check hidden message field exists
3. Verify main.py extracts form fields and appends to message

### Blank response

**Symptom:** Empty content area after request

**Fix:**
1. Check agent.py properly extracts TextBlock content
2. Check for ResultMessage.is_error being True
3. Add logging to see what messages are received

---

## Testing Checklist

Before considering the application complete:

- [ ] Initial page loads with welcome content
- [ ] Typing in input and pressing Enter/Send works
- [ ] "show items" returns list (or empty state)
- [ ] "create item called Test" creates and shows item
- [ ] Button clicks trigger correct agent actions
- [ ] Forms collect input and submit correctly
- [ ] Reset button clears state
- [ ] Error states display gracefully
- [ ] Loading indicator appears during requests

---

## Adapting to Your Domain

### To build a different application:

1. **Replace tools in `tools.py`:**
   - Change entity names (items → tasks, recipes, tickets, etc.)
   - Change fields and operations
   - Update `create_tools_server()` with new tools

2. **Update skill file in `skills/ui.md`:**
   - Change tool list and descriptions
   - Update response patterns for your domain
   - Adjust component patterns if needed

3. **Update agent.py:**
   - Change `_allowed_tools` list to match your tools

4. **Update main.py:**
   - Change title
   - Update WELCOME_CONTENT with domain-appropriate buttons

The architecture stays the same. The domain-specific parts are:
- Tool definitions (what operations exist)
- Skill file (how to present them)
- Welcome content (initial options shown to user)
