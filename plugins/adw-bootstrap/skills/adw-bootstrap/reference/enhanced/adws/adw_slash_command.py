#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic",
#   "python-dotenv",
#   "click",
#   "rich",
# ]
# ///
"""
Run Claude Code slash commands from the command line.

Usage:
    # Method 1: Direct execution (requires uv)
    ./adws/adw_slash_command.py /chore "Update documentation"

    # Method 2: Using uv run
    uv run adws/adw_slash_command.py /implement specs/<name-of-spec>.md

    uv run adws/adw_slash_command.py /start


Examples:
    # Run a slash command
    ./adws/adw_slash_command.py /chore "Add logging to agent.py"

    # Run with specific model
    ./adws/adw_slash_command.py /implement plan.md --model opus

    # Run from a different working directory
    ./adws/adw_slash_command.py /test --working-dir /path/to/project

    # Use custom agent name
    ./adws/adw_slash_command.py /review --agent-name reviewer
"""

import os
import sys
import json
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add the adw_modules directory to the path so we can import agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "adw_modules"))

from agent import (
    AgentTemplateRequest,
    AgentPromptResponse,
    execute_template,
    generate_short_id,
)

# Output file name constants
OUTPUT_JSONL = "cc_raw_output.jsonl"
OUTPUT_JSON = "cc_raw_output.json"
FINAL_OBJECT_JSON = "cc_final_object.json"
SUMMARY_JSON = "custom_summary_output.json"


@click.command()
@click.argument("slash_command", required=True)
@click.argument("args", nargs=-1)  # Accept multiple optional arguments
@click.option(
    "--model",
    type=click.Choice(["sonnet", "opus", "haiku"]),
    default="sonnet",
    help="Claude model to use (sonnet=balanced, opus=max intelligence, haiku=fast & economical)",
)
@click.option(
    "--working-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help="Working directory for command execution (default: current directory)",
)
@click.option(
    "--agent-name",
    default="executor",
    help="Agent name for tracking (default: executor)",
)
def main(
    slash_command: str,
    args: tuple,
    model: str,
    working_dir: str,
    agent_name: str,
):
    """Run Claude Code slash commands from the command line."""
    console = Console()

    # Generate a unique ID for this execution
    adw_id = generate_short_id()

    # Use current directory if no working directory specified
    if not working_dir:
        working_dir = os.getcwd()

    # Create the template request
    request = AgentTemplateRequest(
        agent_name=agent_name,
        slash_command=slash_command,
        args=list(args),  # Convert tuple to list
        adw_id=adw_id,
        model=model,
        working_dir=working_dir,
    )

    # Create execution info table
    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_column(style="bold cyan")
    info_table.add_column()

    info_table.add_row("ADW ID", adw_id)
    info_table.add_row("ADW Name", "adw_slash_command")
    info_table.add_row("Command", slash_command)
    info_table.add_row("Args", " ".join(args) if args else "(none)")
    info_table.add_row("Model", model)
    info_table.add_row("Working Dir", working_dir)

    console.print(
        Panel(
            info_table,
            title="[bold blue]🚀 Inputs[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    try:
        # Execute the slash command
        with console.status("[bold yellow]Executing command...[/bold yellow]"):
            response = execute_template(request)

        # Display the result
        if response.success:
            # Success panel
            result_panel = Panel(
                response.output,
                title="[bold green]✅ Success[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
            console.print(result_panel)

            if response.session_id:
                console.print(
                    f"\n[bold cyan]Session ID:[/bold cyan] {response.session_id}"
                )
        else:
            # Error panel
            error_panel = Panel(
                response.output,
                title="[bold red]❌ Failed[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
            console.print(error_panel)

            if response.retry_code != "none":
                console.print(
                    f"\n[bold yellow]Retry code:[/bold yellow] {response.retry_code}"
                )

        # Show output file info
        console.print()

        # Output files are in agents/<adw_id>/<agent_name>/
        output_dir = f"./agents/{adw_id}/{agent_name}"
        
        # Create the simple JSON summary file
        simple_json_output = f"{output_dir}/{SUMMARY_JSON}"
        
        # Determine the template file path
        command_name = slash_command.lstrip("/")  # Remove leading slash
        path_to_slash_command_prompt = f".claude/commands/{command_name}.md"
        
        with open(simple_json_output, "w") as f:
            json.dump(
                {
                    "adw_id": adw_id,
                    "slash_command": slash_command,
                    "args": list(args),
                    "path_to_slash_command_prompt": path_to_slash_command_prompt,
                    "model": model,
                    "working_dir": working_dir,
                    "success": response.success,
                    "session_id": response.session_id,
                    "retry_code": response.retry_code,
                    "output": response.output,
                },
                f,
                indent=2,
            )

        # Files saved panel
        files_table = Table(show_header=True, box=None)
        files_table.add_column("File Type", style="bold cyan")
        files_table.add_column("Path", style="dim")
        files_table.add_column("Description", style="italic")

        files_table.add_row(
            "JSONL Stream",
            f"{output_dir}/{OUTPUT_JSONL}",
            "Raw streaming output from Claude Code",
        )
        files_table.add_row(
            "JSON Array",
            f"{output_dir}/{OUTPUT_JSON}",
            "All messages as a JSON array",
        )
        files_table.add_row(
            "Final Object",
            f"{output_dir}/{FINAL_OBJECT_JSON}",
            "Last message entry (final result)",
        )
        files_table.add_row(
            "Summary",
            simple_json_output,
            "High-level execution summary with metadata",
        )

        console.print(
            Panel(
                files_table,
                title="[bold blue]📄 Output Files[/bold blue]",
                border_style="blue",
            )
        )

        # Exit with appropriate code
        sys.exit(0 if response.success else 1)

    except Exception as e:
        console.print(
            Panel(
                f"[bold red]{str(e)}[/bold red]",
                title="[bold red]❌ Unexpected Error[/bold red]",
                border_style="red",
            )
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
