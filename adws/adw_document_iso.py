#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Document Iso - Documentation phase with worktree isolation

Usage: uv run adw_document_iso.py <issue-number> <adw-id>

This script runs the documentation phase in isolation:
1. Loads ADW state from review phase
2. Validates worktree exists
3. Generates documentation using /document command
4. Updates state with documentation path
"""

import subprocess
import sys
import os
import logging

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.state import ADWState
from adw_modules.worktree_ops import validate_worktree
from adw_modules.workflow_ops import find_spec_file
from adw_modules.agent import execute_template
from adw_modules.data_types import AgentTemplateRequest

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: uv run adw_document_iso.py <issue-number> <adw-id>")
        print("\nThis runs the isolated documentation phase:")
        print("  1. Load ADW state")
        print("  2. Validate worktree")
        print("  3. Find spec file")
        print("  4. Generate documentation")
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
        logger.warning("No spec file found, documenting without spec reference")
        spec_file = ""

    # Get review screenshots directory if available
    review_img_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "agents",
        adw_id,
        "review_agent",
        "review_img",
    )

    if not os.path.exists(review_img_dir):
        logger.info("No review screenshots found")
        review_img_dir = ""
    else:
        logger.info(f"Found review screenshots at: {review_img_dir}")

    # Generate documentation using /document command
    logger.info("Generating documentation")
    doc_request = AgentTemplateRequest(
        agent_name="documentation_writer",
        slash_command="/document",
        args=[adw_id, spec_file, review_img_dir],
        adw_id=adw_id,
        working_dir=worktree_path,
    )

    doc_response = execute_template(doc_request)

    if not doc_response.success:
        logger.error(f"Documentation generation failed: {doc_response.output}")
        sys.exit(1)

    # Extract documentation file path
    doc_file = doc_response.output.strip()
    logger.info(f"Documentation created: {doc_file}")

    # Save state
    state.save("adw_document_iso")

    print(f"\n=== ISOLATED DOCUMENTATION PHASE COMPLETED ===")
    print(f"ADW ID: {adw_id}")
    print(f"Worktree: {worktree_path}")
    print(f"Documentation: {doc_file}")


if __name__ == "__main__":
    main()
