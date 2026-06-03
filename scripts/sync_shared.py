#!/usr/bin/env python3
"""Generate-from-one-source sync for shared plugin artifacts.

Some artifacts are intentionally duplicated into multiple self-contained plugins
(plugins must ship their own copy — they cannot import from a sibling). To keep
those copies from drifting, each one is generated from a single canonical source
under ``scripts/shared/`` and verified here.

This mirrors ``check_marketplace_versions.py``: the canonical source is the truth,
the per-plugin copies are derived.

Usage:
    python scripts/sync_shared.py            # check for drift (exit 1 on mismatch)
    python scripts/sync_shared.py --check     # same as default
    python scripts/sync_shared.py --write      # regenerate all copies from canonical

Add a new shared artifact by appending to ``SHARED_ARTIFACTS`` below.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED = REPO_ROOT / "scripts" / "shared"

# Each entry: (human label, canonical source, [target copies])
# Paths are relative to the repository root.
SHARED_ARTIFACTS: list[tuple[str, str, list[str]]] = [
    (
        "feedback_manager.py",
        "scripts/shared/feedback_manager.py",
        [
            "plugins/autoloop/scripts/feedback_manager.py",
            "plugins/autonomous-sdlc/scripts/feedback_manager.py",
            "plugins/compound-knowledge/scripts/feedback_manager.py",
            "plugins/hexagonal-agents/scripts/feedback_manager.py",
            "plugins/mochi-creator/scripts/feedback_manager.py",
        ],
    ),
    (
        "prompt_design_principles.md",
        "scripts/shared/prompt_design_principles.md",
        [
            "plugins/mochi-creator/skills/mochi-creator/references/prompt_design_principles.md",
            "plugins/understand/skills/explain-back/references/prompt_design_principles.md",
        ],
    ),
]


def _read(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


def check() -> int:
    drift = 0
    for label, canonical_rel, targets in SHARED_ARTIFACTS:
        canonical = REPO_ROOT / canonical_rel
        if not canonical.exists():
            print(f"✗ {label}: canonical source missing at {canonical_rel}")
            drift += 1
            continue
        canonical_bytes = canonical.read_bytes()
        for target_rel in targets:
            target = REPO_ROOT / target_rel
            if _read(target) != canonical_bytes:
                state = "missing" if not target.exists() else "out of sync"
                print(f"✗ {label}: {target_rel} is {state}")
                drift += 1
    if drift:
        print(f"\n{drift} shared-artifact mismatch(es). Run: python scripts/sync_shared.py --write")
        return 1
    total = sum(len(t) for _, _, t in SHARED_ARTIFACTS)
    print(f"✓ All {total} shared copies match their canonical sources.")
    return 0


def write() -> int:
    written = 0
    for label, canonical_rel, targets in SHARED_ARTIFACTS:
        canonical = REPO_ROOT / canonical_rel
        if not canonical.exists():
            print(f"✗ {label}: canonical source missing at {canonical_rel} — skipping")
            continue
        canonical_bytes = canonical.read_bytes()
        for target_rel in targets:
            target = REPO_ROOT / target_rel
            if _read(target) != canonical_bytes:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(canonical_bytes)
                print(f"↻ wrote {target_rel}")
                written += 1
    print(f"\nDone. {written} copy(ies) regenerated from canonical sources.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate copies from canonical")
    parser.add_argument("--check", action="store_true", help="check for drift (default)")
    args = parser.parse_args()
    return write() if args.write else check()


if __name__ == "__main__":
    sys.exit(main())
