#!/usr/bin/env python3
# ABOUTME: One-command repo health check: version sync, shared-artifact sync, and tests.
# ABOUTME: The single entrypoint CI and contributors run before publishing.
"""Run every repo-wide guard in one place and report a combined result.

Checks, in order:
  1. ``check_marketplace_versions.py`` — marketplace.json matches each plugin.json
  2. ``sync_shared.py --check``        — generated shared copies match their canonical source
  3. ``pytest``                        — every plugin's test suite

Usage:
    python scripts/check_all.py            # run all checks, exit non-zero on any failure
    uv run --group dev python scripts/check_all.py

Each check runs even if an earlier one fails, so a single run surfaces every
problem at once. Exit code is 0 only when all checks pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (label, argv). argv[0] is always the current interpreter for portability.
CHECKS: list[tuple[str, list[str]]] = [
    ("marketplace versions", [sys.executable, "scripts/check_marketplace_versions.py"]),
    ("shared-artifact sync", [sys.executable, "scripts/sync_shared.py", "--check"]),
    ("test suite", [sys.executable, "-m", "pytest", "-q"]),
]


def main() -> int:
    results: list[tuple[str, bool]] = []
    for label, argv in CHECKS:
        print(f"\n=== {label} ===", flush=True)
        completed = subprocess.run(argv, cwd=REPO_ROOT)
        results.append((label, completed.returncode == 0))

    print("\n=== summary ===")
    for label, ok in results:
        print(f"  {'✓' if ok else '✗'} {label}")

    failed = [label for label, ok in results if not ok]
    if failed:
        print(f"\n{len(failed)} check(s) failed: {', '.join(failed)}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
