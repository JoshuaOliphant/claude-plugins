# Claude Code Plugin Marketplace

A collection of Claude Code plugins for productivity, learning, and software-development
workflows.

## Installation

```bash
# Add this marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install any plugin
/plugin install <plugin-name>@oliphant-plugins
```

## Available Plugins

Nine plugins, grouped by focus. Current versions live in
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) and each plugin's
`plugin.json` (the source of truth) — they are intentionally not duplicated here so this
list can't drift.

### Productivity & learning

#### mochi-creator

Create evidence-based spaced-repetition flashcards using cognitive-science principles
(Andy Matuschak's five properties of effective prompts). Quality validation, knowledge-type
workflows (factual, conceptual, procedural, salience), anti-pattern detection, and deck/card
management via the Mochi API.

**Requires:** a Mochi account + `MOCHI_API_KEY`.

```bash
/plugin install mochi-creator@oliphant-plugins
export MOCHI_API_KEY="your_api_key_here"
```

#### compound-knowledge

Institutional memory across sessions and projects: capture solved problems, retrieve past
solutions before you start, and graduate recurring lessons into living context
(CLAUDE.md / AGENTS.md). Structured YAML-frontmatter files for fast grep-based retrieval.

**Skills:** `compound-capture`, `compound-retrieve`, `compound-graduate`.

#### understand

Process information for *real* understanding — an antidote to the illusion of clarity. The
`explain-back` skill makes you explain from memory, grades you against the real source,
teaches struggle-then-teach per gap, and outputs Mochi cards plus a resumable session
record.

### Software development

#### autonomous-sdlc

Autonomous SDLC as a state machine on disk, driven by a Stop-hook loop (or a
user-armed self-paced `/loop`) — one verified, committed unit of work per iteration with
decide-log-proceed autonomy and built-in code-review / simplify gates. Architect
and Builder subagents; TDD, BDD, and Beads skills.

#### hexagonal-agents

Build web apps where an AI agent dynamically generates the HTML UI, using
hexagonal / ports-and-adapters architecture with HTMX for interactivity and MCP tools for
data operations.

**Stack:** Claude Agent SDK + FastAPI + HTMX + Tailwind CSS. **Requires:** `ANTHROPIC_API_KEY`.

```bash
/plugin install hexagonal-agents@oliphant-plugins
export ANTHROPIC_API_KEY="your_key_here"
```

#### autoloop

Generate autonomous experiment loops (Karpathy-style autoresearch) that edit → run →
measure a scalar metric → keep improvements via git. Produces `program.md` plus an
immutable `auto/run.sh` with tiered quality gates and structured `METRIC` output, ready to
run with `claude --dangerously-skip-permissions`.

#### observability-harness

Install a local, Docker-free OTLP observability stack (OpenTelemetry → Vector → JSONL,
optionally VictoriaLogs + VictoriaMetrics) into a project and instrument the code — with a
scan-and-propose step for domain-appropriate spans and metrics — then query that telemetry
as a development feedback signal (`observability-query` skill, `status.sh --json` detection
contract, scripted end-to-end `verify.sh`). Composed by autonomous-sdlc as a soft
dependency.

#### review-diff

Local web-based diff review: comment on your working-tree or committed-branch diff in the
browser and feed the comments back to Claude Code.

#### stick-shift

A manually-driven ("disassembled") SDLC — the same `.sdlc/` session format as
autonomous-sdlc, but you drive each phase by hand via slash commands
(`/spec → /plan → /build → /verify → /journal`). Built for legible, narratable live demos;
adopts an in-progress autonomous-sdlc session and stands its loop down.

## Repository Conventions

Each plugin owns its version in `plugins/{name}/.claude-plugin/plugin.json`; that version is
copied into `.claude-plugin/marketplace.json` at publication time. Run
`python scripts/check_marketplace_versions.py` to confirm they match. See
[`CLAUDE.md`](CLAUDE.md) for full development and versioning guidance.

## Contributing

Contributions are welcome — feel free to submit issues or pull requests.

## License

MIT
