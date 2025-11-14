#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Test Iso - Testing phase with worktree isolation

Usage: uv run adw_test_iso.py <issue-number> <adw-id> [--skip-e2e]

This script runs the testing phase in isolation:
1. Loads ADW state from build phase
2. Validates worktree exists
3. Runs test suite using /test command
4. Updates state with test results
"""

import subprocess
import sys
import os
import logging

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.state import ADWState
from adw_modules.worktree_ops import validate_worktree
from adw_modules.agent import execute_template
from adw_modules.data_types import AgentTemplateRequest

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    # Check for --skip-e2e flag
    skip_e2e = "--skip-e2e" in sys.argv
    if skip_e2e:
        sys.argv.remove("--skip-e2e")

    if len(sys.argv) < 3:
        print("Usage: uv run adw_test_iso.py <issue-number> <adw-id> [--skip-e2e]")
        print("\nThis runs the isolated testing phase:")
        print("  1. Load ADW state")
        print("  2. Validate worktree")
        print("  3. Run tests")
        print("\nFlags:")
        print("  --skip-e2e: Skip end-to-end tests")
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

    # Run tests using /test command
    logger.info("Running test suite")
    test_request = AgentTemplateRequest(
        agent_name="test_validator",
        slash_command="/test",
        args=[],
        adw_id=adw_id,
        working_dir=worktree_path,
    )

    test_response = execute_template(test_request)

    if not test_response.success:
        logger.warning(f"Tests had failures: {test_response.output}")
        # Note: We don't exit(1) here as some tests might be flaky
        # Review phase will determine if failures are acceptable
    else:
        logger.info("All tests passed")

    # Save state
    state.save("adw_test_iso")

    print(f"\n=== ISOLATED TEST PHASE COMPLETED ===")
    print(f"ADW ID: {adw_id}")
    print(f"Worktree: {worktree_path}")
    if skip_e2e:
        print(f"E2E tests: Skipped")

    # Exit with test result status
    sys.exit(0 if test_response.success else 1)


if __name__ == "__main__":
    main()
