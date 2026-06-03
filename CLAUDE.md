# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code plugin marketplace (`oliphant-plugins`). It distributes five plugins that extend Claude Code with specialized skills, subagents, commands, and hooks. Each plugin is self-contained under `plugins/` and registered in `.claude-plugin/marketplace.json`.

## Repository Structure

```
claude-plugins/
├── .claude-plugin/
│   └── marketplace.json            # Catalog of all published plugins (registry)
├── plugins/
│   ├── mochi-creator/              # Evidence-based spaced-repetition flashcards (Mochi API)
│   ├── autonomous-sdlc/            # Agent-team SDLC: TDD, BDD, Beads, verification, worktrees
│   ├── hexagonal-agents/           # Agent-driven HTML-UI web apps (Agent SDK + FastAPI + HTMX)
│   ├── compound-knowledge/         # Capture / retrieve / graduate engineering knowledge
│   └── autoloop/                   # Generate autonomous experiment-optimization loops
├── scripts/
│   ├── check_marketplace_versions.py  # Asserts marketplace.json matches each plugin.json
│   ├── sync_shared.py                 # Asserts/regenerates per-plugin copies of shared artifacts
│   └── shared/                        # Canonical sources for artifacts duplicated across plugins
├── ai_docs/                        # Background research/reference docs (not shipped in plugins)
├── docs/                           # Planning and specifications
├── README.md                       # Marketplace installation instructions
└── CLAUDE.md                       # This file
```

## Plugin Inventory

Each plugin owns its version in `plugins/{name}/.claude-plugin/plugin.json` (the source of truth).

| Plugin | Purpose | Notable pieces |
|---|---|---|
| **mochi-creator** | Create cognitive-science-based flashcards via the Mochi API | `scripts/mochi_api.py` (module + CLI), prompt-quality validation, knowledge-type references |
| **autonomous-sdlc** | Adaptive autonomous SDLC with an agent team | 6 skills (tdd/bdd/beads/verification/feedback), 7 subagents, 4 commands, PostToolUse/Stop hooks |
| **hexagonal-agents** | Web apps where an agent generates HTML UI | Ports-and-adapters arch, MCP tools, Claude Agent SDK, extensive `references/` |
| **compound-knowledge** | Institutional memory: capture → retrieve → graduate | YAML-frontmatter solution files, grep-based retrieval, `knowledge-researcher` subagent |
| **autoloop** | Generate Karpathy-style optimization loops | Produces `program.md` + immutable `auto/run.sh`, `codebase-scout` subagent |

Every plugin also ships a `feedback` skill backed by `scripts/feedback_manager.py` to persist user preferences across sessions.

## Key Architectural Concepts

### Plugin System Structure

Each plugin follows a consistent layout:
- `.claude-plugin/plugin.json` — metadata (name, version, description, author, keywords)
- `skills/<skill>/SKILL.md` — the instruction set / trigger surface for each skill; deep content lives in adjacent `references/*.md` rather than inline
- `agents/*.md` — subagent definitions (frontmatter sets `model`, `tools`, `hooks`, `skills`)
- `commands/*.md` — slash-command entry points
- `hooks/` + `hooks.json` — event-driven validators (e.g. ruff/type checks on Write/Edit)
- `scripts/` — Python helpers, importable and/or CLI-executable

### Subagent Model Tiering (autonomous-sdlc)

The agent team assigns models by the kind of work, optimized for the Opus 4.8 era:
- **Opus** for generative reasoning: **Architect** (planning), **Builder** (implementation/TDD)
- **Sonnet** for verification: **Validator** (read-only checks), **Integrator** (merges)
- **Haiku** for mechanical work: **Documenter** (docs), **PR-Creator** (PR descriptions)

When changing an agent's role significantly, keep the model column in `README.md` and `commands/sdlc.md` in sync with the agent frontmatter.

### Mochi API Client Architecture

`plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py` works as both:
1. An importable module: `from scripts.mochi_api import MochiAPI`
2. A standalone CLI: `python scripts/mochi_api.py list-decks`

It uses HTTP Basic Auth (API key as username), a custom `MochiAPIError`, automatic snake_case ↔ Mochi kebab-case/`?`-suffix translation, and bookmark-based pagination.

### Hexagonal Agents + the Agent SDK

`hexagonal-agents` scaffolds apps where a `ClaudeSDKClient` is the UI layer: its system prompt is a large, static "skill file" teaching the entire UI vocabulary. Because that prefix is identical every turn, connect the client **once and reuse it** so the SDK serves the system prompt and tool definitions from prompt cache. Default model `claude-sonnet-4-6` (use `claude-opus-4-8` for harder reasoning). See `skills/hexagonal-agents/references/sdk_reference.md`.

### Model IDs

Use the current family in examples and generated code: `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`. Subagent frontmatter uses the aliases `opus` / `sonnet` / `haiku`.

## Development Commands

### Mochi API client

```bash
export MOCHI_API_KEY="your_api_key_here"
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py list-decks
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py create-deck "Test Deck"
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py list-cards <deck-id>
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py create-card <deck-id> "# Question\n---\nAnswer"
```

Importable usage:

```python
from scripts.mochi_api import MochiAPI, MochiAPIError

api = MochiAPI()                                  # reads MOCHI_API_KEY
deck = api.create_deck(name="Python Programming")
card = api.create_card(
    content="# What is a decorator?\n---\nA function that modifies another function",
    deck_id=deck["id"],
    manual_tags=["python", "decorators"],
)
```

### Version sync check

```bash
python scripts/check_marketplace_versions.py   # exits non-zero on any drift
```

### Shared-source sync (generate from one source)

Some artifacts must be physically present in multiple self-contained plugins but should never
diverge — e.g. `feedback_manager.py` (shipped by 5 plugins) and `prompt_design_principles.md`
(shared by `mochi-creator` and `understand`). The canonical copy lives under `scripts/shared/`;
each plugin's copy is generated from it.

```bash
python scripts/sync_shared.py            # check for drift (exits non-zero on mismatch)
python scripts/sync_shared.py --write     # regenerate every copy from its canonical source
```

Edit only the canonical file in `scripts/shared/`, then run `--write`. Register a new shared
artifact by appending to `SHARED_ARTIFACTS` in `scripts/sync_shared.py`.

## Important Implementation Details

### Card Content Format

Cards use markdown with `---` separating sides:
```markdown
# Question text
---
Answer text with **formatting**
```

### Field Naming Convention (Mochi / Clojure-style)

- Kebab-case: `deck-id`, `template-id`, `parent-id`
- Boolean suffixes: `archived?`, `trashed?`, `review-reverse?`

The Python client handles this conversion automatically.

### Soft vs Hard Delete

- Soft (reversible, preferred): `api.update_card(card_id, trashed=datetime.utcnow().isoformat())`
- Hard (permanent): `api.delete_card(card_id)`

## Versioning

Two version scopes must stay in sync:

- **`plugin.json`** (per-plugin) is the **source of truth** for each plugin's version. Bump it whenever the plugin changes.
- **`marketplace.json`** has two version fields:
  - `metadata.version` (top-level): the marketplace catalog version. Only bump when adding/removing plugins or changing marketplace structure.
  - Per-plugin `version`: must be **copied from the plugin's `plugin.json`** at publication time. Never maintained independently.

When changing a plugin:
1. Bump the version in `plugins/{name}/.claude-plugin/plugin.json`
2. Copy that version into the matching entry in `.claude-plugin/marketplace.json`
3. Only bump `metadata.version` if the marketplace itself changed (plugin added/removed)
4. Run `python scripts/check_marketplace_versions.py` to confirm they match

## Plugin Installation

```bash
# Add the marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install a plugin
/plugin install mochi-creator@oliphant-plugins
```

## Error Handling

All Mochi API operations can raise `MochiAPIError`; wrap calls in try/except:

```python
from scripts.mochi_api import MochiAPIError

try:
    card = api.create_card(content=content, deck_id=deck_id)
except MochiAPIError as e:
    print(f"Failed to create card: {e}")
```

## Testing and Development

When developing or modifying plugins:
1. Test Python helpers (`mochi_api.py`, `resolve_paths.py`, validators) independently first
2. Verify each `SKILL.md` description accurately reflects capabilities and triggers
3. Ensure `plugin.json` metadata is complete, then re-sync `marketplace.json` and run the version check
4. Test installation from the marketplace structure
5. Keep subagent model assignments consistent across agent frontmatter, `README.md`, and command docs
