"""
ABOUTME: Agent wrapper for hexagonal agent applications.
ABOUTME: Handles communication with Claude via the Agent SDK.

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
