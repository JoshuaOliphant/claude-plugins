# Claude Code Plugin Marketplace

A collection of Claude Code plugins for productivity and learning workflows.

## Installation

```bash
# Add this marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install any plugin
/plugin install <plugin-name>@oliphant-plugins
```

## Available Plugins

### mochi-creator (v1.2.0)

Create evidence-based spaced repetition flashcards using cognitive science principles from Andy Matuschak's research. Applies the 5 properties of effective prompts (focused, precise, consistent, tractable, effortful) to ensure cards actually work for long-term retention.

**Features:** Quality validation, knowledge-type workflows (factual, conceptual, procedural, salience), anti-pattern detection, template support, deck management, batch operations.

**Requirements:** Mochi.cards account + `MOCHI_API_KEY` environment variable.

```bash
/plugin install mochi-creator@oliphant-plugins
export MOCHI_API_KEY="your_api_key_here"
```

### autonomous-sdlc (v2.0.0)

Autonomous SDLC as a state machine on disk driven by a `/goal` loop — one verified,
committed unit of work per iteration until the PR is open or a written escalation stops
the loop:

- **sdlc-loop** — The state machine: iteration ritual, per-state dispatch, decide-log-proceed autonomy, signs
- **bdd-spec** — Acceptance criteria in Given/When/Then; interactive with a human, autonomous inside a loop
- **bdd-generate** — Scaffold pytest-bdd feature files and step definitions from acceptance criteria
- **tdd-workflow** — Enforce red-green-refactor discipline with test-first development
- **beads-workflow** — Track work items with the Beads CLI (`bd` commands) with explicit dependencies

```bash
/plugin install autonomous-sdlc@oliphant-plugins
```

### hexagonal-agents (v1.1.0)

Build web applications where an AI agent dynamically generates HTML UI using hexagonal/ports-and-adapters architecture with HTMX for interactivity and MCP tools for data operations.

**Stack:** Claude Agent SDK + FastAPI + HTMX + Tailwind CSS.

```bash
/plugin install hexagonal-agents@oliphant-plugins
export ANTHROPIC_API_KEY="your_key_here"
```

### compound-knowledge (v0.5.0)

Capture solved problems and retrieve past solutions as structured YAML-frontmatter files for grep-based retrieval across sessions and projects.

- **compound-capture** — Document solved problems and engineering principles after debugging sessions
- **compound-retrieve** — Search past solutions before starting work to prevent repeated mistakes

```bash
/plugin install compound-knowledge@oliphant-plugins
```

### autoloop (v0.3.0)

Generate autonomous experiment loops that iteratively improve code by editing, running, measuring a scalar metric, and keeping improvements via git commit/reset. Based on Karpathy's autoresearch pattern.

**Generates:** `program.md` + `auto/run.sh` with tiered quality gates, ready to run with `claude --dangerously-skip-permissions`.

```bash
/plugin install autoloop@oliphant-plugins
```

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

MIT
