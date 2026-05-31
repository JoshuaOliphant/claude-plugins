#!/usr/bin/env python3
"""
ABOUTME: Resolves understand-plugin settings from .local.md config (deck, session dir, strictness).
ABOUTME: Project-level then user-level override, with sensible defaults.
"""

import json
import re
import sys
from pathlib import Path

CONFIG_NAME = "understand.local.md"
_KV = re.compile(r"^([a-z_]+)\s*:\s*(.+)$")

DEFAULTS = {
    "mochi_deck": "",
    "session_dir": "understand-sessions/",
    "follow_references": "true",
    "strictness": "struggle-then-teach",
    "card_cap": "10",
}


def _parse_config(path: Path) -> dict:
    """Parse `key: value` lines from a .local.md config file."""
    settings: dict = {}
    if not path.exists():
        return settings
    for line in path.read_text(encoding="utf-8").split("\n"):
        match = _KV.match(line.strip())
        if match:
            settings[match.group(1)] = match.group(2).strip()
    return settings


def _find_config(project_root: Path, home: Path):
    """Return (settings, source) using project-level then user-level config."""
    project_cfg = project_root / ".claude" / CONFIG_NAME
    if project_cfg.exists():
        return _parse_config(project_cfg), "project"
    user_cfg = home / ".claude" / CONFIG_NAME
    if user_cfg.exists():
        return _parse_config(user_cfg), "user"
    return {}, "default"


def _as_bool(value: str) -> bool:
    """Interpret a config string as a boolean."""
    return value.strip().lower() in ("true", "yes", "1", "on")


def resolve(project_root: Path, home: Path) -> dict:
    """Resolve understand-plugin settings from config or defaults."""
    settings, source = _find_config(project_root, home)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in settings.items() if k in DEFAULTS})

    expanded = Path(merged["session_dir"]).expanduser()
    if expanded.is_absolute():
        session_dir = str(expanded).rstrip("/") + "/"
    else:
        session_dir = str(project_root / expanded).rstrip("/") + "/"

    try:
        card_cap = int(merged["card_cap"])
    except (ValueError, TypeError):
        card_cap = int(DEFAULTS["card_cap"])

    return {
        "mochi_deck": merged["mochi_deck"],
        "session_dir": session_dir,
        "follow_references": _as_bool(merged["follow_references"]),
        "strictness": merged["strictness"],
        "card_cap": card_cap,
        "config_source": source,
    }


def main(argv: list) -> int:
    project_root = Path(argv[1]).expanduser().resolve() if len(argv) > 1 else Path.cwd()
    home = Path(argv[2]).expanduser().resolve() if len(argv) > 2 else Path.home()
    print(json.dumps(resolve(project_root, home), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
