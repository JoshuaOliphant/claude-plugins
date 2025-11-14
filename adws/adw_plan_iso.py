#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Plan Iso - Planning phase with worktree isolation

Usage: uv run adw_plan_iso.py <issue-number> [adw-id]

This script runs the planning phase in isolation:
1. Loads or creates ADW state
2. Fetches GitHub issue details
3. Creates/finds branch for the issue
4. Creates isolated worktree
5. Generates implementation plan using appropriate slash command
6. Saves state for subsequent phases
"""

import subprocess
import sys
import os
import logging

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.state import ADWState
from adw_modules.workflow_ops import (
    ensure_adw_id,
    create_or_find_branch,
    build_plan,
    fetch_issue_unified,
)
from adw_modules.worktree_ops import create_worktree, find_next_available_ports
from adw_modules.beads_integration import is_beads_issue, update_beads_status
from adw_modules.agent import execute_template
from adw_modules.data_types import AgentTemplateRequest

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run adw_plan_iso.py <issue-number> [adw-id]")
        print("\nThis runs the isolated planning phase:")
        print("  1. Load/create ADW state")
        print("  2. Fetch GitHub issue")
        print("  3. Create/find branch")
        print("  4. Create isolated worktree")
        print("  5. Generate plan")
        sys.exit(1)

    issue_number = sys.argv[1]
    adw_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Ensure ADW ID exists with initialized state
    adw_id = ensure_adw_id(issue_number, adw_id, logger)
    logger.info(f"Using ADW ID: {adw_id}")

    # Load state
    state = ADWState.load(adw_id, logger)
    if not state:
        state = ADWState(adw_id)
        state.update(adw_id=adw_id, issue_number=issue_number)

    # Fetch issue (GitHub or beads)
    is_beads = is_beads_issue(issue_number)
    logger.info(f"Fetching {'beads' if is_beads else 'GitHub'} issue: {issue_number}")
    issue, error = fetch_issue_unified(issue_number, logger)
    if error:
        logger.error(f"Failed to fetch issue: {error}")
        sys.exit(1)

    logger.info(f"Fetched issue: {issue.title}")

    # Update beads status to in_progress if it's a beads issue
    if is_beads:
        success, error = update_beads_status(issue_number, "in_progress")
        if not success:
            logger.warning(f"Failed to update beads status: {error}")

    # For worktree workflows, we need the branch name but should NOT check it out in main
    # Check if we already have a branch in state
    branch_name = state.get("branch_name")
    
    if not branch_name:
        # Generate new branch name without checking out
        from adw_modules.workflow_ops import classify_issue, generate_branch_name
        
        logger.info("Classifying issue to determine branch type")
        issue_command, error = classify_issue(issue, adw_id, logger)
        if error:
            logger.error(f"Failed to classify issue: {error}")
            sys.exit(1)
        
        state.update(issue_class=issue_command)
        
        logger.info("Generating branch name")
        branch_name, error = generate_branch_name(issue, issue_command, adw_id, logger)
        if error:
            logger.error(f"Failed to generate branch name: {error}")
            sys.exit(1)
    
    logger.info(f"Using branch: {branch_name}")

    # Create worktree
    logger.info("Creating isolated worktree")
    worktree_path, error = create_worktree(adw_id, branch_name, logger)
    if error:
        logger.error(f"Failed to create worktree: {error}")
        sys.exit(1)

    logger.info(f"Created worktree at: {worktree_path}")

    # Allocate ports for this worktree
    backend_port, frontend_port = find_next_available_ports(adw_id)
    logger.info(f"Allocated ports - Backend: {backend_port}, Frontend: {frontend_port}")

    # Update state with worktree info
    state.update(
        worktree_path=worktree_path,
        branch_name=branch_name,
        backend_port=backend_port,
        frontend_port=frontend_port,
    )
    state.save("adw_plan_iso")

    # Install worktree environment
    logger.info("Installing worktree environment")
    install_request = AgentTemplateRequest(
        agent_name="worktree_installer",
        slash_command="/install_worktree",
        args=[worktree_path, str(backend_port), str(frontend_port)],
        adw_id=adw_id,
    )
    install_response = execute_template(install_request)
    if not install_response.success:
        logger.error(f"Failed to install worktree: {install_response.output}")
        sys.exit(1)

    logger.info("Worktree environment installed")

    # Build plan using appropriate command
    issue_command = state.get("issue_class") or "/chore"
    logger.info(f"Building plan using command: {issue_command}")

    plan_response = build_plan(
        issue, issue_command, adw_id, logger, working_dir=worktree_path
    )

    if not plan_response.success:
        logger.error(f"Failed to build plan: {plan_response.output}")
        sys.exit(1)

    # Extract plan file path from response
    # The response contains the full message, but we need just the filename
    # Look for specs/*.md pattern in the output
    import re
    plan_file_match = re.search(r'specs/[\w-]+\.md', plan_response.output)
    if plan_file_match:
        plan_file = plan_file_match.group(0)
    else:
        # Fallback: use the full response
        plan_file = plan_response.output.strip()
    
    logger.info(f"Plan created: {plan_file}")

    # Update state with plan file
    state.update(plan_file=plan_file)
    state.save("adw_plan_iso")

    print(f"\n=== ISOLATED PLAN PHASE COMPLETED ===")
    print(f"ADW ID: {adw_id}")
    print(f"Branch: {branch_name}")
    print(f"Worktree: {worktree_path}")
    print(f"Plan file: {plan_file}")
    print(f"Ports: Backend={backend_port}, Frontend={frontend_port}")


if __name__ == "__main__":
    main()
