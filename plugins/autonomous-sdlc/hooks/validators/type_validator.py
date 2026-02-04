#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ABOUTME: PostToolUse hook that runs mypy type checker on modified Python files
# ABOUTME: Reports type errors to stdout for builder agent feedback

"""
Type Validator Hook

This hook runs after Write/Edit operations on Python files.
It checks the modified file with mypy and reports any type errors.

Input: JSON on stdin with tool_use information
Output: Error messages to stdout (if any issues found)
Exit: 0 (always, to not block the agent)
"""

import json
import subprocess
import sys
from pathlib import Path


def get_file_path_from_input() -> str | None:
    """Extract file path from hook input JSON."""
    try:
        hook_input = json.load(sys.stdin)
        tool_input = hook_input.get("tool_input", {})

        # Handle both Write and Edit tool formats
        file_path = tool_input.get("file_path") or tool_input.get("path")
        return file_path
    except (json.JSONDecodeError, KeyError):
        return None


def run_mypy_check(file_path: str) -> tuple[bool, str]:
    """Run mypy check on the specified file.

    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            [
                "uv", "run", "mypy", file_path,
                "--no-error-summary",
                "--no-pretty",
                "--ignore-missing-imports",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True, ""
        else:
            # Filter out notes and only show errors
            errors = []
            for line in result.stdout.split("\n"):
                if ": error:" in line:
                    errors.append(line)
            return False, "\n".join(errors)

    except subprocess.TimeoutExpired:
        return False, "TYPE: Timeout checking file"
    except FileNotFoundError:
        # mypy not installed, skip silently
        return True, ""


def main() -> None:
    """Main entry point for the hook."""
    file_path = get_file_path_from_input()

    if not file_path:
        # No file path, nothing to check
        sys.exit(0)

    # Only check Python files
    if not file_path.endswith(".py"):
        sys.exit(0)

    # Check if file exists
    if not Path(file_path).exists():
        sys.exit(0)

    # Skip test files for type checking (often have looser types)
    if "/test_" in file_path or file_path.startswith("test_"):
        sys.exit(0)

    success, output = run_mypy_check(file_path)

    if not success and output:
        # Format output for agent feedback
        print(f"TYPE: Found issues in {file_path}")
        for line in output.strip().split("\n"):
            if line.strip():
                # Simplify the output
                print(f"  {line}")

    # Always exit 0 to not block the agent
    # Issues are reported but don't prevent further work
    sys.exit(0)


if __name__ == "__main__":
    main()
