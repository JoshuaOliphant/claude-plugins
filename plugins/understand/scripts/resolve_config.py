#!/usr/bin/env python3
"""
ABOUTME: Resolves understand-plugin settings from .local.md config (deck, session dir, strictness).
ABOUTME: Project-level then user-level override, with sensible defaults.
"""

import json
import sys
from pathlib import Path

import config_loader

CONFIG_NAME = "understand.local.md"

DEFAULTS = {
    "mochi_deck": "",
    "session_dir": "understand-sessions/",
    "follow_references": "true",
    "strictness": "struggle-then-teach",
    "card_cap": "10",
}


def _as_bool(value: str) -> bool:
    """Interpret a config string as a boolean."""
    return value.strip().lower() in ("true", "yes", "1", "on")


def resolve(project_root: Path, home: Path) -> dict:
    """Resolve understand-plugin settings from config or defaults."""
    settings, source = config_loader.find_config(project_root, home, CONFIG_NAME)
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
    project_root, home = config_loader.cli_roots(argv)
    print(json.dumps(resolve(project_root, home), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
