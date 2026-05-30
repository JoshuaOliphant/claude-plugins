# Compound Graduate (Promote Face) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the *promote* face of a new `compound-graduate` skill in the `compound-knowledge` plugin — the first, most visible increment of the compound loop's missing "improve" edge: turn captured knowledge (especially synthesized wiki theses) into proposed edits to the always-loaded living context (`CLAUDE.md` / `AGENTS.md`).

**Architecture:** A deterministic Python helper (`resolve_paths.py`) resolves the read/write reservoir paths from config and is fully TDD'd with pytest. A new markdown skill (`compound-graduate`) orchestrates the LLM-driven promotion: resolve paths → scan the read corpus for candidates → propose-then-apply living-context edits → verify. The garden/prune face and the plugin-feedback redirect (Move B) are explicitly out of scope.

**Tech Stack:** Python 3.11 stdlib only, `uv` (`uv run --with pytest`), Claude Code plugin skill (`SKILL.md` + `references/`), `key: value` markdown config.

**Source spec:** `docs/superpowers/specs/2026-05-30-compound-engine-improve-stroke-design.md` (Move A, promote face = sequencing step 1).

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `plugins/compound-knowledge/scripts/resolve_paths.py` (create) | Resolve `write_path`, `read_paths`, `vault_root` from `.local.md` config, with `solutions_path` back-compat and defaults. Deterministic, testable. |
| `plugins/compound-knowledge/tests/test_resolve_paths.py` (create) | pytest unit tests for the resolver. |
| `plugins/compound-knowledge/skills/compound-graduate/SKILL.md` (create) | The promote-face skill: orchestration + triggers. Lean. |
| `plugins/compound-knowledge/skills/compound-graduate/references/promote-workflow.md` (create) | Detailed candidate heuristics, propose-then-apply protocol, verification checklist. |
| `plugins/compound-knowledge/.claude-plugin/plugin.json` (modify) | Version bump 0.7.0 → 0.8.0. |
| `.claude-plugin/marketplace.json` (modify) | Bump `compound-knowledge` to 0.8.0 (reconciles the stale 0.5.0), extend description. |
| `plugins/compound-knowledge/README.md` (modify) | Document the `compound-graduate` skill. |

---

## Task 1: Path resolver (`resolve_paths.py`) — TDD

The deterministic foundation. `read wide, write structured`: one `write_path` for capture, a list of `read_paths` for retrieval/promotion, `solutions_path` kept as a back-compat alias meaning both.

**Files:**
- Create: `plugins/compound-knowledge/tests/test_resolve_paths.py`
- Create: `plugins/compound-knowledge/scripts/resolve_paths.py`

- [ ] **Step 1: Write the failing tests**

Create `plugins/compound-knowledge/tests/test_resolve_paths.py`:

```python
"""
ABOUTME: Tests for resolve_paths.py reservoir path resolution.
ABOUTME: Covers defaults, solutions_path back-compat, read/write split, precedence, vault_root.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import resolve_paths  # noqa: E402


def _write_cfg(dir_path: Path, body: str) -> None:
    cfg_dir = dir_path / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "compound-knowledge.local.md").write_text(body, encoding="utf-8")


def test_default_when_no_config(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    result = resolve_paths.resolve(proj, home)
    expected = str(proj / "knowledge" / "solutions") + "/"
    assert result["write_path"] == expected
    assert result["read_paths"] == [expected]
    assert result["vault_root"] is None
    assert result["config_source"] == "default"


def test_solutions_path_back_compat(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "# Settings\nsolutions_path: /vault/knowledge/solutions/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/vault/knowledge/solutions/"
    assert result["read_paths"] == ["/vault/knowledge/solutions/"]
    assert result["config_source"] == "project"


def test_read_write_split(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "write_path: /vault/knowledge/solutions/\nread_paths: /vault/wiki/, /vault/journal/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/vault/knowledge/solutions/"
    assert result["read_paths"] == ["/vault/knowledge/solutions/", "/vault/wiki/", "/vault/journal/"]


def test_read_paths_dedup_write(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "write_path: /vault/knowledge/solutions/\nread_paths: /vault/knowledge/solutions/, /vault/wiki/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["read_paths"] == ["/vault/knowledge/solutions/", "/vault/wiki/"]


def test_project_over_user_precedence(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(home, "solutions_path: /user/level/solutions/\n")
    _write_cfg(proj, "solutions_path: /project/level/solutions/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/project/level/solutions/"
    assert result["config_source"] == "project"


def test_user_level_when_no_project_config(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(home, "solutions_path: /user/level/solutions/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/user/level/solutions/"
    assert result["config_source"] == "user"


def test_vault_root_parsed(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "solutions_path: /vault/knowledge/solutions/\nvault_root: /vault\n")
    result = resolve_paths.resolve(proj, home)
    assert result["vault_root"] == "/vault/"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest plugins/compound-knowledge/tests/test_resolve_paths.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolve_paths'` (the script does not exist yet).

- [ ] **Step 3: Write the resolver**

Create `plugins/compound-knowledge/scripts/resolve_paths.py`:

```python
#!/usr/bin/env python3
"""
ABOUTME: Resolves compound-knowledge read/write reservoir paths from .local.md config.
ABOUTME: Supports a write_path + read_paths split with a solutions_path back-compat alias.
"""

import json
import re
import sys
from pathlib import Path

CONFIG_NAME = "compound-knowledge.local.md"
_KV = re.compile(r"^([a-z_]+)\s*:\s*(.+)$")


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


def _norm(path: str) -> str:
    """Normalize a directory path to a single trailing slash."""
    return path.rstrip("/") + "/"


def resolve(project_root: Path, home: Path) -> dict:
    """Resolve write_path, read_paths, and vault_root from config or defaults."""
    settings, source = _find_config(project_root, home)

    # write_path: explicit > solutions_path alias > default
    if "write_path" in settings:
        write_path = _norm(settings["write_path"])
    elif "solutions_path" in settings:
        write_path = _norm(settings["solutions_path"])
    else:
        write_path = _norm(str(project_root / "knowledge" / "solutions"))

    # read_paths: explicit comma list, else empty; write_path always included first
    read_paths = []
    if "read_paths" in settings:
        read_paths = [_norm(p.strip()) for p in settings["read_paths"].split(",") if p.strip()]
    if write_path not in read_paths:
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
    project_root = Path(argv[1]).expanduser().resolve() if len(argv) > 1 else Path.cwd()
    home = Path(argv[2]).expanduser().resolve() if len(argv) > 2 else Path.home()
    print(json.dumps(resolve(project_root, home), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --with pytest pytest plugins/compound-knowledge/tests/test_resolve_paths.py -v`
Expected: PASS — 7 passed.

- [ ] **Step 5: Make the script executable**

Run: `chmod +x plugins/compound-knowledge/scripts/resolve_paths.py`

- [ ] **Step 6: Commit**

```bash
git add plugins/compound-knowledge/scripts/resolve_paths.py plugins/compound-knowledge/tests/test_resolve_paths.py
git commit -m "feat(compound-knowledge): add read/write reservoir path resolver"
```

---

## Task 2: `compound-graduate` skill (promote face)

The LLM-driven orchestration. Lean SKILL.md; detail lives in the references file (Task 3). It is not pytest-testable — acceptance is a smoke run of the resolver in-repo plus a frontmatter/triggering validation.

**Files:**
- Create: `plugins/compound-knowledge/skills/compound-graduate/SKILL.md`

- [ ] **Step 1: Create the skill directory**

Run: `mkdir -p plugins/compound-knowledge/skills/compound-graduate/references`

- [ ] **Step 2: Write SKILL.md**

Create `plugins/compound-knowledge/skills/compound-graduate/SKILL.md`:

```markdown
---
name: compound-graduate
description: >
  Promote accumulated knowledge into living context. Use when the user says "graduate
  knowledge", "promote lessons", "update CLAUDE.md from what we've learned", "what should be
  in my CLAUDE.md", "compound graduate", "improve the system from my notes", or after a run of
  captures when patterns recur. Scans the read corpus (solutions + wiki theses) and proposes
  concrete edits to CLAUDE.md / AGENTS.md. Not for capturing (use compound-capture) or
  searching (use compound-retrieve).
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash]
---

# Compound Graduate (promote)

## Goal

Close the compound loop's "improve" edge: turn captured knowledge into visible improvements to
the always-loaded living context (`CLAUDE.md` / `AGENTS.md`). This is the *promote* face. The
garden/prune face is future work and out of scope here.

## When to run

After enough knowledge has accumulated that patterns recur, or on explicit request. Promotion
edits the file read every session, so it is high-trust: always propose before applying.

## Workflow

1. **Resolve the corpus.** Run the resolver to get the read corpus and semantic root:

   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_paths.py
   ```

   Use `read_paths` as the scan corpus and `vault_root` (if set) for semantic queries.

2. **Gather candidates** (prefer the most synthesized layer first):
   - `[solid]` and `[evolving]` theses under any `wiki/theses/` directory in `read_paths`.
   - High-severity solution files (`severity: critical` or `severity: high`) and any
     `critical-patterns.md` in `read_paths`.
   - Use `Grep` for keywords; when `vault_root` is set, use the `vault-recommender` MCP for
     topic clusters keyword search would miss.

3. **Identify the target.** Use `CLAUDE.md` at the project root if present, else `AGENTS.md`.

4. **Propose, do not apply yet.** For each candidate draft a concrete, minimal, evergreen edit
   to the target (one pattern; no temporal phrasing like "recently" or "now we"). Show the
   proposed diff and get confirmation. **Never edit wiki files here** — promote *reads* theses;
   only `wiki-ingest` *writes* the wiki.

5. **Apply confirmed edits** with `Edit`. Elevate broadly-useful patterns into
   `{write_path}/critical-patterns.md`.

6. **Verify each promotion:** ask *"would the system catch this automatically next session now
   that it lives in the always-loaded context?"* If not, refine the edit.

See `references/promote-workflow.md` for candidate heuristics, the propose-then-apply protocol,
and the verification checklist.

## Additional Resources

- `scripts/resolve_paths.py` — resolves `write_path`, `read_paths`, `vault_root` from config.
- `references/promote-workflow.md` — detailed promotion procedure.
```

- [ ] **Step 3: Smoke-test the resolver wiring in-repo**

Run: `python plugins/compound-knowledge/scripts/resolve_paths.py "$(pwd)"`
Expected: valid JSON with a `write_path` ending in `/knowledge/solutions/` and `read_paths` containing it. `config_source` is `default` unless a user-level `~/.claude/compound-knowledge.local.md` exists (then `user`, and the paths reflect that config) — either is fine; the point is the command runs clean and emits the four keys. Confirms the skill's Step-1 command works from the repo.

- [ ] **Step 4: Validate frontmatter and triggering**

Confirm `SKILL.md` frontmatter has `name`, a `description` with concrete trigger phrases, and `allowed-tools`. Optionally dispatch the `skill-reviewer` agent: "Review the compound-graduate skill for description quality and progressive disclosure."

- [ ] **Step 5: Commit**

```bash
git add plugins/compound-knowledge/skills/compound-graduate/SKILL.md
git commit -m "feat(compound-knowledge): add compound-graduate promote skill"
```

---

## Task 3: `references/promote-workflow.md`

Progressive-disclosure detail that keeps `SKILL.md` lean.

**Files:**
- Create: `plugins/compound-knowledge/skills/compound-graduate/references/promote-workflow.md`

- [ ] **Step 1: Write the reference**

Create `plugins/compound-knowledge/skills/compound-graduate/references/promote-workflow.md`:

```markdown
# Promote Workflow

Detailed procedure for the `compound-graduate` promote face.

## Candidate selection (priority order)

1. **Wiki theses** (`wiki/theses/**`) marked `[solid]` — distilled, high-confidence positions.
   These are the best fuel: already synthesized, unlike individual lessons.
2. **Wiki theses marked `[evolving]`** — promote only the stable core, phrased provisionally.
3. **`critical-patterns.md`** entries in any read path.
4. **Solution files** with frontmatter `severity: critical` or `severity: high`.
5. Recurring patterns: the same lesson appearing across 3+ solution files is itself a signal.

Skip: `[hypothesis]` / `[questioning]` theses, low-severity one-offs, anything project-specific
that would not generalize to the target context file.

## Propose-then-apply protocol

For each candidate:

1. Draft the smallest edit that captures the pattern. One pattern per edit.
2. Write evergreen prose: describe the rule as it is, not how it evolved. No "recently",
   "now we", "as of", or change-log phrasing.
3. Place it in the matching section of the target (`CLAUDE.md` / `AGENTS.md`); create a section
   only if none fits.
4. Show the proposed diff. Wait for confirmation. Do not batch-apply silently.
5. On confirmation, apply with `Edit`. On rejection, drop it and move on.

## Hard rules

- **Never write wiki files.** Promote reads `wiki/theses/`; only `wiki-ingest` writes the wiki.
  This prevents a synthesis loop between the two.
- **Living context is high-trust.** Always propose before editing `CLAUDE.md` / `AGENTS.md`.
- **`critical-patterns.md` is lower-trust.** Elevating a broadly-useful pattern into
  `{write_path}/critical-patterns.md` may be applied directly, then reported.

## Verification checklist (per promotion)

- Would a fresh session, reading only the updated context file, now avoid the mistake or apply
  the pattern without being told? If no, the edit is too vague — sharpen it.
- Is the edit evergreen (no temporal references)?
- Is it generalizable, not a project-specific detail that belongs in a solution file instead?
```

- [ ] **Step 2: Commit**

```bash
git add plugins/compound-knowledge/skills/compound-graduate/references/promote-workflow.md
git commit -m "docs(compound-knowledge): add promote-workflow reference for compound-graduate"
```

---

## Task 4: Version bump, marketplace reconcile, README

**Files:**
- Modify: `plugins/compound-knowledge/.claude-plugin/plugin.json` (version `0.7.0` → `0.8.0`)
- Modify: `.claude-plugin/marketplace.json` (compound-knowledge `version` `0.5.0` → `0.8.0`, extend description)
- Modify: `plugins/compound-knowledge/README.md`

- [ ] **Step 1: Bump plugin.json**

In `plugins/compound-knowledge/.claude-plugin/plugin.json`, change:

```json
  "version": "0.7.0",
```

to:

```json
  "version": "0.8.0",
```

- [ ] **Step 2: Reconcile marketplace.json**

In `.claude-plugin/marketplace.json`, in the `compound-knowledge` entry, change:

```json
      "version": "0.5.0",
```

to:

```json
      "version": "0.8.0",
```

And update that entry's `description` to:

```json
      "description": "Capture solved problems, retrieve past solutions, and graduate accumulated knowledge into living context. Skills: compound-capture, compound-retrieve, compound-graduate.",
```

- [ ] **Step 3: Document the skill in the plugin README**

In `plugins/compound-knowledge/README.md`, add a bullet to the skills list describing the new skill:

```markdown
- **compound-graduate** — Promote accumulated knowledge (especially synthesized wiki theses) into the always-loaded living context (`CLAUDE.md` / `AGENTS.md`). The "improve" stroke: proposes concrete, evergreen edits and verifies the system would catch the pattern next session.
```

- [ ] **Step 4: Verify the test suite still passes**

Run: `uv run --with pytest pytest plugins/compound-knowledge/tests/ -v`
Expected: PASS — 7 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/compound-knowledge/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/compound-knowledge/README.md
git commit -m "chore(compound-knowledge): release 0.8.0 with compound-graduate, reconcile marketplace version"
```

---

## Out of scope (do not build here)

- **Garden/prune face** — stale/duplicate/merge/archive pass. Future increment.
- **Move B (feedback redirect)** — routing plugin `feedback` skills into the reservoir. Waits for usage.
- **Marketplace call-wiring** — autonomous-sdlc invoking the engine. Parked downstream.
- **Reconfiguring La Boeuf's actual vault** to read the wiki — that is a config change (`read_paths`), done via `/compound-knowledge:setup` or by hand-editing `compound-knowledge.local.md`, not part of this plugin build.

## Acceptance

- `resolve_paths.py`: 7 pytest cases pass; resolves read/write split with `solutions_path` back-compat.
- `compound-graduate` skill: loads with valid frontmatter; Step-1 resolver command runs clean in-repo; a dry run proposes a `CLAUDE.md`/`AGENTS.md` edit from a sample thesis and writes no wiki file.
- Plugin at 0.8.0; marketplace listing reconciled to 0.8.0.
