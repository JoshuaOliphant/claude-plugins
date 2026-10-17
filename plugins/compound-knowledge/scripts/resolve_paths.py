#!/usr/bin/env python3
"""
ABOUTME: Resolves compound-knowledge read/write reservoir paths from .local.md config.
ABOUTME: Supports a write_path + read_paths split with a solutions_path back-compat alias.
The CLI is the only place skills and agents get these paths from; it exits 1 when write_path
does not exist, so a broken or uninitialized config is loud.
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
    # Reads go wide (the whole vault via read_paths/vault_root) so retrieval finds everything;
    # writes stay in one structured, schema'd location (write_path) so capture stays consistent.
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
    """Print the resolved paths as JSON; exit 1 when write_path does not exist yet."""
    project_root, home = config_loader.cli_roots(argv)
    paths = resolve(project_root, home)
    print(json.dumps(paths, indent=2))
    if not Path(paths["write_path"]).is_dir():
        print(
            f"write_path {paths['write_path']} does not exist; create it with "
            f"`mkdir -p {paths['write_path']}`, or run /compound-knowledge:setup "
            "if no config exists yet.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
