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
allowed-tools: [Read, Grep, Glob]
---

# Compound Retrieve

Search past solutions and engineering principles to surface institutional knowledge before starting work. This skill delegates to the `knowledge-researcher` subagent for fast, grep-based retrieval across YAML-frontmatter solution files.

## Path Resolution

Before any retrieval operation, resolve the solutions directory path.

**Check in this order (first match wins):**

1. **Project-level override**: Read `{project_root}/.claude/compound-knowledge.local.md` — extract `solutions_path` value
2. **User-level override**: Read `~/.claude/compound-knowledge.local.md` — extract `solutions_path` value
3. **Default**: `{project_root}/knowledge/solutions/`

Extract the path from the line starting with `solutions_path:`. Expand `~` to the user's home directory.

If the resolved directory does not exist, inform the user:
> "Solutions directory not found at `{solutions_path}`. Run `/compound-knowledge:setup` to initialize it."

---

## When to Retrieve

- **Before non-trivial debugging**: "Let me check if we've seen this before..."
- **During planning phases**: "Checking for relevant past solutions..."
- **When encountering errors**: Search by symptom/error message
- **When working on a project**: Search by project name for all related solutions
- **Making design decisions**: Surface relevant principles and past architectural choices
- **Working in unfamiliar code**: Check for documented patterns and gotchas

## Retrieval Workflow

### Step 1: Resolve Solutions Path

Follow the Path Resolution algorithm above. Store the result as `{solutions_path}`.

### Step 2: Delegate to Knowledge Researcher

Spawn the knowledge-researcher subagent for fast parallel search:

```
Task(
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

- If a **critical pattern** matches, warn the user prominently
- If a **principle** applies, reference it when making design decisions
- If a **past solution** matches the current problem, suggest the documented fix
- If **nothing found**, say so clearly — don't fabricate relevance

## References

- `references/registry-format.md` — Cross-project registry schema (used by the knowledge-researcher for cross-project search)
