#!/usr/bin/env python3
# ABOUTME: Verifies each plugin's version in marketplace.json matches its plugin.json.
# ABOUTME: Run before publishing; exits non-zero (and prints the drift) on any mismatch.
"""Check that .claude-plugin/marketplace.json is in sync with every plugin.json.

CLAUDE.md treats each plugin's plugin.json as the source of truth for its
version, and requires marketplace.json to copy that value at publication time.
This script enforces that rule so the catalog never advertises a stale version.

Usage:
    python scripts/check_marketplace_versions.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def main() -> int:
    marketplace = json.loads(MARKETPLACE.read_text())
    mismatches: list[str] = []
    missing: list[str] = []

    for entry in marketplace.get("plugins", []):
        name = entry["name"]
        catalog_version = entry.get("version")
        plugin_json = REPO_ROOT / "plugins" / name / ".claude-plugin" / "plugin.json"

        if not plugin_json.exists():
            missing.append(f"{name}: {plugin_json.relative_to(REPO_ROOT)} not found")
            continue

        source_version = json.loads(plugin_json.read_text()).get("version")
        if source_version != catalog_version:
            mismatches.append(
                f"{name}: plugin.json={source_version} != marketplace.json={catalog_version}"
            )

    if missing:
        print("Missing plugin.json files:")
        for line in missing:
            print(f"  - {line}")
    if mismatches:
        print("Version drift (plugin.json is source of truth — update marketplace.json):")
        for line in mismatches:
            print(f"  - {line}")

    if missing or mismatches:
        return 1

    print(f"OK: {len(marketplace.get('plugins', []))} plugin versions in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
