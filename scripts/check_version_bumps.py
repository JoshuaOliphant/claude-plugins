#!/usr/bin/env python3
# ABOUTME: Fails when a branch changes a plugin's shipped files without raising its version past main's.
# ABOUTME: CI runs it on pull requests into main; lanes of an integration branch are not checked.
"""Check that every plugin a branch changes has a bumped version.

AGENTS.md lets the lanes of an integration branch leave versions alone, as long as
one commit on that branch bumps every plugin it changed before it merges to main.
This script makes that "by merge time" rule mechanical: run it on a pull request
into main and it lists each plugin whose files differ from the base but whose
plugin.json version isn't strictly greater than the base's.

The base is the ref the branch merges into (origin/main), not the fork point. Two
branches cut from one commit can both bump 0.8.1 to 0.9.0; once the first merges,
the second still looks bumped against its fork point but not against main, and an
install that already recorded 0.9.0 would never fetch its content (#84). The rule
lives in ``unbumped()``, which takes versions and touches no git; ``main()`` reads
the repo and prints.

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


def _semver(version: str) -> tuple[int, int, int] | None:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    major, minor, patch = (int(part) for part in parts)
    return major, minor, patch


def unbumped(
    base_versions: dict[str, str | None],
    head_versions: dict[str, str | None],
    changed: set[str],
    base: str,
) -> list[str]:
    """One line per changed plugin whose head version isn't strictly greater than base's.

    A plugin with no version at base (new on the branch) has nothing to bump from.
    """
    found: list[str] = []
    for name in sorted(changed):
        base_version = base_versions.get(name)
        if base_version is None:
            continue
        head_version = head_versions.get(name) or ""
        head_key, base_key = _semver(head_version), _semver(base_version)
        if head_key is None:
            found.append(f"{name}: version {head_version} is not MAJOR.MINOR.PATCH")
        elif base_key is None or head_key <= base_key:
            found.append(
                f"{name}: changed since {base}, at {head_version}, needs more than {base_version}"
            )
    return found


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def _changed(root: Path, merge_base: str, name: str) -> bool:
    """True when the branch changed the plugin's files outside tests/ since merge_base."""
    diff = _git(
        root,
        "diff",
        "--quiet",
        merge_base,
        "--",
        f"plugins/{name}",
        f":(exclude)plugins/{name}/tests",
    )
    return diff.returncode == 1


def _version_at(root: Path, ref: str, name: str) -> str | None:
    """The plugin's version at ref, or None when the plugin doesn't exist there."""
    shown = _git(root, "show", f"{ref}:plugins/{name}/.claude-plugin/plugin.json")
    if shown.returncode != 0:
        return None
    return json.loads(shown.stdout).get("version")


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main", help="ref the branch merges into")
    base = parser.parse_args(argv).base

    merge_base = _git(root, "merge-base", base, "HEAD")
    if merge_base.returncode != 0:
        print(f"Can't find a merge base with {base}: {merge_base.stderr.strip()}")
        return 2

    marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text())
    names = [entry["name"] for entry in marketplace["plugins"]]
    found = unbumped(
        {name: _version_at(root, base, name) for name in names},
        {name: _version_at(root, "HEAD", name) for name in names},
        {name for name in names if _changed(root, merge_base.stdout.strip(), name)},
        base,
    )

    if found:
        print(
            f"Plugins changed without a version above {base}'s "
            "(bump plugin.json past it, then copy to marketplace.json):"
        )
        for line in found:
            print(f"  - {line}")
        return 1

    print(f"OK: every plugin changed since {base} has a version above {base}'s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
