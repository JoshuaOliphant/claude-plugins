# Hexagonal Agent Plugin

Build web applications where an AI agent generates UI dynamically based on user intent. The agent acts as the controller, calling tools to read/modify state and responding with HTML that HTMX swaps into the page.

## Features

- **Agent-Generated UI**: Claude generates HTML interfaces based on natural language
- **MCP Tools Integration**: Define tools for the agent to read and modify application state
- **HTMX-Powered**: Seamless updates without page reloads
- **Tailwind CSS**: Beautiful, responsive dark theme design system
- **FastAPI Backend**: Modern async Python web framework

## Architecture

```
Browser (HTMX) → FastAPI (HTTP Adapter) → Agent (Claude SDK) → Tools (MCP Server)
```

The hexagonal pattern separates concerns:
- **Tools**: Define what the agent CAN do (domain operations)
- **Skill File**: Teaches how the agent EXPRESSES itself (UI patterns)
- **HTTP Adapter**: Manages how users INTERACT (routing, sessions)

## Quick Start

```bash
# Create project
mkdir myapp && cd myapp
pip install claude-agent-sdk fastapi uvicorn python-multipart

# Copy templates from this plugin
# - templates/tools.py → app/tools.py
# - templates/agent.py → app/agent.py
# - templates/main.py → app/main.py
# - templates/skills/ui.md → app/skills/ui.md

# Run
export ANTHROPIC_API_KEY=your_key
uvicorn app.main:app --reload
```

## Installation

```bash
# Add the marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install the plugin
/plugin install hexagonal-agent@oliphant-plugins
```

## Documentation

- **SKILL.md**: Main skill documentation with quick reference
- **references/implementation_guide.md**: Step-by-step implementation
- **references/design_guide.md**: Architecture and design decisions
- **references/ui_skill.md**: Complete UI design system
- **references/evaluation_guide.md**: Testing with pydantic-evals
- **references/addendum.md**: SDK details and debugging

## Templates

Ready-to-use template files in `templates/`:

- `tools.py` - MCP tool definitions with CRUD examples
- `agent.py` - Agent wrapper class
- `main.py` - FastAPI application with base HTML
- `skills/ui.md` - UI skill file for the agent

## Use Cases

- Task management applications
- CRUD dashboards
- Conversational interfaces
- Data exploration tools
- Any application where natural language drives UI generation

## Requirements

- Python 3.11+
- Claude Agent SDK (claude-agent-sdk)
- FastAPI
- ANTHROPIC_API_KEY environment variable

## License

MIT
