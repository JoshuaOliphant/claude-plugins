# Vault Search Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a global Claude Code skill at `~/.claude/skills/vault-search/` that searches the second brain's `knowledge/solutions/` using grep + semantic MCP search, with three output modes (find, summarize, inject).

**Architecture:** Single SKILL.md with mode routing, a PEP 723 Python script for structured grep search, and two reference files (vault knowledge map, search examples). The skill orchestrates a two-phase search: Phase 1 runs the script for keyword-based frontmatter matching, Phase 2 calls vault-recommender MCP for semantic similarity, then merges and deduplicates results using rank-based normalization.

**Tech Stack:** Python 3.11+ (PEP 723 script), PyYAML, uv, vault-recommender MCP server

**Spec:** `docs/superpowers/specs/2026-03-24-vault-search-skill-design.md`

---

## File Structure

| File | Responsibility |
|------|----------------|
| `~/.claude/skills/vault-search/SKILL.md` | Skill metadata, mode routing, search orchestration, output formatting |
| `~/.claude/skills/vault-search/scripts/search_solutions.py` | PEP 723 CLI — walks knowledge/solutions/, parses YAML frontmatter, scores by keyword match, outputs JSON/JSONL |
| `~/.claude/skills/vault-search/references/vault-knowledge-map.md` | Documents the 12 categories, frontmatter schema, file naming convention, special files |
| `~/.claude/skills/vault-search/references/search-examples.md` | Worked examples for find/summarize/inject output formats |

---

## Task 1: Create `search_solutions.py` — the grep search script

This is the foundation — a standalone PEP 723 script that the SKILL.md will invoke via `uv run`. Building and testing it first means we can validate search quality before writing the skill instructions.

**Files:**
- Create: `~/.claude/skills/vault-search/scripts/search_solutions.py`
- Test against: `~/Library/CloudStorage/Dropbox/python_workspace/second_brain/knowledge/solutions/` (real data, no mocks)

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p ~/.claude/skills/vault-search/scripts
mkdir -p ~/.claude/skills/vault-search/references
```

- [ ] **Step 2: Write failing unit tests for the three core functions**

Create `~/.claude/skills/vault-search/scripts/test_search_solutions.py` (PEP 723 script with `pytest` as an inline dependency). Tests run against real vault data — no mocks.

```python
# Tests for: parse_frontmatter, score_file, search
# Run with: uv run --with pytest pytest test_search_solutions.py -v

def test_parse_frontmatter_returns_dict_with_expected_keys():
    """Parse a known solution file and verify frontmatter fields."""
    result = parse_frontmatter(VAULT_SOLUTIONS_PATH / "patterns" / "bdd-as-agent-handoff-contract-brooklet-20260315.md")
    assert result is not None
    assert result["project"] == "brooklet"
    assert "solution_summary" in result
    assert isinstance(result["tags"], list)

def test_parse_frontmatter_returns_none_for_missing_file():
    result = parse_frontmatter(Path("/nonexistent/file.md"))
    assert result is None

def test_score_file_matches_keywords_case_insensitive():
    fm = {"solution_summary": "TDD workflow pattern", "tags": ["tdd"], "symptoms": [], "project": "test", "problem_type": "patterns", "component": "testing"}
    score = score_file(fm, "some body text about tdd", ["tdd", "workflow"])
    assert score >= 2  # "tdd" in summary + tags + body, "workflow" in summary

def test_score_file_returns_zero_for_no_matches():
    fm = {"solution_summary": "unrelated topic", "tags": ["other"], "symptoms": [], "project": "x", "problem_type": "y", "component": "z"}
    score = score_file(fm, "nothing relevant here", ["xyznonexistent"])
    assert score == 0

def test_search_returns_results_sorted_by_score():
    results = search("TDD workflow", category=None, project=None, top_k=5)
    assert len(results) > 0
    assert len(results) <= 5
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

def test_search_filters_by_category():
    results = search("TDD", category="patterns", project=None, top_k=10)
    for r in results:
        assert r["path"].startswith("patterns/")

def test_search_filters_by_project():
    results = search("autoloop", category=None, project="forkhub", top_k=10)
    for r in results:
        assert r["project"] == "forkhub"

def test_search_returns_empty_for_nonsense_query():
    results = search("xyznonexistent12345", category=None, project=None, top_k=5)
    assert results == []

def test_search_result_has_expected_fields():
    results = search("debugging", category=None, project=None, top_k=1)
    assert len(results) == 1
    r = results[0]
    for field in ["path", "project", "problem_type", "severity", "tags", "summary", "snippet", "score"]:
        assert field in r
    assert len(r["snippet"]) <= 200  # snippet is first 200 chars of body
```

- [ ] **Step 3: Run tests to verify they fail (functions don't exist yet)**

```bash
cd ~/.claude/skills/vault-search/scripts
uv run --with pytest pytest test_search_solutions.py -v
```

Expected: ImportError or NameError — functions not yet defined.

- [ ] **Step 4: Write `search_solutions.py` with PEP 723 header and implementation**

Create `~/.claude/skills/vault-search/scripts/search_solutions.py` with:
- PEP 723 inline metadata (`requires-python = ">=3.11"`, `dependencies = ["pyyaml>=6.0"]`)
- ABOUTME comment (2 lines per project convention)
- `VAULT_SOLUTIONS_PATH` constant pointing to `~/Library/CloudStorage/Dropbox/python_workspace/second_brain/knowledge/solutions/`
- argparse with: positional `query`, `--category`, `--project`, `--top-k` (default 10), `--json` (default), `--jsonl`

The script needs these functions:
- `parse_frontmatter(path: Path) -> dict | None` — reads a .md file, extracts YAML frontmatter between `---` delimiters, returns parsed dict or None on failure
- `score_file(frontmatter: dict, body_snippet: str, keywords: list[str]) -> int` — counts keyword matches across `solution_summary`, `tags`, `symptoms`, `project`, `problem_type`, `component`, and body snippet (first 500 chars). Case-insensitive matching. Returns integer score.
- `search(query: str, category: str | None, project: str | None, top_k: int) -> list[dict]` — walks `VAULT_SOLUTIONS_PATH` recursively, parses frontmatter, applies category/project filters, scores each file, returns top-k sorted descending by score. Each result dict has: `path` (relative to solutions dir), `project`, `problem_type`, `severity`, `tags`, `summary` (from `solution_summary`), `snippet` (first 200 chars of body), `score`.
- `main()` — argparse entry point, calls `search()`, outputs as JSON array (default) or JSONL based on flags.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd ~/.claude/skills/vault-search/scripts
uv run --with pytest pytest test_search_solutions.py -v
```

Expected: All 9 tests pass.

- [ ] **Step 6: Run the script CLI against real vault data to verify end-to-end**

```bash
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "TDD workflow" --top-k 5
```

Expected: JSON array with 5 results, each with frontmatter fields and scores > 0. Results should include files from `patterns/` and `principles/` and `workflow/` that mention TDD.

- [ ] **Step 4: Test category and project filters**

```bash
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "TDD" --category patterns --top-k 3
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "autoloop" --project forkhub
```

Expected: First command returns only files from `patterns/` directory. Second returns only files with `project: forkhub` in frontmatter.

- [ ] **Step 5: Test JSONL output**

```bash
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "skill evaluation" --jsonl --top-k 3
```

Expected: 3 lines, each a valid JSON object (one per line, no array wrapping).

- [ ] **Step 6: Test edge cases**

```bash
# Query with no matches
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "xyznonexistent12345"

# Empty query
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py ""
```

Expected: First returns empty array `[]`. Second returns empty array or top results by default (design choice — empty query = no results is safer).

- [ ] **Step 9: Commit**

Note: The skill lives under `~/.claude/skills/` which is outside the claude-plugins repo. No git tracking needed for the skill files themselves — they're personal global config like other skills in `~/.claude/skills/`. The spec and plan in the claude-plugins repo will be committed separately.

---

## Task 2: Create `references/vault-knowledge-map.md`

This reference file documents the vault structure so the SKILL.md knows what it's searching. Built from real vault data — not guesses.

**Files:**
- Create: `~/.claude/skills/vault-search/references/vault-knowledge-map.md`

- [ ] **Step 1: Write `vault-knowledge-map.md`**

Document the following from the actual vault structure:

**Base path:** `~/Library/CloudStorage/Dropbox/python_workspace/second_brain/knowledge/solutions/`

**12 categories with file counts (current as of 2026-03-24):**

| Category | Files | Description |
|----------|-------|-------------|
| ci-cd | 19 | Pipeline issues, publishing, deployment |
| configuration | 33 | Config management, env vars, settings |
| critical-patterns.md | 1 | High-severity patterns (special file, always check) |
| debugging | 44 | Service failures, error diagnosis |
| infrastructure | 17 | Networking, storage, resource issues |
| integration | 10 | Cross-system compatibility |
| migration | 10 | System transitions, format changes |
| patterns | 69 | Design patterns, architectural approaches |
| performance | 4 | Speed, resource optimization |
| principles | 163 | Engineering wisdom and governing rules |
| security | 8 | Vulnerability fixes, secrets management |
| workflow | 35 | Process improvements, scope management |

**YAML frontmatter schema:**

```yaml
---
title: "Human-readable title"           # string, optional
project: brooklet                        # string — which project this came from
date: 2026-03-15                         # date — when captured
problem_type: patterns                   # string — matches category directory name
component: testing                       # string — what part of the system
symptoms:                                # list[string] — what the problem looked like
  - "Agent produces implementation that doesn't match spec"
solution_summary: "One-line description" # string — the key insight
severity: medium                         # string — low/medium/high/critical
root_cause: missing-validation           # string — why it happened
resolution_type: process-change          # string — how it was fixed
tags: [bdd, tdd, multi-agent]            # list[string] — searchable tags
related_solutions:                       # list[string] — paths to related files
  - "patterns/other-file.md"
---
```

**File naming convention:** `{topic}-{project}-{date}.md`
Example: `bdd-as-agent-handoff-contract-brooklet-20260315.md`

**Special files:**
- `critical-patterns.md` at the root of `solutions/` — contains high-severity patterns that should always be considered.

- [ ] **Step 2: Verify the reference is accurate by spot-checking 2-3 real files**

Read 2-3 solution files and confirm the frontmatter schema matches what's documented.

- [ ] **Step 3: Commit**

---

## Task 3: Create `references/search-examples.md`

Worked examples showing what each mode's output should look like. These teach the SKILL.md the output voice without rigid templates.

**Files:**
- Create: `~/.claude/skills/vault-search/references/search-examples.md`

- [ ] **Step 1: Run the search script to get real results for example queries**

```bash
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "autoloop coverage" --top-k 3
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "skill evaluation" --top-k 5
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "TDD process" --top-k 4
```

Use the real output to build the examples.

- [ ] **Step 2: Write `search-examples.md` with three worked examples**

Each example shows: the query, what Phase 1 (grep) found, what Phase 2 (semantic) found, and the formatted output for that mode.

**Example 1 — find mode:** query "autoloop coverage" → grep matches + semantic matches → pointer output format

**Example 2 — summarize mode:** query "skill evaluation" → reads top files → synthesized digest with key patterns and principles

**Example 3 — inject mode:** query "TDD process" → same search → XML-tagged `<vault-knowledge>` context block

Use real file paths and real summaries from the script output. The examples should feel authentic, not synthetic.

- [ ] **Step 3: Commit**

---

## Task 4: Write the SKILL.md

The main skill file — mode routing, search orchestration, and output formatting. This is where the two-phase search strategy, merge logic, and three output modes come together.

**Files:**
- Create: `~/.claude/skills/vault-search/SKILL.md`

- [ ] **Step 1: Write SKILL.md with frontmatter**

Use the frontmatter from the spec (name, description, allowed-tools). The description is deliberately pushy with trigger phrases to combat under-triggering.

- [ ] **Step 2: Write the search orchestration section**

This section tells Claude how to run the two-phase search:

**Phase 1 — Grep:**
- Run `uv run <skill-path>/scripts/search_solutions.py "<query>" --json --top-k 10`
- Parse the JSON output into a results list

**Phase 2 — Semantic:**
- Call `mcp__vault-recommender__recommend_by_topic` with the query and `top_k=10`
- If the MCP call fails (server unavailable, timeout), log a warning and proceed with grep-only results
- Parse the MCP response — it returns JSON array with `path`, `title`, `score`, `snippet`, `tags`, `reason`

**Merge & Deduplicate (rank-based normalization):**
1. Each phase's results are ranked 1..N
2. Normalized score = `1 - (rank - 1) / N` (top result = 1.0, last = ~0.0)
3. Files appearing in both phases: sum normalized scores (max 2.0)
4. Files in one phase only: use their single normalized score
5. Sort descending by combined score, cap at 10
6. Note which files appeared in both phases (highest-confidence matches)

- [ ] **Step 3: Write the mode routing and output format sections**

Three modes with output formats matching the spec:

- `find` (default): pointers with frontmatter snippets, grouped by search phase
- `summarize`: read top files, synthesize a digest with key patterns and principles
- `inject`: format as `<vault-knowledge>` XML block, no visible output

Include: "If no mode is specified, default to `find`."
Include: "Read `references/search-examples.md` for output format examples."

- [ ] **Step 4: Write the graceful degradation section**

If vault-recommender MCP is unavailable:
- Proceed with grep-only results
- Add note to output: "(Semantic search unavailable — showing grep results only)"
- The skill still provides value from Phase 1 alone

- [ ] **Step 5: Write scope and reference pointers**

- Default scope is `knowledge/solutions/` only (scope expansion to `areas/`, `projects/`, etc. is deferred per spec's Future Considerations)
- Point to `references/vault-knowledge-map.md` for understanding the vault structure and frontmatter schema
- Point to `references/search-examples.md` for output format guidance

- [ ] **Step 6: Test the skill end-to-end by invoking `/vault-search find "TDD workflow"`**

This requires restarting the Claude Code session so the skill is picked up. After restart:

```
/vault-search find "TDD workflow"
```

Expected: The skill triggers, runs Phase 1 (script), runs Phase 2 (MCP), merges results, and outputs formatted pointer list.

- [ ] **Step 7: Test summarize mode**

```
/vault-search summarize "skill evaluation"
```

Expected: Reads top matching files, produces synthesized digest.

- [ ] **Step 8: Test inject mode**

```
/vault-search inject "autoloop patterns"
```

Expected: No visible output, but subsequent queries in the conversation can reference the injected knowledge.

- [ ] **Step 9: Test default mode (no mode keyword)**

```
/vault-search "autoloop"
```

Expected: Behaves identically to `find` mode — returns pointer list with frontmatter snippets.

- [ ] **Step 10: Test graceful degradation**

Temporarily stop the vault-recommender MCP server, then:

```
/vault-search find "debugging"
```

Expected: Grep-only results with a note that semantic search was unavailable.

- [ ] **Step 10: Commit**

---

## Task 5: Run skill-creator eval loop

Use the skill-creator workflow to validate the skill against test prompts and iterate.

**Files:**
- Create: `~/.claude/skills/vault-search-workspace/` (eval workspace, sibling to skill directory)

- [ ] **Step 1: Define 3 test prompts in `evals/evals.json`**

```json
{
  "skill_name": "vault-search",
  "evals": [
    {
      "id": 1,
      "prompt": "/vault-search find \"TDD workflow\"",
      "expected_output": "Pointer list with results from patterns/, principles/, and workflow/ categories",
      "files": []
    },
    {
      "id": 2,
      "prompt": "/vault-search summarize \"agent handoff patterns\"",
      "expected_output": "Synthesized digest mentioning BDD contracts, multi-agent pipelines, and validator patterns",
      "files": []
    },
    {
      "id": 3,
      "prompt": "/vault-search find \"autoloop\" --project forkhub",
      "expected_output": "Results filtered to forkhub project only, mentioning seed staleness and coverage analysis",
      "files": []
    }
  ]
}
```

- [ ] **Step 2: Run with-skill and baseline evals in parallel**

Spawn subagents for each test prompt — one with the skill, one without.

- [ ] **Step 3: Grade, aggregate, launch viewer**

Follow skill-creator steps: grade assertions, run `aggregate_benchmark`, launch `generate_review.py`.

- [ ] **Step 4: Review feedback and iterate**

Read `feedback.json`, improve SKILL.md based on qualitative feedback, rerun.

- [ ] **Step 5: Optimize description triggering**

After the skill is stable, run the description optimization loop per skill-creator instructions.

---

## Task 6: Final verification and cleanup

- [ ] **Step 1: Verify all files are in place**

```bash
ls -la ~/.claude/skills/vault-search/
ls -la ~/.claude/skills/vault-search/scripts/
ls -la ~/.claude/skills/vault-search/references/
```

Expected:
```
SKILL.md
scripts/search_solutions.py
references/vault-knowledge-map.md
references/search-examples.md
```

- [ ] **Step 2: Run search script one final time to confirm it still works**

```bash
uv run ~/.claude/skills/vault-search/scripts/search_solutions.py "debugging patterns" --top-k 3
```

- [ ] **Step 3: Verify SKILL.md is under 500 lines**

```bash
wc -l ~/.claude/skills/vault-search/SKILL.md
```

Expected: < 500 lines.

- [ ] **Step 4: Commit all final changes**
