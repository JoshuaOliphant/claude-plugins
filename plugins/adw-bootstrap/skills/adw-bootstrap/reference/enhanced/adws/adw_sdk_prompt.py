#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic",
#   "python-dotenv",
#   "click",
#   "rich",
#   "claude-code-sdk",
#   "anyio",
# ]
# ///
"""
Run Claude Code prompts using the official Python SDK.

This ADW demonstrates using the Claude Code Python SDK for both one-shot
and interactive sessions. The SDK provides better type safety, error handling,
and a more Pythonic interface compared to subprocess-based implementations.

Usage:
    # One-shot query (default)
    ./adws/adw_sdk_prompt.py "Hello Claude Code"

    # Interactive session
    ./adws/adw_sdk_prompt.py --interactive

    # Resume a previous session
    ./adws/adw_sdk_prompt.py --interactive --session-id abc123

    # With specific model
    ./adws/adw_sdk_prompt.py "Create a FastAPI app" --model opus

    # From different directory
    ./adws/adw_sdk_prompt.py "List files here" --working-dir /path/to/project

Examples:
    # Simple query
    ./adws/adw_sdk_prompt.py "Explain async/await in Python"

    # Interactive debugging session
    ./adws/adw_sdk_prompt.py --interactive --context "Debugging a memory leak"

    # Resume session with context
    ./adws/adw_sdk_prompt.py --interactive --session-id abc123 --context "Continue debugging"

    # Query with tools
    ./adws/adw_sdk_prompt.py "Create a Python web server" --tools Read,Write,Bash

Key Features:
    - Uses official Claude Code Python SDK
    - Supports both one-shot and interactive modes
    - Better error handling with typed exceptions
    - Native async/await support
    - Clean message type handling
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.prompt import Prompt

# Add the adw_modules directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "adw_modules"))

# Import SDK functions from our clean module
from agent_sdk import (
    simple_query,
    query_with_tools,
    collect_query_response,
    create_session,
    safe_query,
    stream_with_progress,
    extract_text,
    extract_tool_uses,
)

# Import SDK types
from claude_code_sdk import (
    ClaudeCodeOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


def generate_short_id() -> str:
    """Generate a short ID for tracking."""
    import uuid

    return str(uuid.uuid4())[:8]


async def run_one_shot_query(
    prompt: str,
    model: str,
    working_dir: str,
    allowed_tools: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> None:
    """Run a one-shot query using the SDK."""
    console = Console()
    adw_id = generate_short_id()

    # Display execution info
    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_column(style="bold cyan")
    info_table.add_column()

    info_table.add_row("ADW ID", adw_id)
    info_table.add_row("Mode", "One-shot Query")
    info_table.add_row("Prompt", prompt)
    info_table.add_row("Model", model)
    info_table.add_row("Working Dir", working_dir)
    if allowed_tools:
        info_table.add_row("Tools", ", ".join(allowed_tools))
    if session_id:
        info_table.add_row("Session ID", session_id)
    info_table.add_row("[bold green]SDK[/bold green]", "Claude Code Python SDK")

    console.print(
        Panel(
            info_table,
            title="[bold blue]🚀 SDK Query Execution[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    try:
        # Execute query based on whether tools are needed
        with console.status("[bold yellow]Executing via SDK...[/bold yellow]"):
            if allowed_tools:
                # Query with tools
                options = ClaudeCodeOptions(
                    model=model,
                    allowed_tools=allowed_tools,
                    cwd=working_dir,
                    permission_mode="bypassPermissions",
                )
                if session_id:
                    options.resume = session_id
                messages, result = await collect_query_response(prompt, options=options)

                # Extract response text
                response_text = ""
                tool_uses = []

                for msg in messages:
                    if isinstance(msg, AssistantMessage):
                        text = extract_text(msg)
                        if text:
                            response_text += text + "\n"
                        for tool in extract_tool_uses(msg):
                            tool_uses.append(f"{tool.name} ({tool.id[:8]}...)")

                success = result and not result.is_error if result else False

            else:
                # Simple query
                response_text, error = await safe_query(prompt)
                success = error is None
                tool_uses = []

                if error:
                    response_text = error

        # Display result
        if success:
            console.print(
                Panel(
                    response_text.strip(),
                    title="[bold green]✅ SDK Success[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )

            if tool_uses:
                console.print(
                    f"\n[bold cyan]Tools used:[/bold cyan] {', '.join(tool_uses)}"
                )
        else:
            console.print(
                Panel(
                    response_text,
                    title="[bold red]❌ SDK Error[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )

        # Show cost and session info if available
        if "result" in locals() and result:
            if result.total_cost_usd:
                console.print(
                    f"\n[bold cyan]Cost:[/bold cyan] ${result.total_cost_usd:.4f}"
                )
            if hasattr(result, 'session_id') and result.session_id:
                console.print(
                    f"[bold cyan]Session ID:[/bold cyan] {result.session_id}"
                )
                console.print(
                    f"[dim]Resume with: --session-id {result.session_id}[/dim]"
                )

    except Exception as e:
        console.print(
            Panel(
                f"[bold red]{str(e)}[/bold red]",
                title="[bold red]❌ Unexpected Error[/bold red]",
                border_style="red",
            )
        )


async def run_interactive_session(
    model: str,
    working_dir: str,
    context: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Run an interactive session using the SDK."""
    console = Console()
    adw_id = generate_short_id()

    # Display session info
    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_column(style="bold cyan")
    info_table.add_column()

    info_table.add_row("ADW ID", adw_id)
    info_table.add_row("Mode", "Interactive Session")
    info_table.add_row("Model", model)
    info_table.add_row("Working Dir", working_dir)
    if context:
        info_table.add_row("Context", context)
    if session_id:
        info_table.add_row("Session ID", session_id)
    info_table.add_row("[bold green]SDK[/bold green]", "Claude Code Python SDK")

    console.print(
        Panel(
            info_table,
            title="[bold blue]💬 SDK Interactive Session[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    # Instructions
    console.print("[bold yellow]Interactive Mode[/bold yellow]")
    console.print("Commands: 'exit' or 'quit' to end session")
    console.print("Just type your questions or requests\n")

    # Start session
    options = ClaudeCodeOptions(
        model=model,
        cwd=working_dir,
        permission_mode="bypassPermissions",
    )
    if session_id:
        options.resume = session_id
    
    from claude_code_sdk import ClaudeSDKClient
    client = ClaudeSDKClient(options=options)
    await client.connect()
    
    # Track session ID from results throughout the session
    session_id_from_result = None
    
    try:
        # Send initial context if provided
        if context:
            console.print(f"[dim]Setting context: {context}[/dim]\n")
            await client.query(f"Context: {context}")

            # Consume the context response
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    text = extract_text(msg)
                    if text:
                        console.print(f"[dim]Claude: {text}[/dim]\n")

        # Interactive loop
        while True:
            # Get user input
            try:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Session interrupted[/yellow]")
                break

            if user_input.lower() in ["exit", "quit"]:
                break

            # Send to Claude
            await client.query(user_input)

            # Show response with progress
            console.print()
            response_parts = []
            tool_uses = []
            cost = None
            session_id_from_result = None

            with Live(
                Spinner("dots", text="Thinking..."),
                console=console,
                refresh_per_second=4,
            ):
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        text = extract_text(msg)
                        if text:
                            response_parts.append(text)

                        for tool in extract_tool_uses(msg):
                            tool_uses.append(f"{tool.name}")

                    elif isinstance(msg, ResultMessage):
                        if msg.total_cost_usd:
                            cost = msg.total_cost_usd
                        if hasattr(msg, 'session_id') and msg.session_id:
                            session_id_from_result = msg.session_id

            # Display response
            if response_parts:
                console.print("[bold green]Claude:[/bold green]")
                for part in response_parts:
                    console.print(part)

            if tool_uses:
                console.print(f"\n[dim]Tools used: {', '.join(tool_uses)}[/dim]")

            if cost:
                console.print(f"[dim]Cost: ${cost:.4f}[/dim]")
            
            if session_id_from_result:
                console.print(f"[dim]Session ID: {session_id_from_result}[/dim]")

            console.print()
    
    finally:
        await client.disconnect()

    console.print("\n[bold green]Session ended[/bold green]")
    console.print(f"[dim]ADW ID: {adw_id}[/dim]")
    if 'session_id_from_result' in locals() and session_id_from_result:
        console.print(f"[bold cyan]Session ID:[/bold cyan] {session_id_from_result}")
        console.print(f"[dim]Resume with: ./adws/adw_sdk_prompt.py --interactive --session-id {session_id_from_result}[/dim]")


@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start an interactive session instead of one-shot query",
)
@click.option(
    "--model",
    type=click.Choice(["sonnet", "opus", "haiku"]),
    default="sonnet",
    help="Claude model to use (sonnet=balanced, opus=max intelligence, haiku=fast & economical)",
)
@click.option(
    "--working-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help="Working directory (default: current directory)",
)
@click.option(
    "--tools",
    help="Comma-separated list of allowed tools (e.g., Read,Write,Bash)",
)
@click.option(
    "--context",
    help="Context for interactive session (e.g., 'Debugging a memory leak')",
)
@click.option(
    "--session-id",
    help="Resume a previous session by its ID",
)
def main(
    prompt: Optional[str],
    interactive: bool,
    model: str,
    working_dir: Optional[str],
    tools: Optional[str],
    context: Optional[str],
    session_id: Optional[str],
):
    """Run Claude Code prompts using the Python SDK.

    Examples:
        # One-shot query
        adw_sdk_prompt.py "What is 2 + 2?"

        # Interactive session
        adw_sdk_prompt.py --interactive
        
        # Resume session
        adw_sdk_prompt.py --interactive --session-id abc123

        # Query with tools
        adw_sdk_prompt.py "Create hello.py" --tools Write,Read
    """
    if not working_dir:
        working_dir = os.getcwd()

    # Convert model names
    model_map = {
        "sonnet": "claude-sonnet-4-5-20250929",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-haiku-4-5-20251001"
    }
    full_model = model_map.get(model, model)

    # Parse tools if provided
    allowed_tools = None
    if tools:
        allowed_tools = [t.strip() for t in tools.split(",")]

    # Run appropriate mode
    if interactive:
        if prompt:
            console = Console()
            console.print(
                "[yellow]Warning: Prompt ignored in interactive mode[/yellow]\n"
            )

        asyncio.run(
            run_interactive_session(
                model=full_model,
                working_dir=working_dir,
                context=context,
                session_id=session_id,
            )
        )
    else:
        if not prompt:
            console = Console()
            console.print("[red]Error: Prompt required for one-shot mode[/red]")
            console.print("Use --interactive for interactive session")
            sys.exit(1)

        asyncio.run(
            run_one_shot_query(
                prompt=prompt,
                model=full_model,
                working_dir=working_dir,
                allowed_tools=allowed_tools,
                session_id=session_id,
            )
        )


if __name__ == "__main__":
    main()
