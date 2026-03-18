---
name: hexagonal-agents
description: >
  MUST use when building web apps where an AI agent generates HTML UI dynamically. Use INSTEAD OF
  superpowers:brainstorming or impeccable:frontend-design when the architecture is agent-driven
  (Claude Agent SDK + FastAPI + HTMX). Trigger: "build an agent app", "AI-driven web UI", "hexagonal
  architecture", "ports and adapters", "agent that generates HTML", "HTMX with Claude agent", or any
  request for a web app where the AI agent IS the rendering layer, not just a backend service.
---

# Hexagonal Agent Application

## Goal

Build web applications where an AI agent serves as the UI layer, dynamically generating HTML in response to user messages. The agent sits at the center of a hexagonal architecture — tools handle data (ports), FastAPI/HTMX handle transport (adapters), and a skill file teaches the agent its entire UI vocabulary.

## Dependencies

### Tools

- **Write** — Creates project files (tools.py, agent.py, main.py, skill file)
- **Bash** — Runs `uv init`, `uv add`, `uv run uvicorn`

### Connectors

- **Claude Agent SDK** — `claude_agent_sdk` package. Provides `ClaudeSDKClient`, `ClaudeAgentOptions`, `TextBlock`, `@tool`, `create_sdk_mcp_server`.
- **FastAPI** — HTTP adapter. Receives requests, passes to agent, returns HTML.
- **HTMX** — Client-side partial updates. Loaded via CDN in base template.
- **Tailwind CSS** — Utility-first styling. Loaded via CDN.
- **Anthropic API key** — `ANTHROPIC_API_KEY` environment variable.

## Context

### Architecture

```
Browser (static shell + HTMX)
    │ POST /agent {message: "..."}
    ▼
FastAPI (HTTP Adapter)
    │ agent.process(message)
    ▼
Agent (ClaudeSDKClient)
    │ System prompt = skill file
    │ Calls tools for data, generates HTML
    ▼
Tools (MCP Server)
    │ Pure data operations → JSON
```

- **Browser** — Displays static shell + agent-generated HTML, uses HTMX for partial updates
- **FastAPI** — Receives HTTP, passes messages to agent, returns HTML
- **Agent** — Receives messages, calls tools for data, generates HTML responses
- **Tools** — Pure data operations (CRUD) returning structured JSON

### Key Principles

1. **Semantic Late Binding** — Agent interprets user intent at runtime, choosing tools and UI dynamically
2. **Separation of Concerns** — Tools handle data, agent handles presentation, HTTP handles transport
3. **Single Source of Truth** — The skill file defines the agent's entire UI vocabulary
4. **Message-Passing Paradigm** — Agent is a "prompt object" that receives semantic messages and responds with behavior

### Tool Design

Tools are the agent's interface to data. Each tool:
- Does ONE thing (single responsibility)
- Returns structured JSON (not formatted strings)
- Has a clear description of WHEN to use it

```python
@tool("list_items", "Get all items. Returns array of items with id, name, status.", {})
async def list_items(args: dict[str, Any]) -> dict[str, Any]:
    items = load_items()
    return {"content": [{"type": "text", "text": json.dumps({"items": items, "count": len(items)})}]}
```

Return format: `{"content": [{"type": "text", "text": json.dumps(data)}]}`. Errors: add `"is_error": True`.

Tool names in `allowed_tools` must follow: `mcp__{server_key}__{tool_name}`

### Skill File Requirements

The skill file (`app/skills/ui.md`) teaches the agent how to generate UI. Critical requirements:

1. **Raw HTML Output** — LLMs default to markdown. State "output raw HTML only" multiple times.
2. **Complete Component Patterns** — Show full HTML with all classes and HTMX attributes.
3. **HTMX Integration** — Every interactive element needs `hx-post`, `hx-target`, `hx-vals`.
4. **Tool-to-UI Mapping** — Explain when to call each tool and what UI to render.

Every button: `<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'>`
Every form: `<form hx-post="/agent" hx-target="#content">` with hidden `message` input.

### UI Design System and Components

For the complete design system (colors, typography, spacing) and full component library (cards, lists, forms, alerts, empty states, etc.):

→ **`references/component_library.md`**

### Architecture Deep Dive

For detailed hexagonal architecture explanation and SDK API details:

→ **`references/architecture.md`**
→ **`references/sdk_reference.md`**

## Process

### Step 0: Load Stored Feedback

Load any stored feedback preferences before starting:

```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents show-feedback
```

If feedback entries exist, apply them throughout app scaffolding:
- **architecture** → adjust project structure and module organization
- **tools** → guide MCP tool design patterns
- **skill_file** → shape agent skill file content and examples
- **ui_components** → adjust component selection and structure
- **styling** → calibrate Tailwind theme and design system defaults
- **agent_behavior** → strengthen or adjust agent instructions
- **general** → apply to all aspects of app generation

### Step 1: Initialize Project Structure

Locate the init script within this skill's directory and run it:

```bash
uv run {skill_root}/scripts/init_hexagonal_app.py my-app-name --domain items
```

Where `{skill_root}` is the installed path of this skill (e.g., the directory containing this SKILL.md). Alternatively, create the project structure manually following the layout below.

Creates:
```
my-app-name/
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── agent.py         # Agent wrapper
│   ├── tools.py         # MCP tool definitions
│   └── skills/
│       └── ui.md        # UI skill file
└── data/                # Created at runtime
```

### Step 2: Define Tools

Edit `app/tools.py`. Create an MCP server with CRUD operations:

```python
def create_tools_server():
    return create_sdk_mcp_server(
        name="app_tools", version="1.0.0",
        tools=[list_items, get_item, create_item, update_item, delete_item]
    )
```

### Step 3: Create the Skill File

Edit `app/skills/ui.md` to teach the agent its UI vocabulary. Structure:

```markdown
# Application UI Skill
## Critical Output Rules (raw HTML only, never markdown)
## Design System (colors, typography)
## Component Patterns (with full HTML examples)
## Available Tools (when to call each)
## Response Patterns (user intent → tool → UI)
```

Use components from `references/component_library.md`.

### Step 4: Configure the Agent

The agent wrapper (`app/agent.py`) connects everything:

```python
class Agent:
    def __init__(self):
        self.tools_server = create_tools_server()
        self._allowed_tools = ["mcp__app_tools__list_items", ...]

    async def _ensure_connected(self):
        skill_content = SKILL_PATH.read_text()
        options = ClaudeAgentOptions(
            system_prompt=skill_content,
            mcp_servers={"app_tools": self.tools_server},
            allowed_tools=self._allowed_tools,
            permission_mode="acceptEdits",
        )
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def process(self, message: str) -> str:
        await self._ensure_connected()
        await self.client.query(message)
        html_parts = []
        async for msg in self.client.receive_response():
            for block in msg.content:
                if isinstance(block, TextBlock):
                    html_parts.append(block.text)
        return self._clean_html("\n".join(html_parts))
```

### Step 5: Set Up HTTP Adapter

The FastAPI app (`app/main.py`) serves the base template and handles agent messages:

```python
@app.post("/agent", response_class=HTMLResponse)
async def handle_message(request: Request):
    form_data = await request.form()
    message = str(form_data.get("message", "")).strip()
    # Append extra form fields to message
    extra_fields = [f"{k}={v}" for k, v in form_data.items() if k != "message" and v]
    if extra_fields:
        message = f"{message} [{', '.join(extra_fields)}]"
    html = await agent.process(message)
    return html
```

### Human Checkpoint: Test Common Flows

Before considering the app ready, verify:

- [ ] List view (empty state)
- [ ] List view (with items)
- [ ] Create item (with form)
- [ ] Create item (natural language)
- [ ] View single item
- [ ] Update item
- [ ] Delete item
- [ ] Search/filter

### Step 6: Domain Adaptation

To adapt for a new domain:
1. **Define entities** — What are you managing? (books, tasks, recipes, tickets)
2. **Replace tools** — Change entity names, define domain-specific fields
3. **Update skill file** — Adjust tool list, response patterns, empty state messages
4. **Update agent** — Change `_allowed_tools` list
5. **Update welcome** — Domain-appropriate title and initial actions

## Output

A running hexagonal agent web application:

```bash
cd my-app-name
export ANTHROPIC_API_KEY=your_key_here
uv run uvicorn app.main:app --reload
# Open http://localhost:8000
```

### Advanced Evolution

As the app matures:

→ **`references/multi_agent_patterns.md`** — Specialized agents communicating via semantic messages
→ **`references/saved_views.md`** — Progressive UI caching to reduce latency and API costs
→ **`references/sqlite_persistence.md`** — Migrate from JSON to SQLite for ACID compliance
→ **`references/enhanced_ux.md`** — Animated loading states and visual feedback
→ **`references/eval_patterns.md`** — Systematic testing with pydantic-evals

### Debugging

For common issues (agent outputs markdown instead of HTML, tools not being called, HTMX not working, blank responses):

→ **`references/debugging.md`**
