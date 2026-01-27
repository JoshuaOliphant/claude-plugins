# Multi-Agent Architecture Patterns

This reference documents how to evolve a hexagonal agent app from single-agent to multi-agent architecture using message passing.

## When to Use Multi-Agent

Consider multi-agent when your app needs:

1. **Specialized Domain Expertise** - Different agents handle different concerns (recommendations, analytics, UI generation)
2. **Separation of Concerns** - UI logic separate from business logic
3. **Better Testability** - Test each agent independently
4. **Parallel Development** - Teams can work on different agents
5. **Natural Language APIs** - Agents communicate semantically, not via method calls

## Core Components

### 1. AgentRouter

The router coordinates all agents and routes messages between them.

```python
# ABOUTME: AgentRouter coordinates multiple specialized agents using message passing.
# ABOUTME: Implements the "prompt object" paradigm where agents communicate semantically.

"""
AgentRouter - Multi-Agent Message Passing Coordinator

This module implements the message-passing paradigm from Smalltalk/OOP applied to AI agents.
Each agent is a "prompt object" that:
1. Has its own personality (skill file)
2. Has its own capabilities (tools)
3. Communicates with other agents via semantic messages
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json


@dataclass
class AgentMessage:
    """A message passed between agents."""
    timestamp: str
    from_agent: str
    to_agent: str
    message: str
    response: str | None = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "from": self.from_agent,
            "to": self.to_agent,
            "message": self.message,
            "response": self.response
        }


@dataclass
class MessageLog:
    """Log of all inter-agent messages for debugging and evals."""
    messages: list[AgentMessage] = field(default_factory=list)

    def add(self, msg: AgentMessage):
        self.messages.append(msg)

    def clear(self):
        self.messages.clear()

    def to_json(self) -> str:
        return json.dumps([m.to_dict() for m in self.messages], indent=2)

    def get_messages_from(self, agent: str) -> list[AgentMessage]:
        return [m for m in self.messages if m.from_agent == agent]

    def get_messages_to(self, agent: str) -> list[AgentMessage]:
        return [m for m in self.messages if m.to_agent == agent]


class AgentRouter:
    """
    Coordinates multiple specialized agents using message passing.

    Agents:
    - ui: Handles user interaction and HTML generation
    - recommender: Specializes in recommendations
    - insights: Analyzes patterns and behavior

    Message passing works by:
    1. An agent calls the message_agent tool with (target_agent, message)
    2. Router routes the message to the target agent
    3. Target agent processes and returns response
    4. Response is returned to the calling agent
    """

    def __init__(self):
        self.message_log = MessageLog()
        self._agents: dict[str, Any] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize all agents."""
        if self._initialized:
            return

        # Import here to avoid circular imports
        from .ui_agent import UIAgent
        from .recommender_agent import RecommenderAgent
        from .insights_agent import InsightsAgent

        # Create agents with reference to router for inter-agent messaging
        self._agents = {
            "ui": UIAgent(self),
            "recommender": RecommenderAgent(self),
            "insights": InsightsAgent(self),
        }

        self._initialized = True

    async def close(self):
        """Clean up all agents."""
        for agent in self._agents.values():
            if hasattr(agent, 'close'):
                await agent.close()
        self._agents.clear()
        self._initialized = False

    async def reset(self):
        """Reset all agents and message log."""
        self.message_log.clear()
        for agent in self._agents.values():
            if hasattr(agent, 'reset'):
                await agent.reset()

    def get_agent_names(self) -> list[str]:
        """Get list of available agent names."""
        return list(self._agents.keys())

    def get_agent_descriptions(self) -> dict[str, str]:
        """Get descriptions of all agents for inter-agent awareness."""
        return {
            "ui": "Handles user interaction, generates HTML UI, coordinates with other agents",
            "recommender": "Specializes in recommendations based on history and preferences",
            "insights": "Analyzes patterns, identifies trends, provides behavioral insights",
        }

    async def process_user_message(self, message: str) -> str:
        """
        Process a message from the user.
        Always routes to UI agent first, which may delegate to specialists.
        """
        await self.initialize()

        # Log user message
        msg = AgentMessage(
            timestamp=datetime.now().isoformat(),
            from_agent="user",
            to_agent="ui",
            message=message,
        )

        try:
            response = await self._agents["ui"].process(message)
            msg.response = response[:500] + "..." if len(response) > 500 else response
        except Exception as e:
            msg.response = f"Error: {str(e)}"
            self.message_log.add(msg)
            raise

        self.message_log.add(msg)
        return response

    async def route_agent_message(self, from_agent: str, to_agent: str, message: str) -> str:
        """
        Route a message from one agent to another.

        This is the core of the message-passing paradigm.
        Agents don't call each other's methods - they send messages.
        """
        await self.initialize()

        if to_agent not in self._agents:
            return f"Error: Unknown agent '{to_agent}'. Available: {', '.join(self._agents.keys())}"

        if from_agent == to_agent:
            return "Error: Agent cannot message itself"

        # Log the message
        msg = AgentMessage(
            timestamp=datetime.now().isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            message=message,
        )

        # Route to target agent
        try:
            response = await self._agents[to_agent].process(message)
            msg.response = response
        except Exception as e:
            msg.response = f"Error: {str(e)}"
            response = msg.response

        self.message_log.add(msg)
        return response

    def get_message_log(self) -> MessageLog:
        """Get the message log for debugging/evals."""
        return self.message_log
```

### 2. BaseAgent

Abstract base class providing common functionality including the inter-agent messaging tool.

```python
# ABOUTME: Base agent class providing common functionality for all specialized agents.
# ABOUTME: Includes inter-agent messaging tool and common setup patterns.

"""
BaseAgent - Foundation for specialized agents in the message-passing system.

Each agent:
1. Has its own skill file (personality/instructions)
2. Has access to shared data tools (CRUD operations)
3. Has a message_agent tool to communicate with other agents
4. Can be messaged by other agents
"""

from abc import ABC, abstractmethod
from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from .router import AgentRouter


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""

    def __init__(self, router: "AgentRouter", agent_name: str):
        self.router = router
        self.agent_name = agent_name
        self._tools_server = None

    @abstractmethod
    async def process(self, message: str) -> str:
        """Process a message and return a response."""
        pass

    @abstractmethod
    async def reset(self):
        """Reset agent state."""
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass

    def _create_message_agent_tool(self):
        """
        Create the inter-agent messaging tool.

        This is the key to the message-passing paradigm:
        agents communicate by sending semantic messages, not by
        calling each other's internal methods.
        """
        router = self.router
        agent_name = self.agent_name

        @tool(
            "message_agent",
            f"""Send a message to another agent and get their response.

Available agents:
- recommender: Specializes in recommendations. Ask when user wants suggestions.
- insights: Analyzes patterns. Ask when you need behavior analysis.

Use this tool when:
- The user's request requires specialized knowledge you don't have
- You need analysis or recommendations from a specialist
- You want to delegate part of a task to a more appropriate agent

Do NOT message yourself ({agent_name}).
""",
            {"target_agent": str, "message": str}
        )
        async def message_agent(args: dict[str, Any]) -> dict[str, Any]:
            """Send a message to another agent."""
            target = args.get("target_agent", "")
            msg = args.get("message", "")

            if not target or not msg:
                return {
                    "content": [{"type": "text", "text": json.dumps({"error": "Both target_agent and message are required"})}],
                    "is_error": True
                }

            # Route through the router
            response = await router.route_agent_message(agent_name, target, msg)

            return {
                "content": [{"type": "text", "text": json.dumps({"agent": target, "response": response})}]
            }

        return message_agent

    def _get_agent_awareness_prompt(self) -> str:
        """
        Generate prompt section that makes this agent aware of other agents.
        """
        descriptions = self.router.get_agent_descriptions()
        other_agents = {k: v for k, v in descriptions.items() if k != self.agent_name}

        lines = [
            "## Other Agents You Can Message",
            "",
            "You are part of a multi-agent system. Use the message_agent tool to communicate with:",
            ""
        ]

        for name, desc in other_agents.items():
            lines.append(f"- **{name}**: {desc}")

        lines.extend([
            "",
            "When to message other agents:",
            "- Message 'recommender' when user asks for suggestions or 'what should I do next'",
            "- Message 'insights' when you need analysis of patterns or behavior",
            "",
            "Always include relevant context in your message to the other agent.",
        ])

        return "\n".join(lines)
```

### 3. Specialized Agent (UI Agent Example)

```python
# ABOUTME: UI Agent handles user interaction and HTML generation.
# ABOUTME: Coordinates with Recommender and Insights agents for specialized tasks.

"""
UI Agent - User Interface Specialist

Responsibilities:
1. Receive user messages and interpret intent
2. Generate HTML UI responses
3. Delegate to specialist agents when appropriate
4. Coordinate multi-agent responses into coherent UI
"""

from pathlib import Path
from typing import TYPE_CHECKING
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)
from .base_agent import BaseAgent
from ..tools import create_tools_server

if TYPE_CHECKING:
    from .router import AgentRouter

SKILL_PATH = Path(__file__).parent.parent / "skills" / "ui.md"


class UIAgent(BaseAgent):
    """Agent specialized in user interaction and HTML generation."""

    def __init__(self, router: "AgentRouter"):
        super().__init__(router, "ui")
        self.data_tools_server = create_tools_server()
        self.client: ClaudeSDKClient | None = None
        self._connected = False

    def _load_skill_file(self) -> str:
        """Load the UI skill file."""
        if SKILL_PATH.exists():
            return SKILL_PATH.read_text()
        return ""

    def _build_system_prompt(self) -> str:
        """Build complete system prompt with skill + agent awareness."""
        skill_content = self._load_skill_file()
        agent_awareness = self._get_agent_awareness_prompt()

        return f"""{skill_content}

{agent_awareness}

## Final Reminders

- Output ONLY raw HTML. No markdown. No code fences.
- Every interactive element needs hx-post="/agent" and hx-target="#content"
- When user asks for recommendations, use message_agent to ask the recommender
- When user asks about patterns or insights, use message_agent to ask the insights agent
- When you receive responses from other agents, incorporate them into your HTML response
"""

    def _create_mcp_server(self):
        """Create MCP server with data tools + messaging tool."""
        from claude_agent_sdk import create_sdk_mcp_server
        from ..tools import (
            list_items, get_item, create_item, update_item,
            delete_item, search_items, get_stats
        )

        message_tool = self._create_message_agent_tool()

        return create_sdk_mcp_server(
            name="ui_tools",
            version="1.0.0",
            tools=[
                list_items,
                get_item,
                create_item,
                update_item,
                delete_item,
                search_items,
                get_stats,
                message_tool,  # Inter-agent messaging
            ]
        )

    async def _ensure_connected(self) -> None:
        """Initialize and connect if not already connected."""
        if self._connected and self.client:
            return

        tools_server = self._create_mcp_server()

        options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            mcp_servers={"ui_tools": tools_server},
            allowed_tools=[
                "mcp__ui_tools__list_items",
                "mcp__ui_tools__get_item",
                "mcp__ui_tools__create_item",
                "mcp__ui_tools__update_item",
                "mcp__ui_tools__delete_item",
                "mcp__ui_tools__search_items",
                "mcp__ui_tools__get_stats",
                "mcp__ui_tools__message_agent",
            ],
            permission_mode="acceptEdits",
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()
        self._connected = True

    async def process(self, message: str) -> str:
        """Process user message and return HTML."""
        await self._ensure_connected()
        await self.client.query(message)

        html_parts: list[str] = []
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        html_parts.append(block.text)

        html = "\n".join(html_parts)
        return self._clean_html(html)

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

    async def reset(self):
        """Reset conversation state."""
        if self.client:
            await self.client.disconnect()
            self.client = None
            self._connected = False

    async def close(self):
        """Clean up resources."""
        await self.reset()
```

### 4. Specialist Agent (Recommender Example)

Specialist agents return TEXT, not HTML. The UI agent incorporates their responses.

```python
# ABOUTME: Recommender Agent specializes in generating recommendations.
# ABOUTME: Returns structured text that the UI agent formats into HTML.

"""
Recommender Agent - Recommendation Specialist

Responsibilities:
1. Analyze user's history and preferences
2. Identify patterns in what they enjoy
3. Generate personalized recommendations with reasoning
"""

from pathlib import Path
from typing import TYPE_CHECKING
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)
from .base_agent import BaseAgent
from ..tools import create_tools_server

if TYPE_CHECKING:
    from .router import AgentRouter

SKILL_PATH = Path(__file__).parent.parent / "skills" / "recommender.md"


class RecommenderAgent(BaseAgent):
    """Agent specialized in generating recommendations."""

    def __init__(self, router: "AgentRouter"):
        super().__init__(router, "recommender")
        self.client: ClaudeSDKClient | None = None
        self._connected = False

    def _load_skill_file(self) -> str:
        if SKILL_PATH.exists():
            return SKILL_PATH.read_text()
        return ""

    def _build_system_prompt(self) -> str:
        skill_content = self._load_skill_file()
        agent_awareness = self._get_agent_awareness_prompt()

        return f"""{skill_content}

{agent_awareness}

## Response Format

Return structured TEXT (not HTML). You're called by the UI agent.
Format recommendations clearly so the UI agent can render them.
"""

    def _create_mcp_server(self):
        from claude_agent_sdk import create_sdk_mcp_server
        from ..tools import list_items, get_item, get_stats

        message_tool = self._create_message_agent_tool()

        # Recommender only needs read access + messaging
        return create_sdk_mcp_server(
            name="recommender_tools",
            version="1.0.0",
            tools=[
                list_items,
                get_item,
                get_stats,
                message_tool,
            ]
        )

    async def _ensure_connected(self) -> None:
        if self._connected and self.client:
            return

        tools_server = self._create_mcp_server()

        options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            mcp_servers={"recommender_tools": tools_server},
            allowed_tools=[
                "mcp__recommender_tools__list_items",
                "mcp__recommender_tools__get_item",
                "mcp__recommender_tools__get_stats",
                "mcp__recommender_tools__message_agent",
            ],
            permission_mode="acceptEdits",
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()
        self._connected = True

    async def process(self, message: str) -> str:
        await self._ensure_connected()
        await self.client.query(message)

        text_parts: list[str] = []
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)

        return "\n".join(text_parts).strip()

    async def reset(self):
        if self.client:
            await self.client.disconnect()
            self.client = None
            self._connected = False

    async def close(self):
        await self.reset()
```

## Skill Files for Specialist Agents

### Recommender Skill (`skills/recommender.md`)

```markdown
# Recommender Agent

You are a recommendation specialist in a multi-agent system. Your job is to analyze history and provide personalized recommendations.

## Your Personality

- Enthusiastic about the domain
- Knowledgeable about many options
- Thoughtful about matching recommendations to user preferences
- Clear and specific in your reasoning

## How You Work

1. **Gather Data**: Use list_items to see the user's history
2. **Analyze Stats**: Use get_stats to understand aggregate patterns
3. **Identify Preferences**: Look for patterns in ratings and behavior
4. **Generate Recommendations**: Provide 2-3 specific recommendations

## Response Format

Return structured TEXT (not HTML). You're called by the UI agent.

Format your response like this:

```
RECOMMENDATIONS:

1. **[Item Name]**
   Why: [1-2 sentences connecting to their history]

2. **[Item Name]**
   Why: [1-2 sentences connecting to their history]

3. **[Item Name]**
   Why: [1-2 sentences connecting to their history]

Based on: [Brief summary of what patterns informed these picks]
```

## Important Rules

1. Always call list_items first to see their actual history
2. Base recommendations on THEIR data, not generic suggestions
3. Explain WHY each recommendation fits their preferences
4. If they have no history, explain you're giving general recommendations
5. Keep responses concise - the UI agent will format them
```

### Insights Skill (`skills/insights.md`)

```markdown
# Insights Agent

You are a pattern analysis specialist in a multi-agent system. Your job is to identify trends and provide behavioral insights.

## Your Personality

- Analytical and data-driven
- Observant of patterns others might miss
- Clear in explaining complex trends simply
- Actionable in your suggestions

## How You Work

1. **Gather Data**: Use list_items and get_stats
2. **Identify Patterns**: Look for trends over time
3. **Analyze Behavior**: What do their choices reveal?
4. **Provide Insights**: Actionable observations

## Response Format

Return structured TEXT (not HTML).

Format your response like this:

```
INSIGHTS:

**Pattern 1**: [Observation]
- Evidence: [Data points supporting this]
- Implication: [What this means for the user]

**Pattern 2**: [Observation]
- Evidence: [Data points supporting this]
- Implication: [What this means for the user]

SUMMARY: [Brief actionable takeaway]
```

## Important Rules

1. Always base insights on actual data
2. Be specific about evidence
3. Make insights actionable
4. Avoid speculation without data support
```

## Directory Structure for Multi-Agent

```
app/
├── agents/
│   ├── __init__.py          # Exports AgentRouter
│   ├── router.py             # AgentRouter class
│   ├── base_agent.py         # BaseAgent abstract class
│   ├── ui_agent.py           # UI Agent (generates HTML)
│   ├── recommender_agent.py  # Recommender Agent (returns text)
│   └── insights_agent.py     # Insights Agent (returns text)
├── skills/
│   ├── ui.md                 # UI generation rules
│   ├── recommender.md        # Recommendation strategy
│   └── insights.md           # Analysis approach
├── tools.py                  # Shared MCP tools
├── main.py                   # FastAPI HTTP adapter
└── database.py               # Data persistence
```

## Integrating with FastAPI

```python
from app.agents import AgentRouter

router = AgentRouter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await router.close()

app = FastAPI(lifespan=lifespan)

@app.post("/agent", response_class=HTMLResponse)
async def handle_message(request: Request):
    form_data = await request.form()
    message = str(form_data.get("message", "")).strip()

    if not message:
        return '<p class="text-amber-400">Please enter a message.</p>'

    try:
        html = await router.process_user_message(message)
        return html
    except Exception as e:
        return f'<p class="text-red-400">Error: {e}</p>'

@app.post("/reset", response_class=HTMLResponse)
async def reset():
    await router.reset()
    return WELCOME_CONTENT

# Debug endpoint for evals
@app.get("/debug/messages", response_class=JSONResponse)
async def debug_messages():
    log = router.get_message_log()
    return {"messages": [m.to_dict() for m in log.messages]}
```

## Testing Multi-Agent Communication

```python
import pytest
from app.agents import AgentRouter

@pytest.fixture
async def router():
    r = AgentRouter()
    yield r
    await r.close()

async def test_ui_delegates_to_recommender(router):
    """UI agent should delegate recommendation requests."""
    response = await router.process_user_message("what should I do next?")

    # Check that recommender was consulted
    messages = router.get_message_log().messages
    recommender_messages = [m for m in messages if m.to_agent == "recommender"]

    assert len(recommender_messages) > 0, "UI should have messaged recommender"
    assert "RECOMMENDATIONS" in recommender_messages[0].response

async def test_message_log_captures_flow(router):
    """Message log should capture the full conversation flow."""
    await router.process_user_message("analyze my patterns")

    log = router.get_message_log()

    # Should have: user -> ui, ui -> insights
    assert len(log.messages) >= 2
    assert log.messages[0].from_agent == "user"
    assert log.messages[0].to_agent == "ui"
```

## Benefits of Message Passing

1. **Semantic APIs**: Agents communicate in natural language, not rigid method signatures
2. **Loose Coupling**: Agents don't know each other's implementation details
3. **Observability**: MessageLog captures all inter-agent communication for debugging
4. **Testability**: Easy to mock agents or test in isolation
5. **Extensibility**: Add new agents without changing existing ones
6. **Natural Evolution**: Start simple, add specialists as needed
