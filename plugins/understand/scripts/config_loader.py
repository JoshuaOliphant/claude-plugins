#!/usr/bin/env python3
# ABOUTME: Shared loader for a plugin's `.claude/<name>.local.md` key:value config.
# ABOUTME: Canonical source — synced into each plugin's scripts/ via scripts/sync_shared.py.
"""Read `key: value` lines from a plugin's `.claude/<name>.local.md` config file.

Resolution order is project-level (`<project>/.claude/<name>.local.md`) then
user-level (`<home>/.claude/<name>.local.md`), else empty. Callers layer their
own typing, defaults, and path normalization on top of the raw dict returned
here — this module only owns the file format and the project>user>default
precedence, which every consuming plugin shares.
"""

from __future__ import annotations

import re
from pathlib import Path

_KV = re.compile(r"^([a-z_]+)\s*:\s*(.+)$")


def parse_config(path: Path) -> dict:
    """Parse `key: value` lines from a .local.md config file (missing file → {})."""
    settings: dict = {}
    if not path.exists():
        return settings
    for line in path.read_text(encoding="utf-8").split("\n"):
        match = _KV.match(line.strip())
        if match:
            settings[match.group(1)] = match.group(2).strip()
    return settings


def find_config(project_root: Path, home: Path, config_name: str) -> tuple[dict, str]:
    """Return (settings, source) using project-level then user-level config."""
    project_cfg = project_root / ".claude" / config_name
    if project_cfg.exists():
        return parse_config(project_cfg), "project"
    user_cfg = home / ".claude" / config_name
    if user_cfg.exists():
        return parse_config(user_cfg), "user"
    return {}, "default"


def cli_roots(argv: list) -> tuple[Path, Path]:
    """Resolve (project_root, home) from argv[1:] for the standard resolver CLI."""
    project_root = Path(argv[1]).expanduser().resolve() if len(argv) > 1 else Path.cwd()
    home = Path(argv[2]).expanduser().resolve() if len(argv) > 2 else Path.home()
    return project_root, home
