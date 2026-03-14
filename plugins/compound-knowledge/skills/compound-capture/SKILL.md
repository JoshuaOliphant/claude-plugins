---
name: compound-capture
description: >
  Use after solving non-trivial problems, completing debugging sessions, discovering reusable
  patterns, making architecture decisions, or when the user confirms something works. Trigger
  phrases include "that worked", "it's fixed", "problem solved", "document this solution",
  "capture this pattern", "save this for next time", "we should remember this", "finally got
  it working", and explicit /compound-capture invocations. This skill
  captures solved problems and engineering principles as structured YAML-frontmatter files
  for grep-based retrieval across sessions and projects. Not for searching existing knowledge
  — use compound-retrieve for that.
allowed-tools: [Read, Write, Edit, Grep, Glob]
---

# Compound Capture

## Goal

Capture solved problems and engineering principles as searchable YAML-frontmatter markdown files. Every capture creates a structured file that enables fast grep-based retrieval in future sessions, across projects.

## Dependencies

### Tools

- **Grep** — Searches existing solutions for duplicates and cross-references
- **Glob** — Counts solution files for registry updates
- **Write/Edit** — Creates solution files and updates cross-references

### Connectors

- **Solutions directory** — Resolved via path resolution (see Context). Default: `{project_root}/knowledge/solutions/`
- **Cross-project registry** — `~/.claude/compound-knowledge-registry.md`. Tracks all knowledge bases on the machine.

## Context

### Path Resolution

Resolve the solutions directory before any operation. **First match wins:**

1. **Project-level override**: Read `{project_root}/.claude/compound-knowledge.local.md` — extract `solutions_path` value
2. **User-level override**: Read `~/.claude/compound-knowledge.local.md` — extract `solutions_path` value
3. **Default**: `{project_root}/knowledge/solutions/`

If the resolved directory does not exist:
> "Solutions directory not found at `{solutions_path}`. Run `/compound-knowledge:setup` to initialize it."

### Triviality Filter

**Skip capture for:** typos, syntax errors, missing imports, one-line fixes with no investigation, obvious bugs caught immediately.

**Proceed with capture for:** problems requiring multiple investigation attempts, non-obvious root causes, solutions involving code examples or architecture decisions, issues likely to recur.

### Solution vs Principle

| | Solution | Principle |
|---|---|---|
| **Has** | `symptoms` (required) | `statement` + `confidence` (required) |
| **Lives in** | Category directory (`debugging/`, `patterns/`, etc.) | `principles/` directory |
| **Documents** | A specific problem and its fix | Generalizable engineering wisdom |
| **Heuristic** | Someone could grep for an error message and find this | Advice that applies across many situations |

### Directory Structure

```
{solutions_path}/
├── debugging/        # Service failures, error diagnosis
├── infrastructure/   # Networking, storage, resource issues
├── patterns/         # Design patterns, architectural approaches
├── workflow/         # Process improvements, scope management
├── performance/      # Speed, resource optimization
├── security/         # Vulnerability fixes, secrets management
├── ci-cd/           # Pipeline issues, publishing, deployment
├── configuration/    # Config management, env vars, settings
├── migration/        # System transitions, format changes
├── integration/      # Cross-system compatibility
├── principles/       # Engineering wisdom and governing principles
└── critical-patterns.md  # High-severity patterns (always read)
```

### YAML Schema and Templates

For field definitions, enum values, and validation rules:

→ **`references/yaml-schema.md`**

For file templates:

→ **`references/solution-template.md`**
→ **`references/principle-template.md`**

For cross-project registry schema:

→ **`references/registry-format.md`**

## Process

### Step 1: Resolve Solutions Path

Follow the Path Resolution algorithm from Context. Store as `{solutions_path}`.

### Step 2: Apply Triviality Filter

If the problem is trivial (see filter in Context), skip capture.

If unsure:
> "This seems like a solution worth documenting. Want me to capture it?"

### Step 3: Gather Context

Determine whether this is a **solution** or a **principle** (see Context table).

**For solutions**, extract from the conversation:

| Field | Required? |
|-------|-----------|
| `title` — Clear problem description | Yes |
| `date` — Auto-populated as YYYY-MM-DD | Yes |
| `project` — Current working directory or explicit mention | Yes |
| `problem_type` — Maps to category directory (see `yaml-schema.md`) | Yes |
| `component` — Technology involved | Yes |
| `symptoms` — Error messages, observable behavior | Yes |
| `solution_summary` — One-line fix description | Yes |
| `severity` — critical, high, medium, low | Yes |
| `root_cause`, `resolution_type`, `tags`, `environment` | No |

**For principles**, extract:

| Field | Required? |
|-------|-----------|
| `title` — Principle name | Yes |
| `date` — Auto-populated as YYYY-MM-DD | Yes |
| `project` — Where validated, or "cross-project" | Yes |
| `problem_type` — Always `principles` | Yes |
| `component` — Technology domain | Yes |
| `statement` — Concise, generalizable rule (1-2 sentences) | Yes |
| `confidence` — high, medium, low | Yes |
| `solution_summary` — One-line description | Yes |
| `severity` — Impact if ignored | Yes |

If critical fields are missing, ask and wait:
> "I need a few details to capture this properly: What project is this for? What were the symptoms?"

### Step 4: Check for Duplicates

Search `{solutions_path}` for similar existing solutions:

```
Grep(pattern="symptoms:.*{key_symptom}", path="{solutions_path}", output_mode="files_with_matches")
Grep(pattern="title:.*{similar_term}", path="{solutions_path}", output_mode="files_with_matches")
```

- **Different root cause** → Create new file, add `related_solutions` cross-reference
- **Same issue, new context** → Update existing file
- **Exact duplicate** → Skip, inform user: "This is already documented in [file]"

### Step 5: Validate YAML

Read `references/yaml-schema.md` and validate all enum fields. **Block creation if validation fails.** Report which fields are invalid and suggest corrections.

### Human Checkpoint: Present Capture Summary

Before writing, present:

```
Capturing: {solution|principle}
  Title: {title}
  Project: {project}
  Component: {component}
  Category: {problem_type} → {solutions_path}/{category}/
  Severity: {severity}
  File: {filename}.md

Proceed?
```

**Wait for user confirmation before writing.**

### Step 6: Create File

1. Generate filename: `{sanitized-symptom}-{project}-{YYYYMMDD}.md` (lowercase, hyphens, max 80 chars)
2. Read the appropriate template from references (`solution-template.md` or `principle-template.md`)
3. Write the file with validated YAML frontmatter and structured content

### Step 7: Cross-Reference with Bidirectional Links

Links must be **bidirectional** — if file A references file B, file B must reference file A.

1. Add `related_solutions` entries to the new file pointing to matches from Step 4
2. Update each related file to add a backlink (cap at 5 entries per file)
3. Use `category/filename.md` format for all paths (never absolute paths)

Present summary:
```
Created: {solutions_path}/{category}/{filename}.md
Related solutions:
  - [title](path) — {why related}
Updated backlinks in:
  - {path1}
  - {path2}
```

### Step 8: Update Registry

Update `~/.claude/compound-knowledge-registry.md` so this knowledge base is discoverable from other projects.

1. Read the registry (create from `references/registry-format.md` header if missing)
2. Count solution files and extract unique components
3. Update existing entry in-place (path is unique key) or append new entry

## Output

A structured markdown file in `{solutions_path}/{category}/` with:
- YAML frontmatter validated against `references/yaml-schema.md`
- Structured body following `references/solution-template.md` or `references/principle-template.md`
- Bidirectional cross-references to related solutions
- Updated cross-project registry entry
