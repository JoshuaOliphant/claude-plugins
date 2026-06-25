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


def _plugin_dirs() -> list[Path]:
    """Direct children of plugins/ that aren't dotdirs or caches."""
    plugins_dir = REPO_ROOT / "plugins"
    return sorted(
        child
        for child in plugins_dir.iterdir()
        if child.is_dir() and not child.name.startswith(".") and child.name != "__pycache__"
    )


def main() -> int:
    marketplace = json.loads(MARKETPLACE.read_text())
    mismatches: list[str] = []
    missing: list[str] = []

    registered = {entry["name"] for entry in marketplace.get("plugins", [])}

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

    # Reverse direction: every directory under plugins/ must be a registered
    # plugin. Catches both a plugin that was added but never registered, and a
    # non-plugin directory that doesn't belong under plugins/ at all.
    unregistered: list[str] = []
    non_plugin: list[str] = []
    for child in _plugin_dirs():
        has_manifest = (child / ".claude-plugin" / "plugin.json").exists()
        if not has_manifest:
            non_plugin.append(child.name)
        elif child.name not in registered:
            unregistered.append(child.name)

    if missing:
        print("Missing plugin.json files:")
        for line in missing:
            print(f"  - {line}")
    if mismatches:
        print("Version drift (plugin.json is source of truth — update marketplace.json):")
        for line in mismatches:
            print(f"  - {line}")
    if unregistered:
        print("Plugins not registered in marketplace.json (add a catalog entry):")
        for name in unregistered:
            print(f"  - {name}")
    if non_plugin:
        print("Directories under plugins/ that aren't plugins (move them out of plugins/):")
        for name in non_plugin:
            print(f"  - {name} (no .claude-plugin/plugin.json)")

    if missing or mismatches or unregistered or non_plugin:
        return 1

    print(f"OK: {len(marketplace.get('plugins', []))} plugin versions in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
