# Vault Search Skill — Design Spec

## Overview

A global Claude Code skill (`~/.claude/skills/vault-search/`) that searches La Boeuf's second brain knowledge base to surface patterns, principles, debugging solutions, and engineering wisdom accumulated across all projects. Combines grep-based YAML frontmatter search with semantic embedding search via the vault-recommender MCP server.

## Problem

The second brain at `~/Library/CloudStorage/Dropbox/python_workspace/second_brain/knowledge/solutions/` contains 279+ structured solution files across 12 categories — a rich institutional knowledge base. Currently, this knowledge is only accessible when working inside the second brain project (via compound-knowledge). When working on plugins or other projects, there's no way to tap into this cross-project knowledge without manually switching directories and searching.

## Solution

A global skill with three modes that bridges the second brain's knowledge into any project context.

## Skill Structure

```
~/.claude/skills/vault-search/
├── SKILL.md                        # Mode routing + search orchestration (<500 lines)
├── scripts/
│   └── search_solutions.py         # Grep-based frontmatter search (PEP 723 single-file)
└── references/
    ├── vault-knowledge-map.md      # Second brain knowledge/solutions/ structure & schema
    └── search-examples.md          # Worked examples for each mode's output format
```

## SKILL.md Metadata

```yaml
---
name: vault-search
description: >
  Search La Boeuf's second brain knowledge base (knowledge/solutions/) for
  patterns, principles, debugging solutions, and engineering wisdom accumulated
  across all projects. Combines grep-based frontmatter search with semantic
  embedding search via vault-recommender MCP. Three modes: `find` (pointers +
  snippets), `summarize` (read and digest matches), `inject` (silent context
  injection for other skills/agents). Use this skill whenever working on plugin
  development, encountering a problem that might have been solved before,
  planning features that could benefit from past experience, making architecture
  decisions, or when any skill/agent needs cross-project institutional knowledge.
  Trigger phrases include "search my vault", "check my knowledge base",
  "have I solved this before", "what does my second brain say about",
  "vault search", "search solutions", or when compound-retrieve returns
  thin results and cross-project knowledge might help.
allowed-tools: Read, Grep, Glob, Bash, mcp__vault-recommender__recommend_by_topic
---
```

## Search Strategy

Two-phase search that combines structured and semantic results.

### Phase 1: Grep (structured, fast)

The `search_solutions.py` script searches `knowledge/solutions/` by parsing YAML frontmatter fields:

- `solution_summary` — one-line description
- `tags` — category tags
- `symptoms` — what the problem looked like
- `project` — which project it came from
- `problem_type` — patterns, debugging, workflow, etc.
- `component` — what part of the system

The script tokenizes the query into keywords and scores each file by keyword matches across these fields plus the first ~500 chars of the body. Returns top-k results sorted by score.

### Phase 2: Semantic (fuzzy, conceptual)

Calls `mcp__vault-recommender__recommend_by_topic` with the user's query. Uses the pre-built embedding index (all-MiniLM-L6-v2, 384-dim) with cosine similarity + wiki-link graph boosting + staleness boost.

### Why both phases

Grep catches exact matches on known terms (e.g., "autoloop" finds all autoloop solutions). Semantic search catches conceptual matches that grep misses (e.g., "iterative improvement" surfaces autoloop solutions without the keyword). Together they cover the precision-recall spectrum.

### Graceful Degradation

If the vault-recommender MCP tool is unavailable (server not running, index missing, timeout), log a warning, skip Phase 2, and return grep-only results. The output should indicate which phases produced results (e.g., "Grep only — vault-recommender unavailable"). This ensures the skill always returns something useful even with partial infrastructure.

### Merge & Deduplicate

Results from both phases are merged by file path using rank-based normalization:

1. Each phase's results are ranked 1..N
2. Normalized score = `1 - (rank - 1) / N` (top result = 1.0, last = ~0.0)
3. Files appearing in both phases: sum normalized scores (max 2.0)
4. Files in one phase only: use their single normalized score
5. Sort descending by combined score, cap at 10 (configurable)

### Scope

Default: `knowledge/solutions/` only. Optionally expandable to `knowledge/consolidated/`, `areas/`, and `projects/` when the user requests broader vault search.

## Modes

### `/vault-search find <query>` (default)

Returns pointers with enough context to decide what to read deeper.

**Output format:**
```
## Vault Search: "<query>"

### Grep Matches (N)
1. **<path>**
   - project: X | severity: Y | tags: [a, b, c]
   - _"solution_summary snippet"_

### Semantic Matches (N)
2. **<path>**
   - score: 0.82 | tags: [a, b, c]
   - _"snippet from note"_

Found N unique results (M appeared in both searches).
```

**When to use:** Browsing, quick lookup, deciding what's worth reading in full.

### `/vault-search summarize <query>`

Reads the top matching files and returns a synthesized digest.

**Output format:**
```
## Vault Knowledge: "<query>"

Based on N solutions across project-a, project-b, and project-c:

**Key patterns:**
- [synthesized pattern 1]
- [synthesized pattern 2]

**Relevant principles:**
- [principle 1]
- [principle 2]

**Sources:** [file paths listed]
```

**When to use:** Deep context before making decisions, understanding the full picture.

### `/vault-search inject <query>`

No visible output. Runs the same two-phase search as `find`, formats results as a tagged context block injected silently into the conversation. Designed for programmatic use by other skills and agents.

**Output format (injected into context, not shown to user):**
```xml
<vault-knowledge query="TDD process" results="4" phases="grep+semantic">
  <solution path="principles/test-first-discipline-claude-plugins-20260304.md"
            project="claude-plugins" severity="medium" score="1.8">
    TDD's value is process discipline — Claude writes good tests but not test-FIRST.
    The skill enforces the red-green-refactor cycle, not test quality itself.
  </solution>
  <solution path="workflow/autoloop-tdd-seed-staleness-forkhub-20260316.md"
            project="forkhub" severity="high" score="1.2">
    Seed test files go stale when autoloop edits source but not tests.
    Use two-phase strategy: fix tests first, then optimize.
  </solution>
</vault-knowledge>
```

**When to use:** Other skills call this before their main work — e.g., compound-retrieve when local results are thin, or the autonomous-sdlc architect before designing a feature.

## Script: `search_solutions.py`

PEP 723 single-file script with inline dependencies, runnable via `uv run`.

### Inline Dependencies

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
```

### Interface

```bash
# Basic search
uv run search_solutions.py "TDD workflow"

# Filter by category
uv run search_solutions.py "TDD workflow" --category patterns

# Filter by project
uv run search_solutions.py "TDD workflow" --project claude-plugins

# Limit results
uv run search_solutions.py "TDD workflow" --top-k 5

# Output as JSON array
uv run search_solutions.py "TDD workflow" --json

# Output as JSONL (one object per line, pipe-friendly)
uv run search_solutions.py "TDD workflow" --jsonl
```

### Output Examples

**`--json` (array):**
```json
[
  {
    "path": "patterns/bdd-as-agent-handoff-contract-brooklet-20260315.md",
    "project": "brooklet",
    "problem_type": "patterns",
    "severity": "medium",
    "tags": ["bdd", "patterns", "testing"],
    "summary": "BDD feature files serve as contracts between agent handoffs",
    "snippet": "First 200 chars of body...",
    "score": 3
  }
]
```

**`--jsonl` (one object per line, pipe-friendly):**
```
{"path":"patterns/bdd-as-agent-handoff-contract-brooklet-20260315.md","project":"brooklet","problem_type":"patterns","severity":"medium","tags":["bdd","patterns","testing"],"summary":"BDD feature files serve as contracts between agent handoffs","snippet":"First 200 chars of body...","score":3}
{"path":"workflow/autoloop-tdd-seed-staleness-forkhub-20260316.md","project":"forkhub","problem_type":"workflow","severity":"high","tags":["autoloop","tdd","testing"],"summary":"Seed test files go stale when autoloop edits source but not tests","snippet":"First 200 chars of body...","score":2}
```

### Characteristics

- Read-only — no file modification
- No semantic/embedding search — that's Phase 2 via MCP
- Self-contained via PEP 723 — runs anywhere with `uv run`
- Default output is `--json`; use `--jsonl` for pipe-friendly streaming

## References

### `vault-knowledge-map.md`

Living document that maps the second brain's `knowledge/solutions/` structure:

- Base path
- 12 categories with descriptions and approximate file counts
- YAML frontmatter schema — all fields, types, example values
- File naming convention: `{topic}-{project}-{date}.md`
- Special files: `critical-patterns.md` (high-severity, always check)

Updated when the vault structure evolves.

### `search-examples.md`

Three worked examples showing search → output for each mode:

1. **find**: query "autoloop coverage" → grep + semantic results → pointer output
2. **summarize**: query "skill evaluation" → reads files → synthesized digest
3. **inject**: query "TDD process" → same search, silent context block

Examples teach output voice and density without rigid templates.

## Invocation Patterns

### Explicit (user-facing)

```
/vault-search find "TDD workflow patterns"
/vault-search summarize "skill evaluation benchmarking"
/vault-search "autoloop"                    # defaults to find mode
```

### Programmatic (other skills/agents)

Other skills can reference vault-search in their SKILL.md instructions:

```markdown
Before designing the feature architecture, invoke `/vault-search inject` with
the feature's domain keywords to surface relevant past solutions.
```

## Dependencies

- **vault-recommender MCP server**: Must be configured in `~/.claude.json` (already done). Provides `recommend_by_topic` tool for semantic search.
- **Second brain vault**: At `~/Library/CloudStorage/Dropbox/python_workspace/second_brain/knowledge/solutions/`. Must exist and contain YAML-frontmatter solution files.
- **uv**: For running `search_solutions.py` with inline PEP 723 dependencies.

## Future Considerations

- **Brooklet integration**: The `--jsonl` output flag makes it trivial to pipe results into a brooklet topic for knowledge search analytics (e.g., tracking which patterns get surfaced most often). This would be a brooklet contrib adapter, not a change to this skill.
- **Index freshness**: If the vault-recommender index becomes stale, the skill can call `reload_index` MCP tool. Could add a staleness check (compare index mtime vs vault mtime).
- **Additional scopes**: Expanding beyond `knowledge/solutions/` to search journal entries, project docs, or area notes — controlled by a `--scope` flag.
