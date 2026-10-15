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

Six plugins, grouped by focus. Current versions live in
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

#### compost

One software-engineering workflow made from Matt Pocock's skills, superpowers, pstack, Imbue's
blueprint, and the retired autonomous-sdlc and stick-shift plugins: specs with Given/When/Then
acceptance criteria, tracer-bullet issues in your tracker, builds that fit tests into the existing
suite, and review by subagents on every change. It also carries what used to be the review-diff
plugin (comment on a diff in your browser) and jev-lint (semantic lint for Python).
`compost:setup` configures a repo and offers to switch off the collections compost replaces.
See [plugins/compost](plugins/compost/README.md).

#### hexagonal-agents

Build web apps where an AI agent dynamically generates the HTML UI, using
hexagonal / ports-and-adapters architecture with HTMX for interactivity and MCP tools for
data operations.

**Stack:** Claude Agent SDK + FastAPI + HTMX + Tailwind CSS. **Requires:** `ANTHROPIC_API_KEY`.

```bash
/plugin install hexagonal-agents@oliphant-plugins
export ANTHROPIC_API_KEY="your_key_here"
```

#### observability-harness

Install a local, Docker-free OTLP observability stack (OpenTelemetry → Vector → JSONL,
optionally VictoriaLogs + VictoriaMetrics) into a project and instrument the code — with a
scan-and-propose step for domain-appropriate spans and metrics — then query that telemetry
as a development feedback signal (`observability-query` skill, `status.sh --json` detection
contract, scripted end-to-end `verify.sh`).

#### superfan

One headless Claude per component, watching its telemetry on a local launchd schedule through
the read-only MCP servers you already have (Splunk, Prometheus, Kubernetes, ...). Page-worthy
findings raise a clickable macOS notification that opens a triage session; every verdict
(real, noise, known) feeds a ledger that teaches the superfan what normal looks like.
See [plugins/superfan](plugins/superfan/README.md).

## Repository Conventions

Each plugin owns its version in `plugins/{name}/.claude-plugin/plugin.json`; that version is
copied into `.claude-plugin/marketplace.json` at publication time. Run
`python scripts/check_marketplace_versions.py` to confirm they match. See
[`AGENTS.md`](AGENTS.md) for full development and versioning guidance.

## Contributing

Contributions are welcome — feel free to submit issues or pull requests.

## License

MIT
