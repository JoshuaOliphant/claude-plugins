#!/usr/bin/env python3
# ABOUTME: Verifies each plugin's version in marketplace.json matches its plugin.json.
# ABOUTME: Run before publishing; exits non-zero (and prints the drift) on any mismatch.
"""Check that .claude-plugin/marketplace.json is in sync with every plugin.json.

AGENTS.md treats each plugin's plugin.json as the source of truth for its
version, and requires marketplace.json to copy that value at publication time.
This script enforces that rule so the catalog never advertises a stale version.

The rules live in ``drift()``, which takes parsed JSON and touches no files;
``main()`` reads the repo and prints. Plugin directories come from
``git ls-files``, so untracked leftovers under plugins/ don't count.

Usage:
    python scripts/check_marketplace_versions.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Findings:
    missing: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    unregistered: list[str] = field(default_factory=list)
    non_plugin: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.missing or self.mismatches or self.unregistered or self.non_plugin)

    def lines(self) -> list[str]:
        out: list[str] = []
        if self.missing:
            out.append("Missing plugin.json files:")
            out += [f"  - {line}" for line in self.missing]
        if self.mismatches:
            out.append("Version drift (plugin.json is source of truth — update marketplace.json):")
            out += [f"  - {line}" for line in self.mismatches]
        if self.unregistered:
            out.append("Plugins not registered in marketplace.json (add a catalog entry):")
            out += [f"  - {name}" for name in self.unregistered]
        if self.non_plugin:
            out.append(
                "Directories under plugins/ that aren't plugins (move them out of plugins/):"
            )
            out += [f"  - {name} (no .claude-plugin/plugin.json)" for name in self.non_plugin]
        return out


def drift(marketplace: dict, manifests: dict[str, dict | None]) -> Findings:
    """Compare the catalog against plugin manifests.

    ``manifests`` maps each directory under plugins/ to its parsed plugin.json,
    or None when the directory has none.
    """
    findings = Findings()
    entries = marketplace.get("plugins", [])
    registered = {entry["name"] for entry in entries}

    for entry in entries:
        name = entry["name"]
        manifest = manifests.get(name)
        if manifest is None:
            findings.missing.append(f"{name}: plugins/{name}/.claude-plugin/plugin.json not found")
        elif manifest.get("version") != entry.get("version"):
            findings.mismatches.append(
                f"{name}: plugin.json={manifest.get('version')} "
                f"!= marketplace.json={entry.get('version')}"
            )

    # Reverse direction: every directory under plugins/ must be a registered
    # plugin. Catches both a plugin that was added but never registered, and a
    # non-plugin directory that doesn't belong under plugins/ at all.
    # A registered name without a manifest is already reported as missing.
    for name, manifest in sorted(manifests.items()):
        if name in registered:
            continue
        if manifest is None:
            findings.non_plugin.append(name)
        else:
            findings.unregistered.append(name)
    return findings


def _plugin_dirs(root: Path) -> list[str]:
    """Names of directories under plugins/ that git tracks a file in."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", "plugins/"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(
        {path.split("/")[1] for path in listed.stdout.split("\0") if path.count("/") >= 2}
    )


def _read_manifests(root: Path) -> dict[str, dict | None]:
    manifests: dict[str, dict | None] = {}
    for name in _plugin_dirs(root):
        plugin_json = root / "plugins" / name / ".claude-plugin" / "plugin.json"
        manifests[name] = json.loads(plugin_json.read_text()) if plugin_json.exists() else None
    return manifests


def main(root: Path = REPO_ROOT) -> int:
    marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text())
    findings = drift(marketplace, _read_manifests(root))
    if findings:
        print("\n".join(findings.lines()))
        return 1
    print(f"OK: {len(marketplace.get('plugins', []))} plugin versions in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
