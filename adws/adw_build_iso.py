#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Build Iso - Implementation phase with worktree isolation

Usage: uv run adw_build_iso.py <issue-number> <adw-id>

This script runs the implementation phase in isolation:
1. Loads ADW state from planning phase
2. Validates worktree exists
3. Implements the plan using /implement command
4. Updates state for subsequent phases
"""

import subprocess
import sys
import os
import logging

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.state import ADWState
from adw_modules.workflow_ops import implement_plan, find_spec_file
from adw_modules.worktree_ops import validate_worktree

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: uv run adw_build_iso.py <issue-number> <adw-id>")
        print("\nThis runs the isolated implementation phase:")
        print("  1. Load ADW state")
        print("  2. Validate worktree")
        print("  3. Find spec file")
        print("  4. Implement plan")
        sys.exit(1)

    issue_number = sys.argv[1]
    adw_id = sys.argv[2]

    # Load state
    state = ADWState.load(adw_id, logger)
    if not state:
        logger.error(f"No state found for ADW ID: {adw_id}")
        sys.exit(1)

    # Validate worktree
    logger.info("Validating worktree")
    valid, error = validate_worktree(adw_id, state)
    if not valid:
        logger.error(f"Worktree validation failed: {error}")
        sys.exit(1)

    worktree_path = state.get("worktree_path")
    logger.info(f"Using worktree: {worktree_path}")

    # Find spec file
    spec_file = find_spec_file(state, logger)
    if not spec_file:
        logger.error("No spec file found")
        sys.exit(1)

    logger.info(f"Using spec file: {spec_file}")

    # Implement the plan
    logger.info("Implementing plan")
    implement_response = implement_plan(
        spec_file, adw_id, logger, agent_name="build_implementor", working_dir=worktree_path
    )

    if not implement_response.success:
        logger.error(f"Implementation failed: {implement_response.output}")
        sys.exit(1)

    logger.info("Implementation completed successfully")

    # Save state
    state.save("adw_build_iso")

    print(f"\n=== ISOLATED BUILD PHASE COMPLETED ===")
    print(f"ADW ID: {adw_id}")
    print(f"Worktree: {worktree_path}")
    print(f"Spec file: {spec_file}")


if __name__ == "__main__":
    main()
