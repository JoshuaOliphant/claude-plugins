# Understand Plugin (explain-back) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `understand` plugin's `explain-back` skill — an anti-illusion-of-clarity ritual that makes the user explain a topic from memory, grades it against an enriched answer key, runs struggle-then-teach per gap, and outputs Mochi cards plus a resumable vault session record.

**Architecture:** A deterministic Python config reader (`resolve_config.py`, fully TDD'd) resolves plugin settings from a `.local.md` file. A markdown `SKILL.md` orchestrates the interactive ritual, with a references file for grading heuristics and a session-record template asset. Mochi cards are written via the Mochi MCP (`mcp__mochi-donut__*`), not a bespoke client. v1 ships standalone + quiz modes; blog-publish wiring is deferred.

**Tech Stack:** Python 3.11 stdlib only, `uv` (`uv run --with pytest`), Claude Code plugin skill (`SKILL.md` + `references/` + `assets/`), Mochi MCP, `key: value` markdown config.

**Source spec:** `docs/superpowers/specs/2026-05-30-understand-plugin-design.md`.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `plugins/understand/scripts/resolve_config.py` (create) | Resolve `mochi_deck`, `session_dir`, `follow_references`, `strictness`, `card_cap` from `.local.md`, with defaults. Deterministic. |
| `plugins/understand/tests/test_resolve_config.py` (create) | pytest for the config reader. |
| `plugins/understand/skills/explain-back/SKILL.md` (create) | The ritual orchestration + triggers. Lean. |
| `plugins/understand/skills/explain-back/references/friction-signals.md` (create) | Grading heuristics, answer-key construction, struggle-then-teach protocol, card rules. |
| `plugins/understand/skills/explain-back/assets/session-record-template.md` (create) | Resumable session-record template. |
| `plugins/understand/README.md` (create) | Plugin overview + setup. |
| `plugins/understand/.claude-plugin/plugin.json` (create) | Plugin manifest. |
| `.claude-plugin/marketplace.json` (modify) | Add the `understand` plugin entry; bump catalog version. |

---

## Task 1: Config reader (`resolve_config.py`) — TDD

**Files:**
- Create: `plugins/understand/tests/test_resolve_config.py`
- Create: `plugins/understand/scripts/resolve_config.py`

- [ ] **Step 1: Write the failing tests**

Create `plugins/understand/tests/test_resolve_config.py`:

```python
"""
ABOUTME: Tests for resolve_config.py understand-plugin settings resolution.
ABOUTME: Covers defaults, overrides, bool/int parsing, precedence, tilde expansion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import resolve_config  # noqa: E402


def _write_cfg(dir_path: Path, body: str) -> None:
    cfg_dir = dir_path / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "understand.local.md").write_text(body, encoding="utf-8")


def test_defaults_when_no_config(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    result = resolve_config.resolve(proj, home)
    assert result["mochi_deck"] == ""
    assert result["session_dir"] == "understand-sessions/"
    assert result["follow_references"] is True
    assert result["strictness"] == "struggle-then-teach"
    assert result["card_cap"] == 10
    assert result["config_source"] == "default"


def test_full_override(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, (
        "mochi_deck: Learning\n"
        "session_dir: /vault/areas/learning/sessions/\n"
        "follow_references: false\n"
        "strictness: pure-examiner\n"
        "card_cap: 5\n"
    ))
    result = resolve_config.resolve(proj, home)
    assert result["mochi_deck"] == "Learning"
    assert result["session_dir"] == "/vault/areas/learning/sessions/"
    assert result["follow_references"] is False
    assert result["strictness"] == "pure-examiner"
    assert result["card_cap"] == 5
    assert result["config_source"] == "project"


def test_invalid_card_cap_falls_back_to_default(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "card_cap: lots\n")
    result = resolve_config.resolve(proj, home)
    assert result["card_cap"] == 10


def test_follow_references_bool_parsing(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "follow_references: YES\n")
    result = resolve_config.resolve(proj, home)
    assert result["follow_references"] is True


def test_project_over_user_precedence(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(home, "mochi_deck: UserDeck\n")
    _write_cfg(proj, "mochi_deck: ProjectDeck\n")
    result = resolve_config.resolve(proj, home)
    assert result["mochi_deck"] == "ProjectDeck"
    assert result["config_source"] == "project"


def test_session_dir_tilde_expanded(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "session_dir: ~/vault/sessions/\n")
    result = resolve_config.resolve(proj, home)
    assert not result["session_dir"].startswith("~")
    assert result["session_dir"].endswith("/")
```

- [ ] **Step 2: Run the tests to verify they FAIL**

Run: `uv run --with pytest pytest plugins/understand/tests/test_resolve_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolve_config'`.

- [ ] **Step 3: Write the config reader**

Create `plugins/understand/scripts/resolve_config.py`:

```python
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

    session_dir = str(Path(merged["session_dir"]).expanduser()).rstrip("/") + "/"

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
```

- [ ] **Step 4: Run the tests to verify they PASS**

Run: `uv run --with pytest pytest plugins/understand/tests/test_resolve_config.py -v`
Expected: PASS — 6 passed.

- [ ] **Step 5: Make the script executable**

Run: `chmod +x plugins/understand/scripts/resolve_config.py`

- [ ] **Step 6: Commit**

```bash
git add plugins/understand/scripts/resolve_config.py plugins/understand/tests/test_resolve_config.py
git commit -m "feat(understand): add config reader for explain-back settings"
```

---

## Task 2: `explain-back` SKILL.md

**Files:**
- Create: `plugins/understand/skills/explain-back/SKILL.md`

- [ ] **Step 1: Create the skill directories**

Run: `mkdir -p plugins/understand/skills/explain-back/references plugins/understand/skills/explain-back/assets`

- [ ] **Step 2: Write SKILL.md**

Create `plugins/understand/skills/explain-back/SKILL.md` with EXACTLY this content:

```markdown
---
name: explain-back
description: >
  Process information for real understanding and expose the illusion of clarity. Use when the user
  says "help me actually understand this", "test my understanding", "process what I learned", "quiz
  me on this", "am I fooling myself about X", "explain-back", "make sure I get this before I blog
  it", or after building/reading something they want to internalize. Makes the user explain from
  memory, grades against the real source, and teaches only after they attempt. Not for writing
  content for the user — this withholds answers on purpose.
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash, mcp__mochi-donut__list_decks, mcp__mochi-donut__create_cards]
---

# Explain-Back

## Goal

Defeat the illusion of clarity: the confident feeling of understanding something whose grasp is
full of gaps. Force the user to *generate* an explanation from memory, grade it against a real
answer key, and teach only after they attempt — so fluency never passes for understanding.

## Hard rule

**Never supply a gap's answer before the user has genuinely attempted it.** The withhold-until-
attempt gate is the entire point. Breaking it re-creates the illusion this skill targets.

## Workflow

1. **Resolve settings.**

   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_config.py
   ```

   Gives `mochi_deck`, `session_dir`, `follow_references`, `strictness`, `card_cap`.

2. **Set topic + source.** Ask what is being processed and locate the artifact (repo, draft,
   article, note). If `follow_references` is true, note references the source points to for step 3.

3. **Build the answer key — privately.** Read the source and (if `follow_references`) its
   references, and integrate your own domain knowledge into the complete picture. Do NOT reveal it.
   The source artifact outranks your own knowledge; mark any knowledge-only claims as
   lower-confidence (see `references/friction-signals.md`).

4. **User explains from memory.** Prompt: "Explain this to me from memory, no looking. Teach it to
   me cold." Do not hint.

5. **Grade against the answer key.** Identify gaps using the friction signals — vague phrases,
   broken cause→effect chains, restating outcomes instead of mechanisms — plus anything from the
   source/references they omitted or got wrong.

6. **Per gap, apply strictness:**
   - `struggle-then-teach` (default): name the gap, have them attempt it; only after a genuine
     attempt supply the missing mechanism; then have them **re-explain it back** in their words.
   - `pure-examiner`: name the gap and withhold entirely; they re-derive or go read, then explain
     again. Do not teach.

7. **Outputs.**
   - **Mochi cards:** for each closed/confirmed gap (up to `card_cap`), write a card via the Mochi
     MCP into `mochi_deck`. List decks with `mcp__mochi-donut__list_decks` first; if `mochi_deck`
     is empty, ask which deck. If the Mochi MCP is unavailable, skip cards and say so — do not fail
     the session.
   - **Session record:** write a resumable record to `{session_dir}` using
     `assets/session-record-template.md`, filling topic, source, the user's explanation, gaps,
     what was taught, confirmed understanding, and still-open gaps.

8. **Verify:** before closing, confirm each "closed" gap was re-explained by the user, not just
   explained at them. Still-open gaps stay logged as the resume handle.

## Modes

- **Standalone** (default): process anything built or read.
- **Quiz:** point at an existing draft/concept; run the same loop to interrogate it.
- **Blog-gate:** when invoked before drafting a post, the user's confirmed explanation is the raw
  material for the draft. (The `blog-publish` hook itself is a future increment.)

See `references/friction-signals.md` for grading heuristics, answer-key construction, and card rules.

## Additional Resources

- `scripts/resolve_config.py` — resolves plugin settings.
- `references/friction-signals.md` — grading heuristics and protocol.
- `assets/session-record-template.md` — resumable session-record template.
```

- [ ] **Step 3: Smoke-test the config wiring**

Run: `python plugins/understand/scripts/resolve_config.py "$(pwd)"`
Expected: valid JSON with keys `mochi_deck`, `session_dir`, `follow_references`, `strictness`, `card_cap`, `config_source`. Exit 0.

- [ ] **Step 4: Commit**

```bash
git add plugins/understand/skills/explain-back/SKILL.md
git commit -m "feat(understand): add explain-back skill"
```

---

## Task 3: `references/friction-signals.md`

**Files:**
- Create: `plugins/understand/skills/explain-back/references/friction-signals.md`

- [ ] **Step 1: Write the reference**

Create `plugins/understand/skills/explain-back/references/friction-signals.md` with EXACTLY this content:

```markdown
# Friction Signals and Protocol

Detailed procedure for the `explain-back` skill.

## Building the answer key

Construct the most complete reference available, in this priority:

1. **The source artifact** (repo, draft, article) — the ground truth. When it conflicts with your
   own knowledge, the artifact wins.
2. **References the source points to** (when `follow_references` is true) — read linked materials.
3. **Your own domain knowledge** — fill conceptual gaps the source assumes but does not state.

Mark claims that rest only on your own knowledge (not the artifact) as lower-confidence. If you are
unsure whether the user is wrong or you misread the source, re-read the source before flagging it —
do not mark the user wrong on a claim you cannot ground in the artifact.

## Friction signals (what a gap looks like)

- **Vague phrases** — "it just handles that", "somehow", "magic", hand-waving over a step.
- **Broken cause→effect** — the explanation jumps from A to D without B and C.
- **Outcomes restated as mechanisms** — describing *what* happens instead of *how/why* it happens.
- **Omissions vs. the source** — a component, step, or constraint present in the artifact but
  missing from the explanation.
- **Wrong claims** — contradicts the artifact (not merely your own knowledge).

## Struggle-then-teach protocol (per gap)

1. Name the gap precisely. Do not supply the answer.
2. Prompt the user to attempt it ("what do you think happens between B and D?").
3. Only after a genuine attempt, supply the missing mechanism — concise, mechanism-first.
4. Have the user **re-explain it back** in their own words. This is the second generation pass and
   is required to mark the gap closed.
5. If they cannot re-explain, the gap stays open — log it, do not paper over it.

`pure-examiner` strictness: do steps 1–2 only, then withhold entirely; the user re-derives or reads
and explains again. Never teach in this mode.

## Mochi cards

- One card per closed/confirmed gap, up to `card_cap`. If gaps exceed the cap, choose the most
  load-bearing and say which were dropped.
- Follow effective-prompt principles: focused (one idea), precise, effortful (the answer should
  require recall, not recognition). Prefer mechanism questions ("why does X cause Y?") over
  fact-lookup.
- Write into `mochi_deck`. If empty, ask which deck (list via the Mochi MCP). If the MCP is
  unavailable, skip and report — never fail the session over cards.

## Verification checklist (before closing)

- Was every "closed" gap re-explained by the user in their own words? If not, it is still open.
- Are still-open gaps recorded in the session file as the resume handle?
- Were cards capped and the dropped ones named?
```

- [ ] **Step 2: Commit**

```bash
git add plugins/understand/skills/explain-back/references/friction-signals.md
git commit -m "docs(understand): add friction-signals reference for explain-back"
```

---

## Task 4: `assets/session-record-template.md`

**Files:**
- Create: `plugins/understand/skills/explain-back/assets/session-record-template.md`

- [ ] **Step 1: Write the template**

Create `plugins/understand/skills/explain-back/assets/session-record-template.md` with EXACTLY this content:

```markdown
---
title: "Understanding session: {{TOPIC}}"
date: {{DATE}}
source: {{SOURCE}}
status: {{STATUS}}
tags: [understanding, explain-back]
---

# Understanding session: {{TOPIC}}

**Source:** {{SOURCE}}
**Strictness:** {{STRICTNESS}}

## What I explained from memory

{{USER_EXPLANATION}}

## Gaps found

{{GAPS}}

## What I learned (taught after attempting)

{{TAUGHT}}

## Confirmed understanding (re-explained in my words)

{{CONFIRMED}}

## Still open (resume here)

{{OPEN_GAPS}}

## Mochi cards created

{{CARDS}}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/understand/skills/explain-back/assets/session-record-template.md
git commit -m "docs(understand): add session-record template for explain-back"
```

---

## Task 5: Plugin manifest, README, marketplace entry

**Files:**
- Create: `plugins/understand/.claude-plugin/plugin.json`
- Create: `plugins/understand/README.md`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Create plugin.json**

Run: `mkdir -p plugins/understand/.claude-plugin`

Create `plugins/understand/.claude-plugin/plugin.json` with EXACTLY this content:

```json
{
  "name": "understand",
  "version": "0.1.0",
  "description": "Process information for real understanding. The explain-back skill makes you explain from memory, grades against the real source, teaches only after you attempt, and outputs Mochi cards plus a resumable session record. An antidote to the illusion of clarity.",
  "license": "MIT",
  "author": {
    "name": "Joshua Oliphant"
  },
  "homepage": "https://github.com/joshuaoliphant/claude-plugins",
  "repository": "https://github.com/joshuaoliphant/claude-plugins",
  "keywords": [
    "learning",
    "understanding",
    "spaced-repetition",
    "mochi",
    "feynman",
    "active-recall",
    "metacognition"
  ]
}
```

- [ ] **Step 2: Create README.md**

Create `plugins/understand/README.md` with EXACTLY this content:

```markdown
# understand (v0.1.0)

Process information for real understanding — an antidote to the illusion of clarity (the confident
feeling of understanding something whose grasp is actually full of gaps).

## Skill

- **explain-back** — Names a topic and source, builds a complete answer key privately (source +
  references + model knowledge), has you explain from memory, grades against the answer key, and
  runs **struggle-then-teach** per gap: it withholds the answer until you attempt, then teaches,
  then has you re-explain it back. Outputs **Mochi cards** for each gap and a **resumable session
  record**.

## Modes

- **Standalone** — process anything you built or read.
- **Quiz** — point it at an existing draft or concept and be interrogated.
- **Blog-gate** — run it before drafting a post so the draft is built from *your* explanation.

## Configuration

Optional `.claude/understand.local.md` (project or user level):

```markdown
mochi_deck: Learning
session_dir: ~/vault/areas/learning/sessions/
follow_references: true
strictness: struggle-then-teach
card_cap: 10
```

Defaults: `session_dir` `understand-sessions/`, `follow_references` true, `strictness`
`struggle-then-teach`, `card_cap` 10.

## Requirements

- Mochi MCP (`MOCHI_API_KEY`) for card output. Without it, the ritual still runs; cards are skipped.

```bash
/plugin install understand@oliphant-plugins
```
```

- [ ] **Step 3: Add the marketplace entry**

Edit `.claude-plugin/marketplace.json`. Add this object to the `plugins` array (after the existing entries):

```json
    {
      "name": "understand",
      "source": "./plugins/understand",
      "description": "Process information for real understanding with the explain-back skill: explain from memory, grade against the real source, struggle-then-teach per gap, output Mochi cards and a resumable session record. An antidote to the illusion of clarity.",
      "version": "0.1.0",
      "author": {
        "name": "Joshua Oliphant"
      },
      "keywords": [
        "learning",
        "understanding",
        "spaced-repetition",
        "mochi",
        "metacognition"
      ],
      "category": "productivity",
      "license": "MIT"
    }
```

Then bump the catalog `metadata.version` from its current value to the next patch (e.g. `1.0.5` → `1.0.6`).

Verify valid JSON:
`python -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('marketplace.json valid')"`

- [ ] **Step 4: Verify the test suite still passes**

Run: `uv run --with pytest pytest plugins/understand/tests/ -v`
Expected: PASS — 6 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/understand/.claude-plugin/plugin.json plugins/understand/README.md .claude-plugin/marketplace.json
git commit -m "feat(understand): add plugin manifest, README, and marketplace entry"
```

---

## Out of scope (do not build here)

- **blog-publish wiring** for the blog-gate mode (it is documented as a mode; the actual hook into the vault skill is a follow-up).
- **Auto-detect triggers** ("you just shipped something, want to process it?").
- **Spaced re-prompting** from still-open gaps (a scheduler that resurfaces them).
- A bespoke Mochi API client — use the Mochi MCP.

## Acceptance

- `resolve_config.py`: 6 pytest cases pass; resolves deck/session_dir/follow_references/strictness/card_cap with defaults, bool/int parsing, precedence, tilde expansion.
- `explain-back` skill: loads with valid frontmatter; config smoke-run clean in-repo; a dry run elicits an explanation, withholds until attempt, and writes a session record (Mochi skipped gracefully if MCP absent).
- Plugin at 0.1.0; marketplace lists `understand`; catalog version bumped; JSON valid.
