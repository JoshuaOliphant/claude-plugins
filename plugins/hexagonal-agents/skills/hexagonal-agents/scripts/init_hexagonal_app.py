#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ABOUTME: PEP 723 script that scaffolds a new hexagonal agent application.
# ABOUTME: Creates project structure with tools, agent wrapper, FastAPI app, and skill file.

"""
Hexagonal Agent Application Scaffolder

Creates a complete project structure for a hexagonal agent application.

Usage:
    uv run init_hexagonal_app.py my-app-name --domain books
    uv run init_hexagonal_app.py task-tracker --domain tasks
"""

import argparse
import os
from pathlib import Path
from textwrap import dedent


def create_pyproject(project_dir: Path, project_name: str) -> None:
    """Create pyproject.toml with uv-compatible dependencies."""
    content = dedent(f'''\
        [project]
        name = "{project_name}"
        version = "0.1.0"
        description = "Hexagonal agent application"
        requires-python = ">=3.11"
        dependencies = [
            "claude-agent-sdk>=0.1.0",
            "fastapi>=0.109.0",
            "uvicorn[standard]>=0.27.0",
            "python-multipart>=0.0.6",
        ]

        [project.optional-dependencies]
        dev = [
            "pydantic-evals>=0.1.0",
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
        ]

        [tool.uv]
        dev-dependencies = [
            "pydantic-evals>=0.1.0",
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
        ]
    ''')
    (project_dir / "pyproject.toml").write_text(content)


def create_readme(project_dir: Path, project_name: str, domain: str) -> None:
    """Create README.md with usage instructions."""
    content = dedent(f'''\
        # {project_name}

        A hexagonal agent application for managing {domain}.

        ## Setup

        ```bash
        # Install dependencies
        uv sync

        # Set API key
        export ANTHROPIC_API_KEY=your_key_here

        # Run the application
        uv run uvicorn app.main:app --reload
        ```

        Open http://localhost:8000 in your browser.

        ## Architecture

        This application uses the hexagonal (ports-and-adapters) pattern:

        - **Tools** (`app/tools.py`): Data operations (CRUD)
        - **Agent** (`app/agent.py`): UI generation via Claude
        - **HTTP Adapter** (`app/main.py`): FastAPI endpoints
        - **Skill File** (`app/skills/ui.md`): UI vocabulary and patterns

        ## Development

        ```bash
        # Run tests
        uv run pytest

        # Run evaluations
        uv run python -m evals.test_agent
        ```
    ''')
    (project_dir / "README.md").write_text(content)


def create_init(project_dir: Path) -> None:
    """Create empty __init__.py."""
    (project_dir / "app" / "__init__.py").write_text("")


def create_tools(project_dir: Path, domain: str, entity: str, entities: str) -> None:
    """Create tools.py with CRUD operations."""
    content = dedent(f'''\
        # ABOUTME: MCP tool definitions for {domain} management.
        # ABOUTME: Each tool handles one data operation, returns structured JSON.

        """
        Tool definitions for the {domain} application.

        Each tool:
        1. Does ONE thing
        2. Returns structured JSON data
        3. Includes everything the agent needs for UI generation
        4. Handles errors gracefully
        """

        from claude_agent_sdk import tool, create_sdk_mcp_server
        from typing import Any
        import json
        from pathlib import Path
        from datetime import datetime

        # === Data Persistence ===

        DATA_FILE = Path("data/{entities}.json")


        def _load_data() -> dict:
            """Load data from JSON file."""
            if not DATA_FILE.exists():
                return {{"{entities}": []}}
            try:
                return json.loads(DATA_FILE.read_text())
            except json.JSONDecodeError:
                return {{"{entities}": []}}


        def _save_data(data: dict) -> None:
            """Save data to JSON file."""
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(json.dumps(data, indent=2, default=str))


        def _success(data: Any) -> dict:
            """Format successful tool response."""
            return {{
                "content": [{{
                    "type": "text",
                    "text": json.dumps(data, default=str)
                }}]
            }}


        def _error(message: str) -> dict:
            """Format error tool response."""
            return {{
                "content": [{{
                    "type": "text",
                    "text": json.dumps({{"error": message}})
                }}],
                "is_error": True
            }}


        # === Tool Definitions ===

        @tool(
            "list_{entities}",
            "Get all {entities}. Returns array with id, name, status, created_at.",
            {{}}
        )
        async def list_{entities}(args: dict[str, Any]) -> dict[str, Any]:
            """List all {entities}."""
            data = _load_data()
            items = data.get("{entities}", [])
            return _success({{"{entities}": items, "count": len(items)}})


        @tool(
            "get_{entity}",
            "Get a specific {entity} by ID.",
            {{"id": str}}
        )
        async def get_{entity}(args: dict[str, Any]) -> dict[str, Any]:
            """Get a single {entity}."""
            data = _load_data()
            items = data.get("{entities}", [])

            for item in items:
                if item["id"] == args["id"]:
                    return _success({{"{entity}": item}})

            return _error(f"{entity.title()} not found: {{args['id']}}")


        @tool(
            "create_{entity}",
            "Create a new {entity}. Requires: name. Optional: description.",
            {{"name": str, "description": str | None}}
        )
        async def create_{entity}(args: dict[str, Any]) -> dict[str, Any]:
            """Create a new {entity}."""
            data = _load_data()
            items = data.setdefault("{entities}", [])

            item_id = str(len(items) + 1)

            item = {{
                "id": item_id,
                "name": args["name"],
                "description": args.get("description", ""),
                "status": "active",
                "created_at": datetime.now().isoformat()
            }}

            items.append(item)
            _save_data(data)

            return _success({{"{entity}": item, "message": "{entity.title()} created"}})


        @tool(
            "update_{entity}",
            "Update an existing {entity}. Requires: id. Optional: name, description, status.",
            {{"id": str, "name": str | None, "description": str | None, "status": str | None}}
        )
        async def update_{entity}(args: dict[str, Any]) -> dict[str, Any]:
            """Update a {entity}."""
            data = _load_data()
            items = data.get("{entities}", [])

            for item in items:
                if item["id"] == args["id"]:
                    if args.get("name"):
                        item["name"] = args["name"]
                    if args.get("description"):
                        item["description"] = args["description"]
                    if args.get("status"):
                        item["status"] = args["status"]

                    item["updated_at"] = datetime.now().isoformat()
                    _save_data(data)
                    return _success({{"{entity}": item, "message": "{entity.title()} updated"}})

            return _error(f"{entity.title()} not found: {{args['id']}}")


        @tool(
            "delete_{entity}",
            "Delete a {entity} by ID. This is permanent.",
            {{"id": str}}
        )
        async def delete_{entity}(args: dict[str, Any]) -> dict[str, Any]:
            """Delete a {entity}."""
            data = _load_data()
            items = data.get("{entities}", [])

            for i, item in enumerate(items):
                if item["id"] == args["id"]:
                    deleted = items.pop(i)
                    _save_data(data)
                    return _success({{"deleted": deleted, "message": "{entity.title()} deleted"}})

            return _error(f"{entity.title()} not found: {{args['id']}}")


        @tool(
            "search_{entities}",
            "Search {entities} by keyword. Searches name and description.",
            {{"query": str}}
        )
        async def search_{entities}(args: dict[str, Any]) -> dict[str, Any]:
            """Search {entities}."""
            data = _load_data()
            items = data.get("{entities}", [])
            query = args["query"].lower()

            matches = [
                item for item in items
                if query in item["name"].lower()
                or query in item.get("description", "").lower()
            ]

            return _success({{"{entities}": matches, "count": len(matches), "query": args["query"]}})


        # === MCP Server Creation ===

        def create_tools_server():
            """Create the MCP server with all tools."""
            return create_sdk_mcp_server(
                name="app_tools",
                version="1.0.0",
                tools=[
                    list_{entities},
                    get_{entity},
                    create_{entity},
                    update_{entity},
                    delete_{entity},
                    search_{entities},
                ]
            )
    ''')
    (project_dir / "app" / "tools.py").write_text(content)


def create_agent(project_dir: Path, entity: str, entities: str) -> None:
    """Create agent.py wrapper."""
    content = dedent(f'''\
        # ABOUTME: Agent wrapper that connects Claude SDK to the application.
        # ABOUTME: Loads skill file, registers tools, extracts HTML from responses.

        """
        Agent wrapper for the hexagonal agent pattern.

        Responsibilities:
        1. Load skill file into system prompt
        2. Connect tools via MCP server
        3. Process messages and extract HTML responses
        4. Handle errors gracefully
        """

        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
        )
        from pathlib import Path
        from app.tools import create_tools_server

        SKILL_PATH = Path(__file__).parent / "skills" / "ui.md"


        def _load_skill_file() -> str:
            """Load the skill file content."""
            if SKILL_PATH.exists():
                return SKILL_PATH.read_text()
            return ""


        def _build_system_prompt() -> str:
            """Build the complete system prompt."""
            skill_content = _load_skill_file()

            return f"""{{skill_content}}

        ## Final Reminders

        - Output ONLY raw HTML. No markdown. No code fences. No explanations.
        - Every interactive element needs hx-post="/agent" and hx-target="#content"
        - Use hx-vals to pass the message describing what action to take
        - When you receive form submissions, field values come as separate parameters alongside the message
        """


        class Agent:
            """Wrapper around ClaudeSDKClient for the hexagonal agent pattern."""

            def __init__(self):
                self.tools_server = create_tools_server()
                self.client: ClaudeSDKClient | None = None
                self._connected = False

                # Tool names: mcp__{{server_name}}__{{tool_name}}
                self._allowed_tools = [
                    "mcp__app_tools__list_{entities}",
                    "mcp__app_tools__get_{entity}",
                    "mcp__app_tools__create_{entity}",
                    "mcp__app_tools__update_{entity}",
                    "mcp__app_tools__delete_{entity}",
                    "mcp__app_tools__search_{entities}",
                ]

            async def _ensure_connected(self) -> None:
                """Initialize and connect the client if not already connected."""
                if self._connected and self.client:
                    return

                options = ClaudeAgentOptions(
                    system_prompt=_build_system_prompt(),
                    mcp_servers={{"app_tools": self.tools_server}},
                    allowed_tools=self._allowed_tools,
                    permission_mode="acceptEdits",
                )

                self.client = ClaudeSDKClient(options=options)
                await self.client.connect()
                self._connected = True

            async def process(self, message: str) -> str:
                """Process a user message and return HTML."""
                await self._ensure_connected()

                await self.client.query(message)

                html_parts: list[str] = []

                async for msg in self.client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                html_parts.append(block.text)

                html = "\\n".join(html_parts)
                return self._clean_html(html)

            def _clean_html(self, html: str) -> str:
                """Clean up the HTML response."""
                html = html.strip()

                if html.startswith("```html"):
                    html = html[7:]
                elif html.startswith("```"):
                    html = html[3:]

                if html.endswith("```"):
                    html = html[:-3]

                return html.strip()

            def _error_html(self, message: str) -> str:
                """Generate error display HTML."""
                return f\'\'\'
        <div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p class="text-red-300">{{message}}</p>
            <button hx-post="/agent" hx-target="#content" hx-vals=\'{{"message":"show {entities}"}}\'
                    class="mt-3 text-sm text-slate-400 hover:text-white">
                ← Back to list
            </button>
        </div>
        \'\'\'

            async def reset(self) -> None:
                """Reset the conversation state."""
                if self.client:
                    await self.client.disconnect()
                    self.client = None
                    self._connected = False

            async def close(self) -> None:
                """Clean up resources."""
                await self.reset()
    ''')
    (project_dir / "app" / "agent.py").write_text(content)


def create_main(project_dir: Path, project_name: str, domain: str, entity: str, entities: str) -> None:
    """Create main.py FastAPI application."""
    title = project_name.replace("-", " ").title()
    content = dedent(f'''\
        # ABOUTME: FastAPI application serving as the HTTP adapter for the hexagonal agent.
        # ABOUTME: Handles requests, passes messages to agent, returns HTML fragments.

        """
        FastAPI application - HTTP adapter for the hexagonal agent pattern.

        Responsibilities:
        1. Serve the base HTML template
        2. Handle /agent POST requests
        3. Return HTML fragments for HTMX to swap
        """

        from fastapi import FastAPI, Request
        from fastapi.responses import HTMLResponse
        from contextlib import asynccontextmanager

        from app.agent import Agent

        agent = Agent()


        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan - cleanup on shutdown."""
            yield
            await agent.close()


        app = FastAPI(lifespan=lifespan)


        BASE_TEMPLATE = \'\'\'<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <script src="https://unpkg.com/htmx.org@1.9.10"></script>
            <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
            <style>
                .htmx-request .loading-indicator {{ display: flex; }}
                .htmx-request #content {{ opacity: 0.6; pointer-events: none; }}
                .loading-indicator {{ display: none; }}
                @keyframes fadeSlideIn {{
                    from {{ opacity: 0; transform: translateY(8px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                .animate-in {{ animation: fadeSlideIn 0.3s ease-out; }}
            </style>
        </head>
        <body class="min-h-screen bg-slate-950 text-slate-100">
            <nav class="bg-slate-900 border-b border-slate-800">
                <div class="max-w-4xl mx-auto px-4 py-3 flex justify-between items-center">
                    <h1 class="text-xl font-bold font-[\'Space_Grotesk\']">{title}</h1>
                    <button hx-post="/reset" hx-target="#content"
                            class="text-sm text-slate-400 hover:text-white transition-colors">
                        Reset
                    </button>
                </div>
            </nav>

            <main class="max-w-4xl mx-auto p-4">
                <div class="loading-indicator items-center justify-center py-8">
                    <svg class="animate-spin h-8 w-8 text-indigo-500" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                </div>

                <div id="content">
                    {{content}}
                </div>
            </main>

            <footer class="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800">
                <form hx-post="/agent" hx-target="#content" class="max-w-4xl mx-auto p-4 flex gap-3">
                    <input type="text" name="message"
                           placeholder="What would you like to do?"
                           autocomplete="off"
                           class="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                                  text-white placeholder-slate-500
                                  focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
                    <button type="submit"
                            class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500
                                   text-white font-medium rounded-lg transition-colors">
                        Send
                    </button>
                </form>
            </footer>

            <div class="h-24"></div>

            <script>
                document.body.addEventListener(\'htmx:afterRequest\', function(event) {{
                    if (event.detail.elt.matches(\'form\')) {{
                        const input = event.detail.elt.querySelector(\'input[name="message"]\');
                        if (input) input.value = \'\';
                    }}
                }});
                document.querySelector(\'input[name="message"]\')?.focus();
            </script>
        </body>
        </html>\'\'\'


        WELCOME_CONTENT = \'\'\'
        <div class="text-center py-16 animate-in">
            <div class="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
                <span class="text-2xl">📋</span>
            </div>
            <h2 class="text-2xl font-bold font-[\'Space_Grotesk\'] text-white mb-4">Welcome</h2>
            <p class="text-slate-400 mb-8">What would you like to do today?</p>
            <div class="flex flex-wrap justify-center gap-3">
                <button hx-post="/agent" hx-target="#content" hx-vals=\'{{"message":"show my {entities}"}}\'
                        class="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors">
                    View {entities.title()}
                </button>
                <button hx-post="/agent" hx-target="#content" hx-vals=\'{{"message":"create a new {entity}"}}\'
                        class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors">
                    Create {entity.title()}
                </button>
            </div>
        </div>
        \'\'\'


        @app.get("/", response_class=HTMLResponse)
        async def home():
            """Serve the main page."""
            return BASE_TEMPLATE.format(content=WELCOME_CONTENT)


        @app.post("/agent", response_class=HTMLResponse)
        async def handle_message(request: Request):
            """Handle user messages sent to the agent."""
            form_data = await request.form()

            message = form_data.get("message", "")
            if not message or not str(message).strip():
                return \'<p class="text-amber-400">Please enter a message.</p>\'

            message = str(message).strip()

            # Append form fields to message
            extra_fields = []
            for key, value in form_data.items():
                if key != "message" and value:
                    extra_fields.append(f"{{key}}={{value}}")

            if extra_fields:
                message = f"{{message}} [{{', '.join(extra_fields)}}]"

            try:
                html = await agent.process(message)
                return html
            except Exception as e:
                print(f"Agent error: {{e}}")
                return \'\'\'
        <div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p class="text-red-300">An error occurred. Please try again.</p>
        </div>
        \'\'\'


        @app.post("/reset", response_class=HTMLResponse)
        async def reset():
            """Reset conversation state and return to welcome screen."""
            await agent.reset()
            return WELCOME_CONTENT
    ''')
    (project_dir / "app" / "main.py").write_text(content)


def create_skill_file(project_dir: Path, domain: str, entity: str, entities: str) -> None:
    """Create the UI skill file."""
    content = dedent(f'''\
        # {domain.title()} UI Skill

        You are an AI application that generates user interfaces for managing {domain}. You receive natural language requests and respond with HTML that will be displayed to the user.

        ## Critical Output Rules

        1. Output ONLY raw HTML — never wrap in markdown code fences
        2. Never include ```html or ``` markers
        3. Never include explanations outside of HTML
        4. All output must be valid HTML fragments
        5. Always use the component patterns below
        6. Always include HTMX attributes for interactive elements

        ## Design System

        ### Colors (Tailwind classes)
        - Page: bg-slate-950
        - Cards: bg-slate-900
        - Inputs: bg-slate-800
        - Borders: border-slate-800, border-slate-700
        - Text: text-white (headings), text-slate-300 (body), text-slate-400 (muted)
        - Primary: bg-indigo-600 hover:bg-indigo-500, text-indigo-400
        - Danger: text-red-400, bg-red-500/10
        - Success: text-emerald-400, bg-emerald-500/10
        - Warning: text-amber-400

        ### Typography
        - Page title: text-2xl font-bold font-['Space_Grotesk'] text-white
        - Section: text-xl font-semibold text-white
        - Card title: text-lg font-medium text-white
        - Body: text-slate-300
        - Caption: text-sm text-slate-400

        ## Component Patterns

        ### Page Header
        ```html
        <div class="flex justify-between items-center mb-8 animate-in">
          <div>
            <h1 class="text-2xl font-bold font-['Space_Grotesk'] text-white">Title</h1>
            <p class="text-slate-400 mt-1">Supporting context</p>
          </div>
          <button hx-post="/agent" hx-target="#content" hx-vals='{{"message":"action"}}'
                  class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                         shadow-lg shadow-indigo-500/25 transition-all duration-200">
            + New {entity.title()}
          </button>
        </div>
        ```

        ### Card
        ```html
        <div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden
                    shadow-lg shadow-slate-950/50 animate-in">
          <div class="p-5">
            <!-- content -->
          </div>
        </div>
        ```

        ### List Item
        ```html
        <div class="group flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800
                    hover:border-slate-700 hover:bg-slate-800/50 transition-all duration-200 cursor-pointer"
             hx-post="/agent" hx-target="#content" hx-vals='{{"message":"show {entity} ID"}}'>
          <div class="flex items-center gap-4">
            <div class="w-10 h-10 rounded-lg bg-indigo-600/20 flex items-center justify-center">
              <span class="text-indigo-400 font-semibold">A</span>
            </div>
            <div>
              <p class="font-medium text-white group-hover:text-indigo-300 transition-colors">Name</p>
              <p class="text-sm text-slate-400">Description</p>
            </div>
          </div>
          <div class="text-slate-400 group-hover:text-white transition-colors">→</div>
        </div>
        ```

        ### Primary Button
        ```html
        <button hx-post="/agent" hx-target="#content" hx-vals='{{"message":"action"}}'
                class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                       shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40
                       transition-all duration-200 active:scale-[0.98]">
          Button Text
        </button>
        ```

        ### Secondary Button
        ```html
        <button hx-post="/agent" hx-target="#content" hx-vals='{{"message":"action"}}'
                class="px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800
                       rounded-lg transition-all duration-200">
          Button Text
        </button>
        ```

        ### Danger Button
        ```html
        <button hx-post="/agent" hx-target="#content" hx-vals='{{"message":"delete {entity} ID"}}'
                class="px-4 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10
                       rounded-lg transition-all duration-200">
          Delete
        </button>
        ```

        ### Text Input
        ```html
        <input type="text" name="field" placeholder="Placeholder..."
               class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg
                      text-white placeholder-slate-500
                      focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                      transition-all duration-200">
        ```

        ### Form
        ```html
        <form hx-post="/agent" hx-target="#content" class="space-y-5 animate-in">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-2">Name</label>
            <input type="text" name="name" required
                   class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white
                          placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500
                          focus:border-transparent transition-all duration-200">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-2">Description</label>
            <textarea name="description" rows="3"
                      class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white
                             placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500
                             focus:border-transparent transition-all duration-200"></textarea>
          </div>
          <input type="hidden" name="message" value="create {entity} with name and description">
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" hx-post="/agent" hx-target="#content" hx-vals='{{"message":"show {entities}"}}'
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

        ### Empty State
        ```html
        <div class="text-center py-16 animate-in">
          <div class="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
            <span class="text-2xl">📋</span>
          </div>
          <h3 class="text-lg font-semibold text-white mb-2">No {entities} yet</h3>
          <p class="text-slate-400 mb-6">Get started by creating your first {entity}</p>
          <button hx-post="/agent" hx-target="#content" hx-vals='{{"message":"create new {entity}"}}'
                  class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                         shadow-lg shadow-indigo-500/25 transition-all">
            Create First {entity.title()}
          </button>
        </div>
        ```

        ### Success Alert
        ```html
        <div class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg animate-in mb-4">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
              <span class="text-emerald-400">✓</span>
            </div>
            <p class="text-emerald-300 font-medium">Success message</p>
          </div>
        </div>
        ```

        ### Error Alert
        ```html
        <div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg animate-in mb-4">
          <p class="text-red-300">Error message</p>
        </div>
        ```

        ## Available Tools

        1. **list_{entities}** — Get all {entities}. Call when user wants to see their {entities}.
        2. **get_{entity}** — Get one {entity} by ID. Call when user asks about a specific {entity}.
        3. **create_{entity}** — Create new {entity}. Requires: name. Optional: description.
        4. **update_{entity}** — Update {entity}. Requires: id. Optional: name, description, status.
        5. **delete_{entity}** — Delete {entity}. Requires: id.
        6. **search_{entities}** — Search {entities} by keyword.

        ## Response Patterns

        ### User wants to see {entities} ("show my {entities}", "list", "what do I have")
        1. Call list_{entities} tool
        2. If {entities} exist: render Page Header + list of items
        3. If no {entities}: render Empty State

        ### User wants to create ("add", "create", "new")
        If user provides the name:
        1. Call create_{entity} with the name
        2. Show Success Alert + the created {entity} card

        If user doesn't provide details:
        1. Show Form to collect name and description

        ### User wants to see one {entity} ("show {entity} 3", "details for...")
        1. Call get_{entity} with the ID
        2. Render detailed card view with edit/delete actions
        3. Include back link to list

        ### User wants to delete ("delete {entity} 3", "remove...")
        1. Call delete_{entity} with the ID
        2. Show Success Alert + link to view all {entities}

        ### User wants to update ("change", "edit", "update")
        If user provides what to change:
        1. Call update_{entity} with id and new values
        2. Show Success Alert + updated {entity}

        If user doesn't specify changes:
        1. Call get_{entity} first
        2. Show Form pre-filled with current values

        ### User asks conversational question
        Respond in a Card with helpful text. Include action buttons for likely next steps.

        ## Form Data Handling

        When a form is submitted, you receive the form fields AND the hidden message field.
        Parse the message to understand the intent, then use form field values.

        Example: Form with name="title" and message="create {entity} with name"
        When user enters "Buy groceries", you receive: message="create {entity} with name", title="Buy groceries"
        Action: Call create_{entity} with name="Buy groceries"
    ''')
    (project_dir / "app" / "skills" / "ui.md").write_text(content)


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a hexagonal agent application"
    )
    parser.add_argument(
        "project_name",
        help="Name of the project (used for directory and package name)"
    )
    parser.add_argument(
        "--domain",
        default="items",
        help="Domain name (e.g., books, tasks, recipes). Defaults to 'items'"
    )
    parser.add_argument(
        "--entity",
        help="Singular entity name. Defaults to domain without trailing 's'"
    )

    args = parser.parse_args()

    project_name = args.project_name
    domain = args.domain

    # Derive entity names
    if args.entity:
        entity = args.entity
        entities = f"{entity}s" if not entity.endswith("s") else entity
    else:
        # Simple pluralization
        if domain.endswith("s"):
            entities = domain
            entity = domain[:-1]
        else:
            entity = domain
            entities = f"{domain}s"

    # Create project directory
    project_dir = Path.cwd() / project_name
    if project_dir.exists():
        print(f"Error: Directory '{project_name}' already exists")
        return 1

    print(f"Creating hexagonal agent app: {project_name}")
    print(f"  Domain: {domain}")
    print(f"  Entity: {entity} / {entities}")

    # Create directory structure
    project_dir.mkdir()
    (project_dir / "app").mkdir()
    (project_dir / "app" / "skills").mkdir()

    # Create files
    create_pyproject(project_dir, project_name)
    create_readme(project_dir, project_name, domain)
    create_init(project_dir)
    create_tools(project_dir, domain, entity, entities)
    create_agent(project_dir, entity, entities)
    create_main(project_dir, project_name, domain, entity, entities)
    create_skill_file(project_dir, domain, entity, entities)

    print(f"\nProject created at: {project_dir}")
    print("\nNext steps:")
    print(f"  cd {project_name}")
    print("  uv sync")
    print("  export ANTHROPIC_API_KEY=your_key_here")
    print("  uv run uvicorn app.main:app --reload")

    return 0


if __name__ == "__main__":
    exit(main())
