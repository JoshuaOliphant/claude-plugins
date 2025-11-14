#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.7",
#     "pydantic>=2.10.3",
#     "python-dotenv>=1.0.1",
# ]
# ///

"""
ABOUTME: ADW script to create TDD implementation plans from specifications
ABOUTME: Breaks large tasks into GitHub issue-sized chunks with dependency tracking
"""

import os
import sys
import uuid
import click
from pathlib import Path
from typing import Optional, Literal

# Add adw_modules to path
sys.path.insert(0, str(Path(__file__).parent / "adw_modules"))

from agent import (
    prompt_claude_code_with_retry,
    execute_template,
    AgentPromptRequest,
    AgentTemplateRequest,
)


@click.command()
@click.argument("spec_input")
@click.option(
    "--spec-file",
    is_flag=True,
    help="Treat spec_input as a file path to read",
)
@click.option(
    "--model",
    type=click.Choice(["sonnet", "opus", "haiku"]),
    default="sonnet",
    help="Claude model to use (sonnet=balanced, opus=max intelligence, haiku=fast)",
)
@click.option(
    "--adw-id",
    help="Custom ADW ID (default: auto-generated)",
)
@click.option(
    "--create-issues",
    is_flag=True,
    help="Create GitHub issues for each task (requires gh CLI)",
)
@click.option(
    "--working-dir",
    type=click.Path(exists=True),
    help="Working directory for execution",
)
def main(
    spec_input: str,
    spec_file: bool,
    model: Literal["sonnet", "opus", "haiku"],
    adw_id: Optional[str],
    create_issues: bool,
    working_dir: Optional[str],
):
    """
    Create a TDD implementation plan from a specification.

    Breaks down large tasks into GitHub issue-sized chunks following TDD principles.

    Examples:

        # From description
        ./adws/adw_plan_tdd.py "Add user authentication with JWT"

        # From spec file
        ./adws/adw_plan_tdd.py specs/feature-auth.md --spec-file

        # Use Opus for complex planning
        ./adws/adw_plan_tdd.py "Build real-time chat system" --model opus

        # Create GitHub issues automatically
        ./adws/adw_plan_tdd.py "Add OAuth2 support" --create-issues
    """

    # Generate ADW ID if not provided
    if not adw_id:
        adw_id = str(uuid.uuid4())[:8]

    # Read spec from file if specified
    if spec_file:
        spec_path = Path(spec_input)
        if not spec_path.exists():
            click.echo(f"❌ Spec file not found: {spec_input}", err=True)
            sys.exit(1)
        specification = spec_path.read_text()
        click.echo(f"📄 Read specification from: {spec_input}")
    else:
        specification = spec_input

    click.echo(f"🎯 Creating TDD plan with ID: {adw_id}")
    click.echo(f"🤖 Using model: {model}")
    click.echo()

    # Create plans directory if it doesn't exist
    plans_dir = Path("specs/plans")
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Execute /plan-tdd command
    click.echo("📋 Generating task breakdown...")

    template_request = AgentTemplateRequest(
        slash_command="/plan-tdd",
        args=[adw_id, specification],
        adw_id=adw_id,
        agent_name="plan-tdd",
        model=model,
        working_dir=working_dir,
    )

    result = execute_template(template_request)

    if not result.success:
        click.echo(f"❌ Plan generation failed", err=True)
        click.echo(f"Output: {result.output[:800]}", err=True)  # Show first 800 chars
        sys.exit(1)

    click.echo("✅ Plan generation complete!")
    click.echo()

    # Find the generated plan file
    plan_file = plans_dir / f"plan-{adw_id}.md"

    if not plan_file.exists():
        click.echo()
        click.echo(f"❌ Plan file not created: {plan_file}", err=True)
        click.echo()
        click.echo("This indicates the /plan-tdd template may have an issue or didn't write the file.", err=True)
        click.echo(f"Check agent output in: agents/{adw_id}/plan-tdd/ for more details.", err=True)
        sys.exit(1)  # Exit with error - file creation failed

    click.echo(f"📝 Plan saved to: {plan_file}")
    click.echo()

    # Parse plan to show summary
    plan_content = plan_file.read_text()

    # Count tasks (simple parsing)
    task_lines = [line for line in plan_content.split('\n') if line.startswith('### Task ')]
    num_tasks = len(task_lines)

    # Count complexity
    complexity_s = plan_content.count('**Complexity**: S')
    complexity_m = plan_content.count('**Complexity**: M')
    complexity_l = plan_content.count('**Complexity**: L')

    click.echo("📊 Plan Summary:")
    click.echo(f"   Total tasks: {num_tasks}")
    click.echo(f"   Simple (S):  {complexity_s} tasks")
    click.echo(f"   Medium (M):  {complexity_m} tasks")
    click.echo(f"   Large (L):   {complexity_l} tasks")
    click.echo()

    # Show complexity insights
    if complexity_l > 0:
        click.echo("⚠️  Warning: Contains Large tasks - consider breaking down further")
    if complexity_s + complexity_m > 20:
        click.echo("💡 Tip: Consider grouping related small tasks for efficiency")
    click.echo()

    # Create GitHub issues if requested
    if create_issues:
        click.echo("🐙 Creating GitHub issues...")

        # Check if gh CLI is available
        import subprocess
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            click.echo("❌ GitHub CLI (gh) not found. Install: brew install gh", err=True)
            click.echo("   Skipping issue creation.")
            sys.exit(1)

        # Parse tasks and create issues
        # This is a simplified implementation - could be more sophisticated
        click.echo("⚠️  GitHub issue creation not yet implemented.")
        click.echo("   You can manually create issues from the plan.")
        click.echo()

    # Show next steps
    click.echo("🚀 Next Steps:")
    click.echo()
    click.echo("1. Review the plan:")
    click.echo(f"   cat {plan_file}")
    click.echo()
    click.echo("2. Implement tasks in order:")
    click.echo(f"   # Extract task specs from plan and use /implement")
    click.echo(f"   # Or manually implement following the task breakdown")
    click.echo()
    click.echo("3. Track progress:")
    click.echo("   # Mark tasks complete in the plan file")
    click.echo("   # Or create GitHub issues for tracking")
    click.echo()

    click.echo(f"📂 Full output available in: agents/{adw_id}/plan-tdd/")


if __name__ == "__main__":
    main()
