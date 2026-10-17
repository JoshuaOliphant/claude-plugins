#!/usr/bin/env python3
# ABOUTME: Fails when a branch changes a plugin's shipped files without bumping its plugin.json version.
# ABOUTME: CI runs it on pull requests into main; lanes of an integration branch are not checked.
"""Check that every plugin a branch changes has a bumped version.

AGENTS.md lets the lanes of an integration branch leave versions alone, as long as
one commit on that branch bumps every plugin it changed before it merges to main.
This script makes that "by merge time" rule mechanical: run it on a pull request
into main and it lists each plugin whose files differ from the base but whose
plugin.json version doesn't.

A plugin's tests/ directory doesn't count as shipped content. A plugin that is new
on the branch has nothing to bump from and is skipped.

Usage:
    python scripts/check_version_bumps.py              # compare against origin/main
    python scripts/check_version_bumps.py --base main
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)


def _changed(merge_base: str, name: str) -> bool:
    """True when the branch changed the plugin's files outside tests/ since merge_base."""
    diff = _git(
        "diff",
        "--quiet",
        merge_base,
        "--",
        f"plugins/{name}",
        f":(exclude)plugins/{name}/tests",
    )
    return diff.returncode == 1


def _version_at(ref: str, name: str) -> str | None:
    """The plugin's version at ref, or None when the plugin doesn't exist there."""
    shown = _git("show", f"{ref}:plugins/{name}/.claude-plugin/plugin.json")
    if shown.returncode != 0:
        return None
    return json.loads(shown.stdout).get("version")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main", help="ref the branch merges into")
    base = parser.parse_args(argv).base

    merge_base = _git("merge-base", base, "HEAD")
    if merge_base.returncode != 0:
        print(f"Can't find a merge base with {base}: {merge_base.stderr.strip()}")
        return 2

    names = [entry["name"] for entry in json.loads(MARKETPLACE.read_text())["plugins"]]
    unbumped: list[str] = []
    for name in names:
        base_version = _version_at(base, name)
        if base_version is None or not _changed(merge_base.stdout.strip(), name):
            continue
        head_version = _version_at("HEAD", name)
        if head_version == base_version:
            unbumped.append(f"{name}: changed since {base}, still at {head_version}")

    if unbumped:
        print("Plugins changed without a version bump (bump plugin.json, then marketplace.json):")
        for line in unbumped:
            print(f"  - {line}")
        return 1

    print(f"OK: every plugin changed since {base} has a bumped version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
