---
name: hexagonal-agent
description: Build applications where an AI agent generates UI dynamically using the Anthropic Agent SDK, FastAPI, HTMX, and Tailwind CSS. Use when the user wants to create conversational applications, agent-driven interfaces, MCP tools, or implements the hexagonal architecture pattern for AI agents.
version: 1.0.0
allowed-tools: [Read, Write, Glob, Grep, Bash, Edit]
---

# Hexagonal Agent Application Skill

Build web applications where an AI agent generates UI dynamically based on user intent. The agent acts as the controller, calling tools to read/modify state and responding with HTML that HTMX swaps into the page.

## Overview

The hexagonal agent pattern separates your application into three layers:

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (HTMX)                                             │
│  ← User input → HTML fragments                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  HTTP Adapter (FastAPI)                                     │
│  ← Routes messages to agent → Returns HTML                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent (Claude SDK)                                         │
│  ← Processes intent → Calls tools → Generates UI            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Tools (MCP Server)                                         │
│  ← Domain operations → Returns structured data              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Set Up Project

```bash
mkdir myapp && cd myapp
mkdir -p app/skills data

# Create requirements.txt
cat > requirements.txt << 'EOF'
claude-agent-sdk>=0.1.0
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
EOF

pip install -r requirements.txt
```

### 2. Create Empty Files

```bash
touch app/__init__.py
touch app/tools.py
touch app/agent.py
touch app/main.py
touch app/skills/ui.md
```

### 3. Copy Templates

Use the templates from this skill:
- `templates/tools.py` → `app/tools.py`
- `templates/agent.py` → `app/agent.py`
- `templates/main.py` → `app/main.py`
- `templates/skills/ui.md` → `app/skills/ui.md`

### 4. Run

```bash
export ANTHROPIC_API_KEY=your_key_here
uvicorn app.main:app --reload
# Open http://localhost:8000
```

## The Three Design Decisions

Every hexagonal agent app requires three interdependent decisions:

### 1. Tools: What Can the Agent Do?

Tools define the agent's capability boundary. Design atomic, composable operations:

```python
from claude_agent_sdk import tool

@tool("list_items", "Get all items", {})
async def list_items(args):
    # Return structured data, not UI
    return {"content": [{"type": "text", "text": json.dumps({"items": items})}]}

@tool("create_item", "Create a new item", {"name": str, "description": str | None})
async def create_item(args):
    item = {"id": str(uuid4()), "name": args["name"]}
    return {"content": [{"type": "text", "text": json.dumps({"item": item})}]}
```

**Tool Design Principles:**
- Tools should be atomic and composable
- Tools return data, not UI (agent decides presentation)
- Tool names use verb_noun format
- Descriptions explain WHEN to use the tool
- All tools registered in `create_tools_server()`

### 2. Skill File: How Does It Express Itself?

The skill file teaches the agent to generate appropriate UI:

```markdown
# UI Skill

You generate HTML interfaces. Output ONLY raw HTML—no markdown, no code fences.

## Component Patterns

### Card
<div class="bg-slate-900 rounded-xl border border-slate-800 p-5">
  <!-- content -->
</div>

### Button (HTMX-enabled)
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'>
  Click Me
</button>

## Response Patterns

When user asks to see items:
1. Call list_items tool
2. Render as card list with actions

When user wants to create:
1. If details provided: Call create_item → Show success
2. If details missing: Show form to collect input
```

**Skill File Requirements:**
- Specify raw HTML output rules
- Show complete HTML patterns with all classes
- Include HTMX attributes on all interactive elements
- Map tools to UI patterns
- Define response patterns for each intent type

### 3. HTTP Adapter: How Do Users Interact?

The FastAPI adapter handles routing and session management:

```python
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse

@app.post("/agent", response_class=HTMLResponse)
async def handle_message(request: Request):
    form = await request.form()
    message = form.get("message", "")

    # Append extra form fields to message
    extra = {k: v for k, v in form.items() if k != "message"}
    if extra:
        message = f"{message} [{', '.join(f'{k}={v}' for k, v in extra.items())}]"

    return await agent.process(message)
```

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

## Tool Design

### Parameter Schema

The `@tool` decorator uses simplified type annotations:

```python
# Required parameters
@tool("name", "desc", {"title": str, "count": int, "price": float, "active": bool})

# Optional parameters (use | None)
@tool("name", "desc", {"title": str, "description": str | None})

# Defaults in function signature
def my_tool(title: str, limit: int = 10):
    ...
```

### Tool Response Format

All tools must return this exact structure:

```python
def _success(data):
    return {
        "content": [{"type": "text", "text": json.dumps(data, default=str)}]
    }

def _error(message):
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message})}],
        "is_error": True
    }
```

### MCP Server Naming

Tool names in `allowed_tools` follow this pattern:

```
mcp__{server_name}__{tool_name}
```

Both underscores are double underscores (`__`). The server_name must match the key in `mcp_servers={}`:

```python
mcp_server = create_sdk_mcp_server(list_items, create_item, ...)

client = ClaudeSDKClient(
    mcp_servers={"app": mcp_server},  # ← "app" is the server name
    allowed_tools=[
        "mcp__app__list_items",        # ← mcp__{app}__{tool}
        "mcp__app__create_item",
    ],
)
```

## UI Design System

Use the dark, atmospheric design system with Tailwind CSS:

### Colors

```
Backgrounds: bg-slate-950 (page), bg-slate-900 (cards), bg-slate-800 (inputs)
Borders: border-slate-800 (default), border-slate-700 (emphasis)
Text: text-white (headings), text-slate-300 (body), text-slate-400 (muted)
Accent: bg-indigo-600 (buttons), text-indigo-400 (links)
Status: text-emerald-400 (success), text-red-400 (error), text-amber-400 (warning)
```

### Typography

```html
<!-- Load distinctive fonts -->
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">

<!-- Usage -->
<h1 class="text-2xl font-bold font-['Space_Grotesk'] text-white">Heading</h1>
<p class="text-slate-300">Body text</p>
```

### Key Components

**Card:**
```html
<div class="bg-slate-900 rounded-xl border border-slate-800 p-5 shadow-lg shadow-slate-950/50">
  <!-- content -->
</div>
```

**Primary Button:**
```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
        class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
               shadow-lg shadow-indigo-500/25 transition-all duration-200">
  Button
</button>
```

**Form Input:**
```html
<input type="text" name="field"
       class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg
              text-white placeholder-slate-500 focus:outline-none focus:ring-2
              focus:ring-indigo-500 focus:border-transparent">
```

**Success Alert:**
```html
<div class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
  <p class="text-emerald-300">Success message</p>
</div>
```

## HTMX Integration

Every interactive element needs three attributes:

```html
hx-post="/agent"           <!-- Send request to agent -->
hx-target="#content"       <!-- Replace content area -->
hx-vals='{"message":"..."}'  <!-- What action to take -->
```

Forms use a hidden message field:

```html
<form hx-post="/agent" hx-target="#content">
  <input type="text" name="title" required>
  <input type="hidden" name="message" value="create item with title">
  <button type="submit">Create</button>
</form>
```

## Form Data Flow

1. **HTML Form** → User fills fields, submits
2. **FastAPI** → Extracts message + extra fields
3. **Message Construction** → `"action [field1=value1, field2=value2]"`
4. **Agent** → Parses intent and data, calls appropriate tool
5. **HTML Response** → Rendered based on tool result

Example flow:
```
User submits: title="The Hobbit", author="Tolkien", message="add this book"
FastAPI sends: "add this book [title=The Hobbit, author=Tolkien]"
Agent calls: add_book(title="The Hobbit", author="Tolkien")
Agent returns: Success card + book details
```

## Response Patterns

### Viewing a List

1. Call list tool
2. If empty → Empty state with create action
3. If items → Page header + list cards with stagger animation

### Creating Something

1. If user provides details → Call create → Success alert + item card
2. If details missing → Show form

### Viewing One Item

1. Call get tool
2. Full detail card with edit/delete actions
3. Back link to list

### After Actions

Success: Alert + affected item + clear next action
Error: Alert with message + recovery action

## Debugging

### Agent outputs markdown

**Fix:** Reinforce "Output ONLY raw HTML" in skill file. The agent wrapper has `_clean_html()` to strip fences as fallback.

### Tool not being called

**Fix:**
1. Check tool in `allowed_tools` list (format: `mcp__servername__toolname`)
2. Check tool description clearly states when to use it
3. Add explicit mapping in skill file

### HTMX not working

**Fix:**
1. Verify HTMX script loaded in base template
2. Check all three attributes present: `hx-post`, `hx-target`, `hx-vals`
3. Ensure `hx-vals` has valid JSON with escaped quotes

### Form data not reaching agent

**Fix:**
1. Form fields need `name` attribute
2. Check hidden message field exists
3. Verify FastAPI extracts and appends form fields

## Testing Checklist

- [ ] Initial page loads with welcome content
- [ ] Text input and Send works
- [ ] "show items" returns list (or empty state)
- [ ] "create item called Test" creates and shows item
- [ ] Button clicks trigger correct agent actions
- [ ] Forms collect input and submit correctly
- [ ] Reset button clears state
- [ ] Error states display gracefully
- [ ] Loading indicator appears during requests

## References

Detailed documentation available in `references/`:

- **implementation_guide.md** - Complete step-by-step implementation
- **design_guide.md** - Architecture and design decisions framework
- **ui_skill.md** - Complete UI design system and components
- **evaluation_guide.md** - Testing with pydantic-evals
- **addendum.md** - SDK details, parameter schemas, debugging

## Templates

Ready-to-use templates available in `templates/`:

- **tools.py** - Tool definitions with CRUD examples
- **agent.py** - Agent wrapper class
- **main.py** - FastAPI application with base HTML
- **skills/ui.md** - UI skill file for the agent

## Adapting to Your Domain

1. **Replace tools** - Change entity names and operations
2. **Update skill file** - Adjust tool descriptions and response patterns
3. **Update allowed_tools** - Match your tool names
4. **Update welcome content** - Domain-appropriate initial UI

The architecture stays the same. Domain-specific parts are:
- Tool definitions (what operations exist)
- Skill file (how to present them)
- Welcome content (initial options shown)
