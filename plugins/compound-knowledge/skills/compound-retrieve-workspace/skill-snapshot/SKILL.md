---
name: compound-retrieve
description: >
  Use when starting debugging, planning features, encountering errors, making design decisions,
  or working in unfamiliar code. Searches past solutions and engineering principles captured by
  compound-capture to surface institutional knowledge and prevent repeated mistakes. Trigger
  phrases include "have we seen this before", "check knowledge", "search for solutions", "this
  looks familiar", "check if we've solved this", "any past experience with this", "before I
  start, check for existing solutions", or any time past experience might inform the current
  task. Not for capturing new solutions — use compound-capture for that.
allowed-tools: [Read, Grep, Glob, Agent]
---

# Compound Retrieve

## Goal

Surface institutional knowledge from past solutions and engineering principles before starting work. Prevent repeated mistakes by searching YAML-frontmatter solution files captured by compound-capture.

## Dependencies

### Tools

- **`compound-knowledge:knowledge-researcher`** — Haiku-powered subagent that performs fast, parallel grep-based retrieval across solution files. Designed for speed (<30s).

### Connectors

- **Solutions directory** — Resolved via path resolution (see Context). Default: `{project_root}/knowledge/solutions/`
- **Cross-project registry** — `~/.claude/compound-knowledge-registry.md`. Enables searching other projects' knowledge bases when local results are thin.

## Context

### Path Resolution

Resolve the solutions directory before any operation. **First match wins:**

1. **Project-level override**: Read `{project_root}/.claude/compound-knowledge.local.md` — extract `solutions_path` value
2. **User-level override**: Read `~/.claude/compound-knowledge.local.md` — extract `solutions_path` value
3. **Default**: `{project_root}/knowledge/solutions/`

If the resolved directory does not exist:
> "Solutions directory not found at `{solutions_path}`. Run `/compound-knowledge:setup` to initialize it."

### When to Retrieve

- **Before non-trivial debugging**: "Let me check if we've seen this before..."
- **During planning phases**: "Checking for relevant past solutions..."
- **When encountering errors**: Search by symptom/error message
- **When working on a project**: Search by project name for all related solutions
- **Making design decisions**: Surface relevant principles and past architectural choices
- **Working in unfamiliar code**: Check for documented patterns and gotchas

## Process

### Step 0: Load Stored Feedback

Load any stored feedback preferences before starting:

```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py compound-knowledge show-feedback
```

If feedback entries exist, apply them:
- **retrieval_depth** → adjust how many results are surfaced
- **general** → apply to result formatting and presentation

### Step 1: Resolve Solutions Path

Follow the Path Resolution algorithm from Context. Store as `{solutions_path}`.

### Step 2: Delegate to Knowledge Researcher

Spawn the subagent for fast parallel search:

```
Agent(
  subagent_type="compound-knowledge:knowledge-researcher",
  model="haiku",
  prompt="Search for solutions related to: {task_description}. Project: {project_name}. Keywords: {extracted_keywords}. Solutions path: {solutions_path}. Registry path: ~/.claude/compound-knowledge-registry.md",
  description="Search past solutions"
)
```

The researcher reads the registry to identify other knowledge bases for cross-project search when primary results are thin (<3 hits).

### Step 3: Interpret and Apply Results

The knowledge-researcher returns:
1. **Critical patterns** — always-relevant warnings from `critical-patterns.md`
2. **Relevant principles** — engineering wisdom that applies to the current task
3. **Ranked solutions** — scored by project, component, symptom, and tag relevance
4. **Cross-project results** — solutions from other registered knowledge bases
5. **Recommendations** — actionable suggestions based on found solutions

Surface the top results to the user and incorporate insights into your approach:

- If a **critical pattern** matches → warn the user prominently
- If a **principle** applies → reference it when making design decisions
- If a **past solution** matches → suggest the documented fix
- If **nothing found** → say so clearly, don't fabricate relevance

## Output

A concise summary of relevant past solutions and principles, presented to the user with:
- File paths for deeper reading
- Actionable recommendations based on findings
- Prominent warnings for any matching critical patterns
