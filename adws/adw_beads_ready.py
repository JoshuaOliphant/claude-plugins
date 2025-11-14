#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Beads Ready - Select and execute workflow on a ready beads task

Usage: uv run adw_beads_ready.py [--workflow sdlc|plan-build-test-review]

This script:
1. Shows list of ready beads tasks (no blockers)
2. Lets you select one
3. Runs the full SDLC workflow on it
"""

import subprocess
import sys
import os

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.beads_integration import get_ready_beads_tasks


def main():
    """Main entry point."""
    workflow = "sdlc"  # default

    # Parse arguments
    if "--workflow" in sys.argv:
        idx = sys.argv.index("--workflow")
        if idx + 1 < len(sys.argv):
            workflow = sys.argv[idx + 1]

    print("🔍 Fetching ready beads tasks...")

    # Get ready tasks
    tasks, error = get_ready_beads_tasks(limit=20)
    if error:
        print(f"❌ Error: {error}")
        sys.exit(1)

    if not tasks:
        print("✅ No ready tasks found. All caught up!")
        sys.exit(0)

    print(f"\n📋 Found {len(tasks)} ready tasks:\n")
    for idx, task_id in enumerate(tasks, 1):
        print(f"  {idx}. {task_id}")

    print("\n")
    try:
        selection = input("Select task number (or 'q' to quit): ").strip()

        if selection.lower() == 'q':
            print("👋 Goodbye!")
            sys.exit(0)

        selected_idx = int(selection) - 1
        if selected_idx < 0 or selected_idx >= len(tasks):
            print("❌ Invalid selection")
            sys.exit(1)

        task_id = tasks[selected_idx]
        print(f"\n🚀 Running {workflow} workflow on task: {task_id}\n")

        # Run the workflow
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if workflow == "sdlc":
            cmd = [
                "uv",
                "run",
                os.path.join(script_dir, "adw_sdlc_iso.py"),
                task_id,
            ]
        elif workflow == "plan-build-test-review":
            cmd = [
                "uv",
                "run",
                os.path.join(script_dir, "adw_plan_build_test_review_iso.py"),
                task_id,
            ]
        else:
            print(f"❌ Unknown workflow: {workflow}")
            sys.exit(1)

        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("\n\n👋 Cancelled")
        sys.exit(0)
    except ValueError:
        print("❌ Invalid number")
        sys.exit(1)


if __name__ == "__main__":
    main()
