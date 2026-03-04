---
name: hexagonal-agents
description: >
  This skill should be used when building web applications where an AI agent dynamically generates
  HTML UI, using the hexagonal/ports-and-adapters architecture with HTMX for interactivity and MCP
  tools for data operations. Trigger phrases include "build a hexagonal agent app", "AI agent that
  generates HTML", "agent-driven web UI", "ports and adapters web app", "build me an app where the
  agent creates the frontend", "HTMX with Claude agent", "scaffold a hexagonal agents project", or
  any request for a web application where an AI agent serves as the dynamic UI generation layer
  using the Claude Agent SDK with FastAPI and HTMX.
---

# Hexagonal Agent Application Skill

Build web applications where an AI agent serves as the UI layer, dynamically generating HTML in response to user messages. This architecture combines the hexagonal (ports-and-adapters) pattern with the Claude Agent SDK.

---

## Philosophy

This skill applies the **message-passing paradigm** from Smalltalk and object-oriented programming to AI agents. In this model, the agent is a "prompt object" that receives semantic messages from users and responds with appropriate behavior—in this case, generating UI.

**Key Principles:**

1. **Semantic Late Binding**: The agent interprets user intent at runtime, choosing which tools to call and what UI to generate. This provides flexibility traditional code cannot match.

2. **Separation of Concerns**: Tools handle data operations (CRUD), the agent handles presentation logic (generating HTML), and the HTTP adapter handles transport (FastAPI/HTMX).

3. **Hexagonal Architecture**: The agent sits at the center, with ports (tool interfaces) connecting to adapters (MCP servers, HTTP endpoints). This makes testing and evolution straightforward.

4. **Single Source of Truth**: The skill file defines the agent's entire UI vocabulary. When you want to change behavior, you modify the skill—not scattered code.

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
│  FastAPI Server (HTTP Adapter)                              │
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

**Components:**

- **Browser**: Displays static shell + agent-generated HTML, uses HTMX for partial updates
- **FastAPI**: Receives HTTP requests, passes messages to agent, returns HTML
- **Agent**: Receives messages, calls tools for data, generates HTML responses
- **Tools**: Pure data operations (list, create, update, delete) returning structured JSON

---

## Quick Start Workflow

When a user wants to build a hexagonal agent application, follow these steps:

### Step 1: Initialize Project Structure

Run the initialization script or create manually:

```bash
uv run scripts/init_hexagonal_app.py my-app-name --domain items
```

This creates:
```
my-app-name/
├── pyproject.toml
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── agent.py         # Agent wrapper
│   ├── tools.py         # MCP tool definitions
│   └── skills/
│       └── ui.md        # UI skill file
└── data/                # Created at runtime
```

### Step 2: Define Your Tools

Edit `app/tools.py` to define what operations the agent can perform. Each tool:
- Does ONE thing (single responsibility)
- Returns structured JSON (not formatted strings)
- Has a clear description of WHEN to use it

### Step 3: Create the Skill File

Edit `app/skills/ui.md` to teach the agent:
- What UI components to use
- When to call which tools
- How to handle different user intents

### Step 4: Configure the Agent

The agent wrapper in `app/agent.py` connects everything:
- Loads the skill file into the system prompt
- Registers tools via MCP server
- Extracts HTML from responses

### Step 5: Run and Iterate

```bash
cd my-app-name
uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000` and interact with your agent.

---

## Detailed Implementation

### Tool Design

Tools are the agent's interface to data. They define what actions are possible.

**Tool Anatomy:**

```python
from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any
import json

@tool(
    "list_items",                           # Name: verb_noun format
    "Get all items. Returns array of items with id, name, status.", # Description
    {}                                      # Schema: parameter definitions
)
async def list_items(args: dict[str, Any]) -> dict[str, Any]:
    """List all items."""
    items = load_items()  # Your data access logic
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({"items": items, "count": len(items)})
        }]
    }
```

**Design Principles:**

1. **Single Responsibility**: Each tool does one thing. `list_items` lists, `create_item` creates.

2. **Structured Returns**: Return JSON with all fields the agent needs for UI generation. Don't format strings—let the agent decide presentation.

3. **Clear Descriptions**: The description tells the agent WHEN to use this tool. Be specific: "Get all items" vs "Search items by query".

4. **Error Handling**: Return errors in a consistent format with `is_error: True`.

**Return Format:**

```python
# Success
{
    "content": [{"type": "text", "text": json.dumps(data)}]
}

# Error
{
    "content": [{"type": "text", "text": json.dumps({"error": "message"})}],
    "is_error": True
}
```

**Parameter Schema:**

```python
# Required string
{"name": str}

# Optional (can be None)
{"description": str | None}

# With defaults (in function signature)
@tool("search", "Search items", {"query": str, "limit": int | None})
async def search(query: str, limit: int = 10):
    ...
```

**Creating the MCP Server:**

```python
def create_tools_server():
    return create_sdk_mcp_server(
        name="app_tools",
        version="1.0.0",
        tools=[
            list_items,
            get_item,
            create_item,
            update_item,
            delete_item,
        ]
    )
```

---

### Skill File Design

The skill file is the heart of the hexagonal agent pattern. It teaches the agent how to generate UI.

**Critical Requirements:**

1. **Raw HTML Output**: LLMs default to markdown. You MUST explicitly state "output raw HTML only" multiple times.

2. **Complete Component Patterns**: Show full HTML examples with all classes and HTMX attributes. Don't just list class names.

3. **HTMX Integration**: Every interactive element needs `hx-post`, `hx-target`, and `hx-vals`.

4. **Tool-to-UI Mapping**: Explain when to call each tool and what UI to render with the results.

**Skill File Structure:**

```markdown
# Application UI Skill

You are an AI application that generates user interfaces...

## Critical Output Rules

1. Output ONLY raw HTML — never wrap in markdown code fences
2. Never include ```html or ``` markers
3. All output must be valid HTML fragments
...

## Design System

### Colors (Tailwind classes)
- Background: bg-slate-900 (page), bg-slate-800 (cards)
...

## Component Patterns

### Card Container
```html
<div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
  <!-- content -->
</div>
```

## Available Tools

1. **list_items** — Get all items. Call when user wants to see items.
...

## Response Patterns

### User wants to see items
1. Call list_items tool
2. If items exist: render with Page Header + Item List
3. If no items: render Empty State
...
```

**HTMX Requirements:**

Every button must have:
```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'>
  Text
</button>
```

Every form must have:
```html
<form hx-post="/agent" hx-target="#content">
  <input type="text" name="fieldname">
  <input type="hidden" name="message" value="action with {fieldname}">
  <button type="submit">Submit</button>
</form>
```

---

### Agent Wrapper

The agent wrapper connects the SDK to your application.

**Key Responsibilities:**

1. Load skill file into system prompt
2. Create and register MCP tools server
3. Process messages and extract HTML
4. Handle errors gracefully

**Implementation Pattern:**

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, TextBlock
from pathlib import Path
from app.tools import create_tools_server

SKILL_PATH = Path(__file__).parent / "skills" / "ui.md"

class Agent:
    def __init__(self):
        self.tools_server = create_tools_server()
        self.client = None
        self._connected = False

        # Tool names must match: mcp__{server_name}__{tool_name}
        self._allowed_tools = [
            "mcp__app_tools__list_items",
            "mcp__app_tools__create_item",
            # ... add all your tools
        ]

    async def _ensure_connected(self):
        if self._connected:
            return

        skill_content = SKILL_PATH.read_text()
        options = ClaudeAgentOptions(
            system_prompt=skill_content,
            mcp_servers={"app_tools": self.tools_server},
            allowed_tools=self._allowed_tools,
            permission_mode="acceptEdits",
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()
        self._connected = True

    async def process(self, message: str) -> str:
        await self._ensure_connected()
        await self.client.query(message)

        html_parts = []
        async for msg in self.client.receive_response():
            for block in msg.content:
                if isinstance(block, TextBlock):
                    html_parts.append(block.text)

        return self._clean_html("\n".join(html_parts))

    def _clean_html(self, html: str) -> str:
        """Strip markdown fences if present."""
        html = html.strip()
        if html.startswith("```html"):
            html = html[7:]
        elif html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        return html.strip()
```

**MCP Server Naming:**

Tool names in `allowed_tools` must follow exact format:
```
mcp__{server_key}__{tool_name}
```

Where `server_key` is the key used in `mcp_servers={"server_key": server}`.

---

### HTTP Adapter

The FastAPI application serves as the HTTP adapter in the hexagonal architecture.

**Base Template:**

```python
BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
    <style>
        .htmx-request .loading-indicator { display: flex; }
        .htmx-request #content { opacity: 0.6; }
        .loading-indicator { display: none; }
        @keyframes fadeSlideIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-in { animation: fadeSlideIn 0.3s ease-out; }
    </style>
</head>
<body class="min-h-screen bg-slate-950 text-slate-100">
    <main class="max-w-4xl mx-auto p-4">
        <div class="loading-indicator items-center justify-center py-8">
            <svg class="animate-spin h-8 w-8 text-indigo-500" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
        </div>
        <div id="content">{content}</div>
    </main>
    <footer class="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800">
        <form hx-post="/agent" hx-target="#content" class="max-w-4xl mx-auto p-4 flex gap-3">
            <input type="text" name="message" placeholder="What would you like to do?"
                   class="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white
                          placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <button type="submit" class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg">
                Send
            </button>
        </form>
    </footer>
    <div class="h-24"></div>
</body>
</html>'''
```

**Agent Endpoint:**

```python
@app.post("/agent", response_class=HTMLResponse)
async def handle_message(request: Request):
    form_data = await request.form()
    message = str(form_data.get("message", "")).strip()

    if not message:
        return '<p class="text-amber-400">Please enter a message.</p>'

    # Append form fields to message
    extra_fields = [f"{k}={v}" for k, v in form_data.items() if k != "message" and v]
    if extra_fields:
        message = f"{message} [{', '.join(extra_fields)}]"

    try:
        html = await agent.process(message)
        return html
    except Exception as e:
        return f'''<div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p class="text-red-300">An error occurred. Please try again.</p>
        </div>'''
```

**Form Data Flow:**

1. User submits form with fields + hidden message
2. FastAPI extracts all form data
3. Extra fields appended to message: `"action [field1=value1, field2=value2]"`
4. Agent parses and uses values with appropriate tool

---

## UI Design System

This skill uses a dark, atmospheric aesthetic with refined typography.

### Color Palette

```
Backgrounds:
- Page: bg-slate-950
- Cards: bg-slate-900
- Inputs: bg-slate-800
- Highlight: bg-slate-800/50

Borders:
- Default: border-slate-800
- Emphasis: border-slate-700
- Focus: ring-indigo-500

Accent (use sparingly):
- Primary: bg-indigo-600 hover:bg-indigo-500
- Links: text-indigo-400
- Focus: ring-indigo-500

Text:
- Headings: text-white
- Body: text-slate-300
- Muted: text-slate-400
- Success: text-emerald-400
- Warning: text-amber-400
- Danger: text-red-400
```

### Typography

```
Headings: font-['Space_Grotesk'] font-bold
Body: Default sans (Inter)

Sizes:
- Page title: text-2xl font-bold
- Section: text-xl font-semibold
- Card title: text-lg font-medium
- Body: default
- Caption: text-sm text-slate-400
```

### Component Examples

**Page Header:**
```html
<div class="flex justify-between items-center mb-8 animate-in">
  <div>
    <h1 class="text-2xl font-bold font-['Space_Grotesk'] text-white">Title</h1>
    <p class="text-slate-400 mt-1">Supporting context</p>
  </div>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
          class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                 shadow-lg shadow-indigo-500/25 transition-all duration-200">
    + New Item
  </button>
</div>
```

**Card:**
```html
<div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden
            shadow-lg shadow-slate-950/50 animate-in">
  <div class="p-5">
    <!-- content -->
  </div>
</div>
```

**List Item (Interactive):**
```html
<div class="group flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800
            hover:border-slate-700 hover:bg-slate-800/50 transition-all duration-200 cursor-pointer"
     hx-post="/agent" hx-target="#content" hx-vals='{"message":"show item 123"}'>
  <div class="flex items-center gap-4">
    <div class="w-10 h-10 rounded-lg bg-indigo-600/20 flex items-center justify-center">
      <span class="text-indigo-400 font-semibold">A</span>
    </div>
    <div>
      <p class="font-medium text-white group-hover:text-indigo-300 transition-colors">Item Name</p>
      <p class="text-sm text-slate-400">Description</p>
    </div>
  </div>
  <div class="text-slate-400 group-hover:text-white transition-colors">→</div>
</div>
```

**Primary Button:**
```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
        class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
               shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40
               transition-all duration-200 active:scale-[0.98]">
  Button Text
</button>
```

**Form:**
```html
<form hx-post="/agent" hx-target="#content" class="space-y-5 animate-in">
  <div>
    <label class="block text-sm font-medium text-slate-300 mb-2">Label</label>
    <input type="text" name="field" required
           class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white
                  placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500
                  focus:border-transparent transition-all duration-200">
  </div>
  <input type="hidden" name="message" value="create with field value">
  <div class="flex justify-end gap-3 pt-2">
    <button type="button" hx-post="/agent" hx-target="#content" hx-vals='{"message":"cancel"}'
            class="px-4 py-2.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg">
      Cancel
    </button>
    <button type="submit"
            class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                   shadow-lg shadow-indigo-500/25 transition-all duration-200">
      Create
    </button>
  </div>
</form>
```

**Empty State:**
```html
<div class="text-center py-16 animate-in">
  <div class="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
    <span class="text-2xl">📚</span>
  </div>
  <h3 class="text-lg font-semibold text-white mb-2">No items yet</h3>
  <p class="text-slate-400 mb-6">Get started by creating your first item</p>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"create new"}'
          class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                 shadow-lg shadow-indigo-500/25 transition-all">
    Create First Item
  </button>
</div>
```

**Success Alert:**
```html
<div class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg animate-in">
  <div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
      <span class="text-emerald-400">✓</span>
    </div>
    <p class="text-emerald-300 font-medium">Success message</p>
  </div>
</div>
```

**Error Alert:**
```html
<div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg animate-in">
  <p class="text-red-300">Error message</p>
</div>
```

---

## Evaluation Patterns

Use `pydantic-evals` to systematically test your hexagonal agent application.

### Three Evaluation Targets

1. **Tool Usage**: Did the agent call the right tools with correct parameters?
2. **State Outcome**: Is the data correct after the action?
3. **UI Quality**: Does the HTML make sense for this context?

### Evaluator Types

| Type | Use For | Example |
|------|---------|---------|
| Code-based | Deterministic checks | Tool was called, state changed |
| Model-based | Subjective quality | UI appropriateness |
| Human | Calibration | Periodic review |

### Basic Test Case

```python
from pydantic_evals import Case, Dataset

Case(
    name="create_item_natural_language",
    inputs="Create a task called 'Buy groceries'",
    metadata={"category": "create", "initial_state": {}},
    evaluators=[
        ToolWasCalled(tool_name="create_item"),
        StateCountDelta(collection="items", delta=1),
        ContainsHTMXAttributes(),
    ],
)
```

### Key Principles

- **Grade outcomes, not paths**: Don't require specific tool sequences
- **Start with real failures**: Convert bugs into test cases
- **Run multiple trials**: Agent behavior varies; use `num_trials=3`
- **Graduate passing tests**: Move capability tests to regression suite at 95%+ pass rate

---

## Debugging Guide

### Agent outputs markdown instead of HTML

**Symptom:** Response wrapped in ```html ... ```

**Fix:**
1. Verify skill file has "Output ONLY raw HTML" rule prominently
2. Add reminder at end of system prompt: "Never use markdown code fences"
3. The agent's `_clean_html` method strips fences as fallback

### Tool not being called

**Symptom:** Agent responds conversationally instead of using tools

**Fix:**
1. Check tool is in `allowed_tools` list (exact format: `mcp__servername__toolname`)
2. Verify tool description clearly states when to use it
3. Add explicit instruction: "When user asks X, call tool Y"
4. Print registered tools to debug: `print(list(mcp_server.tools.keys()))`

### HTMX not working

**Symptom:** Buttons cause full page reload or nothing happens

**Fix:**
1. Check HTMX script loaded in base template
2. Verify hx-post, hx-target, hx-vals all present
3. hx-vals must be valid JSON: `hx-vals='{"message":"..."}'`
4. hx-target must match element ID: `hx-target="#content"`

### Form data not reaching agent

**Symptom:** Agent doesn't see form field values

**Fix:**
1. Form fields need `name` attribute
2. Hidden message field must exist
3. Verify FastAPI extracts form fields and appends to message

### Blank response

**Symptom:** Empty content area after request

**Fix:**
1. Check agent properly extracts TextBlock content
2. Look for ResultMessage.is_error being True
3. Add logging to see what messages are received

---

## Domain Adaptation Checklist

To build a hexagonal agent app for your domain:

### 1. Define Your Entities

What are you managing? Books, tasks, recipes, tickets, products?

### 2. Replace Tools (`tools.py`)

- Change entity names (items → books, tasks, etc.)
- Define fields specific to your domain
- Keep CRUD operations standard
- Add domain-specific operations (search, filter, aggregate)

### 3. Update Skill File (`skills/ui.md`)

- Update tool list and descriptions
- Adjust response patterns for your domain
- Customize empty state messages and icons
- Add domain-specific components (star ratings, status badges)

### 4. Update Agent (`agent.py`)

- Change `_allowed_tools` list to match your tools

### 5. Update Welcome Content (`main.py`)

- Domain-appropriate title
- Initial action buttons for your use case

### 6. Test Common Flows

- [ ] List view (empty state)
- [ ] List view (with items)
- [ ] Create item (with form)
- [ ] Create item (natural language)
- [ ] View single item
- [ ] Update item
- [ ] Delete item
- [ ] Search/filter

---

## Running Your Application

```bash
# Navigate to your app
cd my-app-name

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Run with uvicorn
uv run uvicorn app.main:app --reload

# Open browser
open http://localhost:8000
```

---

## Evolving Your Application

As your app matures, consider these advanced patterns documented in the references:

### Multi-Agent Architecture

When your app needs specialized domain expertise, evolve to multiple agents:
- **UI Agent**: Handles user interaction, generates HTML
- **Specialist Agents**: Handle recommendations, analytics, etc.
- **Message Passing**: Agents communicate via semantic messages, not method calls

See `references/multi_agent_patterns.md` for complete implementation.

### Progressive UI Caching (Saved Views)

Reduce latency and API costs by caching agent-generated views:
- **Static Views**: Cache forms, welcome screens
- **Data-Driven Views**: Templates with fresh data at serve time
- **Fast Path**: Match saved views before calling agents

See `references/saved_views.md` for implementation.

### SQLite Persistence

Migrate from JSON files to SQLite for ACID compliance:
- Proper transactions
- Concurrent access safety
- Query capabilities
- Auto-migration from JSON

See `references/sqlite_persistence.md` for implementation.

### Enhanced Loading UX

Improve perceived performance with better feedback:
- Animated loading indicators with status messages
- Form disabling during requests
- Content dimming during loading
- Bouncing dots for agent activity

See `references/enhanced_ux.md` for patterns.

---

## Files Reference

When implementing, refer to these reference files:

### Core Architecture
- `references/architecture.md` — Deep dive on hexagonal architecture
- `references/sdk_reference.md` — Claude Agent SDK API details

### UI & Components
- `references/component_library.md` — Extended UI component patterns
- `references/enhanced_ux.md` — Advanced loading states and visual feedback

### Advanced Patterns
- `references/multi_agent_patterns.md` — Multi-agent message-passing architecture
- `references/saved_views.md` — Progressive UI caching (fast/slow path)
- `references/sqlite_persistence.md` — SQLite database patterns

### Testing & Evaluation
- `references/eval_patterns.md` — Comprehensive evaluation examples

---

## Summary

The hexagonal agent pattern provides:

1. **Clean separation**: Tools handle data, agent handles UI, HTTP handles transport
2. **Flexibility**: Change UI behavior by editing skill file, not code
3. **Testability**: Mock tools for unit tests, use evals for integration
4. **Evolvability**: Swap implementations at any boundary

Start simple: one entity, basic CRUD, minimal UI. Iterate from working software.
