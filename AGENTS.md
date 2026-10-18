# AGENTS.md

This file provides guidance to coding agents (Claude Code reads it natively) when working in this repository.

## Project Overview

This is a Claude Code plugin marketplace (`oliphant-plugins`). It distributes seven plugins that extend Claude Code with specialized skills, subagents, commands, and hooks. Each plugin is self-contained under `plugins/` and registered in `.claude-plugin/marketplace.json`.

## Repository Structure

```
claude-plugins/
├── .claude-plugin/
│   └── marketplace.json            # Catalog of all published plugins (registry)
├── plugins/
│   ├── mochi-creator/              # Evidence-based spaced-repetition flashcards (Mochi API)
│   ├── hexagonal-agents/           # Agent-driven HTML-UI web apps (Agent SDK + FastAPI + HTMX)
│   ├── compound-knowledge/         # Capture / retrieve / graduate engineering knowledge
│   ├── observability-harness/      # Local Docker-free OTLP stack (OTel → Vector → JSONL/Victoria*)
│   ├── understand/                 # Explain-back learning loop (graded recall → Mochi cards)
│   ├── compost/                    # One SDLC workflow composted from several skill collections
│   └── superfan/                   # Scheduled per-component telemetry watchers (headless Claude + launchd)
├── scripts/
│   ├── cloud-setup.sh                 # Cloud environment setup script: installs compost + typesafe plugins
│   ├── check_all.py                   # One-command repo health check (versions + sync + tests + lint + format)
│   ├── check_marketplace_versions.py  # Asserts marketplace.json ⇄ plugin.json (versions + registration)
│   ├── check_version_bumps.py         # CI on PRs into main: every changed plugin's version is above main's
│   ├── sync_shared.py                 # Asserts/regenerates per-plugin copies of shared artifacts
│   └── shared/                        # Canonical sources for artifacts duplicated across plugins
├── knowledge/                      # Captured solutions (compound-knowledge output for this repo)
├── ai_docs/                        # Background research/reference docs (not shipped in plugins)
├── docs/agents/                    # How the compost skills work in this repo (tracker, domain docs, gates, core docs, observability)
├── pyproject.toml                  # Repo-wide dev group (pytest, ruff) and their config
├── CONTEXT-MAP.md                  # Bounded contexts and their glossaries
├── README.md                       # Marketplace installation instructions
└── AGENTS.md                       # This file
```

## Plugin Inventory

Each plugin owns its version in `plugins/{name}/.claude-plugin/plugin.json` (the source of truth).

| Plugin | Purpose | Notable pieces |
|---|---|---|
| **mochi-creator** | Create cognitive-science-based flashcards via the Mochi API | `scripts/mochi_api.py` (module + CLI), prompt-quality validation, knowledge-type references |
| **hexagonal-agents** | Web apps where an agent generates HTML UI | Ports-and-adapters arch, MCP tools, Claude Agent SDK, extensive `references/` |
| **compound-knowledge** | Institutional memory: capture → retrieve → graduate | YAML-frontmatter solution files, grep-based retrieval, `knowledge-researcher` subagent |
| **observability-harness** | Local Docker-free OTLP stack (OTel → Vector → JSONL/Victoria*) + instrumentation | setup skill with scan-and-propose, `observability-query` skill, `status.sh --json` detection contract, scripted `verify.sh` |
| **understand** | Process information for real understanding (antidote to the illusion of clarity) | `explain-back` skill: graded recall, struggle-then-teach per gap, Mochi-card output, resumable session record |
| **superfan** | One headless Claude per component watching telemetry through read-only MCP tools | `setup` + `triage` skills, `scripts/superfan.py` (run loop, ledger, launchd, notifiers), `scripts/watch_prompt.md` |
| **compost** | One SDLC workflow made from Matt Pocock's skills, superpowers, pstack, blueprint, and the retired autonomous-sdlc and stick-shift plugins | 17 skills linked by Next moves plus the user-invoked `/compost:wait-what`, `canon/` essays, `compost:prune` + `scripts/doc_refs.py` keeping docs to the core, `compost:thin` + `scripts/thin.py` finding tests no mutant needs and, as `thin.py survivors`, the mutants a diff leaves alive for `compost:verify`, `/compost:review-changes` workflow + `reviewer` agent, Jev tools (`scripts/jev.py`), browser diff review (`scripts/review_diff/`), semantic Python lint (`scripts/lint/`), `pile.toml` + `scripts/pile.py` tracking upstream sources for `compost:turn` |

## Key Architectural Concepts

### Plugin System Structure

Each plugin follows a consistent layout:
- `.claude-plugin/plugin.json` — metadata (name, version, description, author, keywords)
- `skills/<skill>/SKILL.md` — the instruction set / trigger surface for each skill; deep content lives in adjacent `references/*.md` rather than inline
- `agents/*.md` — subagent definitions (frontmatter sets `model`, `tools`, `hooks`, `skills`)
- `commands/*.md` — slash-command entry points
- `hooks/` + `hooks.json`: plugin-wide hooks (compost's implement-run Stop guard, and its one hooks module `compost.ts` carrying the skill-drift and architecture-review mods)
- `scripts/` — Python helpers, importable and/or CLI-executable

### compost

compost has no state machine: each skill ends with Next moves naming the skills that usually
follow, and work is tracked in the repo's issue tracker. Its `[replaces]` table in `pile.toml`
lists the plugins and skills it supersedes, which `compost:setup` offers to switch off. Its own
vocabulary is in `plugins/compost/CONTEXT.md`; the workflow is described in
`plugins/compost/README.md`.

### Mochi API Client Architecture

`plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py` works as both:
1. An importable module: `from scripts.mochi_api import MochiAPI`
2. A standalone CLI: `python scripts/mochi_api.py list-decks`

It uses HTTP Basic Auth (API key as username), a custom `MochiAPIError`, automatic snake_case ↔ Mochi kebab-case/`?`-suffix translation, and bookmark-based pagination.

### Hexagonal Agents + the Agent SDK

`hexagonal-agents` scaffolds apps where a `ClaudeSDKClient` is the UI layer: its system prompt is a large, static "skill file" teaching the entire UI vocabulary. Because that prefix is identical every turn, connect the client **once and reuse it** so the SDK serves the system prompt and tool definitions from prompt cache. Default model `claude-sonnet-5-5` (use `claude-opus-5-5` for harder reasoning). See `skills/hexagonal-agents/references/sdk_reference.md`.

### Model IDs

Use the current family in examples and generated code: `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, and `claude-fable-5-1` for the most demanding reasoning. Subagent frontmatter uses the aliases `opus` / `sonnet` / `haiku` / `fable`.

## Development Commands

Mochi client: run `python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py` with no arguments for its commands; the API is documented in its docstrings and the mochi-creator SKILL.md.

### Version sync check

```bash
python scripts/check_marketplace_versions.py   # exits non-zero on any drift
```

### Shared-source sync (generate from one source)

Some artifacts must be physically present in multiple self-contained plugins but should never
diverge — e.g. `config_loader.py` (the `.claude/<name>.local.md` reader shared by
`compound-knowledge` and `understand`) and
`prompt_design_principles.md` (shared by `mochi-creator` and `understand`). The canonical copy
lives under `scripts/shared/`; each plugin's copy is generated from it.

```bash
python scripts/sync_shared.py            # check for drift (exits non-zero on mismatch)
python scripts/sync_shared.py --write     # regenerate every copy from its canonical source
```

Edit only the canonical file in `scripts/shared/`, then run `--write`. Register a new shared
artifact by appending to `SHARED_ARTIFACTS` in `scripts/sync_shared.py`.

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
4. Run `python scripts/check_marketplace_versions.py` to confirm they match. This
   check is bidirectional: it also fails if a directory under `plugins/` has no
   marketplace entry, or if a non-plugin directory (no `.claude-plugin/plugin.json`)
   is sitting under `plugins/`.

On an integration branch that merges several issues (a `compost:implement` run), lanes leave
versions alone, since per-lane bumps conflict on every merge. One commit on that branch bumps
every plugin the branch changed, and it goes in right after the first lane lands, before the draft
PR opens, so every push to the PR runs CI green instead of failing the bump check until the end. A
plugin first changed by a later lane gets its bump in the commit that lands that lane. A lane commit without a bump is not a
finding; a branch reaching `main` with a changed plugin still at its old version is. CI enforces
this on pull requests into `main` with `python scripts/check_version_bumps.py` (base
`origin/main`; a plugin's `tests/` doesn't count as shipped content). The changed plugin's
version must be strictly greater than the one on current `main`, not the fork point: two branches
that both bump 0.8.1 to 0.9.0 pass alone, but the second fails once the first has merged, because
an install that recorded 0.9.0 never re-fetches it. When the check fails that way, bump past
`main`'s version.

## Testing and Development

When developing or modifying plugins:
1. Test Python helpers (`mochi_api.py`, `resolve_paths.py`, validators) independently first
2. Verify each `SKILL.md` description accurately reflects capabilities and triggers
3. Ensure `plugin.json` metadata is complete, then re-sync `marketplace.json` and run the version check
4. Test installation from the marketplace structure
5. Keep subagent model assignments consistent across agent frontmatter, `README.md`, and command docs

## Agent skills

### Issue tracker

GitHub issues via `gh`; specs are parent issues labelled `spec`, slices are sub-issues. See
`docs/agents/issue-tracker.md`.

### Domain docs

Multiple contexts, one per plugin plus the marketplace, listed in `CONTEXT-MAP.md`. See
`docs/agents/domain.md`.

### Tests and gates

pytest per plugin; `scripts/check_all.py` plus the 100% coverage gate in compost. See `docs/agents/testing.md`.

### Observability

None: nothing here runs long enough to observe. See `docs/agents/observability.md`.

### Docs

Code is the source of truth; docs hold only what it can't say, in the core docs. Put a new fact in
a name, type, test, or comment before a core doc, and never in a new file. See `docs/agents/docs.md`.
