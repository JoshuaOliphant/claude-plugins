#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Review Iso - Review phase with worktree isolation

Usage: uv run adw_review_iso.py <issue-number> <adw-id> [--skip-resolution]

This script runs the review phase in isolation:
1. Loads ADW state from test phase
2. Validates worktree exists
3. Reviews implementation against spec using /review command
4. Optionally resolves review issues if found
5. Updates state with review results
"""

import subprocess
import sys
import os
import logging
import json

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.state import ADWState
from adw_modules.worktree_ops import validate_worktree
from adw_modules.workflow_ops import find_spec_file, create_and_implement_patch
from adw_modules.agent import execute_template
from adw_modules.data_types import AgentTemplateRequest

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    # Check for --skip-resolution flag
    skip_resolution = "--skip-resolution" in sys.argv
    if skip_resolution:
        sys.argv.remove("--skip-resolution")

    if len(sys.argv) < 3:
        print("Usage: uv run adw_review_iso.py <issue-number> <adw-id> [--skip-resolution]")
        print("\nThis runs the isolated review phase:")
        print("  1. Load ADW state")
        print("  2. Validate worktree")
        print("  3. Review implementation")
        print("  4. Resolve issues (unless --skip-resolution)")
        print("\nFlags:")
        print("  --skip-resolution: Skip automatic issue resolution")
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

    # Run review using /review command
    logger.info("Running review")
    review_request = AgentTemplateRequest(
        agent_name="review_agent",
        slash_command="/review",
        args=[adw_id, spec_file, "review_agent"],
        adw_id=adw_id,
        working_dir=worktree_path,
    )

    review_response = execute_template(review_request)

    if not review_response.success:
        logger.error(f"Review failed to execute: {review_response.output}")
        sys.exit(1)

    # Parse review results
    try:
        # Try to extract JSON from markdown code block if present
        output = review_response.output.strip()
        
        # Check if output is wrapped in markdown code block
        if "```json" in output:
            # Extract JSON from code block
            start = output.find("```json") + 7
            end = output.find("```", start)
            if end != -1:
                output = output[start:end].strip()
        elif "```" in output and "{" in output:
            # Generic code block with JSON
            start = output.find("```") + 3
            # Skip language identifier if present
            newline = output.find("\n", start)
            if newline != -1:
                start = newline + 1
            end = output.find("```", start)
            if end != -1:
                output = output[start:end].strip()
        
        review_results = json.loads(output)
        logger.info(f"Review completed: {review_results.get('review_summary', 'No summary')}")

        # Check for blocking issues
        blocking_issues = [
            issue
            for issue in review_results.get("review_issues", [])
            if issue.get("issue_severity") == "blocker"
        ]

        if blocking_issues and not skip_resolution:
            logger.warning(f"Found {len(blocking_issues)} blocking issues, attempting resolution")

            # Attempt to resolve each blocking issue
            for issue in blocking_issues:
                logger.info(f"Resolving issue {issue['review_issue_number']}: {issue['issue_description']}")

                # Create and implement patch for this issue
                patch_file, patch_response = create_and_implement_patch(
                    adw_id=adw_id,
                    review_change_request=issue["issue_resolution"],
                    logger=logger,
                    agent_name_planner="review_patch_planner",
                    agent_name_implementor="review_patch_implementor",
                    spec_path=spec_file,
                    issue_screenshots=issue.get("screenshot_path"),
                    working_dir=worktree_path,
                )

                if not patch_response.success:
                    logger.error(f"Failed to resolve issue: {patch_response.output}")
                    sys.exit(1)

                logger.info(f"Resolved issue {issue['review_issue_number']}")

        elif blocking_issues:
            logger.error(f"Found {len(blocking_issues)} blocking issues (resolution skipped)")
            for issue in blocking_issues:
                logger.error(f"  - {issue['issue_description']}")
            sys.exit(1)

        # Save state
        state.save("adw_review_iso")

        print(f"\n=== ISOLATED REVIEW PHASE COMPLETED ===")
        print(f"ADW ID: {adw_id}")
        print(f"Worktree: {worktree_path}")
        print(f"Review: {'Success' if review_results.get('success') else 'Has issues'}")
        print(f"Blocking issues: {len(blocking_issues)}")
        if skip_resolution and blocking_issues:
            print(f"Resolution: Skipped")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse review results: {e}")
        logger.error(f"Review output: {review_response.output}")
        sys.exit(1)


if __name__ == "__main__":
    main()
