#!/usr/bin/env python3
"""
ABOUTME: Resolves compound-knowledge read/write reservoir paths from .local.md config.
ABOUTME: Supports a write_path + read_paths split with a solutions_path back-compat alias.
"""

import json
import sys
from pathlib import Path

import config_loader

CONFIG_NAME = "compound-knowledge.local.md"


def _norm(path: str) -> str:
    """Normalize a directory path: expand ~ and ensure a single trailing slash."""
    return str(Path(path).expanduser()).rstrip("/") + "/"


def resolve(project_root: Path, home: Path) -> dict:
    """Resolve write_path, read_paths, and vault_root from config or defaults."""
    settings, source = config_loader.find_config(project_root, home, CONFIG_NAME)

    # write_path: explicit > solutions_path alias > default
    if "write_path" in settings:
        write_path = _norm(settings["write_path"])
    elif "solutions_path" in settings:
        write_path = _norm(settings["solutions_path"])
    else:
        write_path = _norm(str(project_root / "knowledge" / "solutions"))

    # read_paths: explicit comma list, else empty; write_path is always first (deduped)
    read_paths = []
    if "read_paths" in settings:
        read_paths = [_norm(p.strip()) for p in settings["read_paths"].split(",") if p.strip()]
    read_paths = [p for p in read_paths if p != write_path]
    read_paths.insert(0, write_path)

    vault_root = settings.get("vault_root")
    if vault_root:
        vault_root = _norm(vault_root)

    return {
        "write_path": write_path,
        "read_paths": read_paths,
        "vault_root": vault_root,
        "config_source": source,
    }


def main(argv: list) -> int:
    project_root, home = config_loader.cli_roots(argv)
    print(json.dumps(resolve(project_root, home), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
