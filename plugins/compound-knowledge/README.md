# ABOUTME: Marketplace plugin for capturing and retrieving solved problems
# ABOUTME: Creates structured YAML-frontmatter solution files with grep-based search

# Compound Knowledge Plugin

Capture solved problems as structured solution files with YAML frontmatter. Surface past solutions when facing similar problems. Compounds engineering knowledge across sessions and projects.

Inspired by [EveryInc's compound-engineering plugin](https://github.com/EveryInc/compound-engineering-plugin), adapted to be tech-stack agnostic with configurable storage paths.

## Quick Start

### 1. Install the plugin

```bash
claude plugin add joshuaoliphant/claude-plugins --path plugins/compound-knowledge
```

Or clone and link locally:

```bash
git clone https://github.com/joshuaoliphant/claude-plugins.git
cd claude-plugins
claude plugin link plugins/compound-knowledge
```

### 2. Initialize in your project

```
/compound-knowledge:setup
```

This creates the `knowledge/solutions/` directory structure with 10 category subdirectories and a `critical-patterns.md` file.

### 3. Start capturing

After solving a non-trivial problem, say:
- "That worked, capture it"
- "Problem solved"
- `/compound-knowledge`

The skill creates a structured solution file with YAML frontmatter in the appropriate category directory.

### 4. Retrieve past solutions

When starting debugging or planning, the skill automatically searches for relevant past solutions. You can also trigger it explicitly:
- "Check if we've seen this before"
- "Search for solutions related to [topic]"

## Configuration

### Default behavior

Solutions are stored at `{project_root}/knowledge/solutions/` — no configuration needed.

### Custom path (shared knowledge base)

To point all projects at a shared knowledge base (e.g., a second brain), create a config file:

**User-level** (applies to all projects):
```markdown
# ~/.claude/compound-knowledge.local.md
# Compound Knowledge Settings
solutions_path: ~/path/to/your/knowledge/solutions/
```

**Project-level** (overrides user-level for one project):
```markdown
# {project}/.claude/compound-knowledge.local.md
# Compound Knowledge Settings
solutions_path: /absolute/path/to/knowledge/solutions/
```

**Resolution order**: project-level → user-level → default.

### Extending the component enum

The `component` field in YAML frontmatter has a default vocabulary of 22 common technologies. You can use any value — the enum is a starting vocabulary, not a constraint. Add project-specific components (e.g., `postfix`, `kafka`, `helm`) freely.

## How It Works

### Capture flow

```
Problem solved → Gather context → Check for duplicates → Validate YAML → Write solution file
```

1. **Detect** confirmation ("that worked", "it's fixed", `/compound-knowledge`)
2. **Extract** title, project, component, symptoms, severity from conversation
3. **Deduplicate** — grep existing solutions for similar symptoms/titles
4. **Validate** YAML fields against schema enums
5. **Write** solution file to `{solutions_path}/{category}/{filename}.md`
6. **Cross-reference** related solutions

### Retrieval flow

```
New task → Extract keywords → Parallel grep → Score candidates → Return top matches
```

1. **Resolve** solutions path from config
2. **Delegate** to `knowledge-researcher` agent (runs on haiku for speed)
3. **Grep** frontmatter fields in parallel (project, component, symptoms, tags)
4. **Read** `critical-patterns.md` (always)
5. **Score** candidates by relevance (project +3, component +2, symptom +2, tags +1 each)
6. **Return** top 2-5 solutions with key insights

## Directory Structure

```
knowledge/solutions/
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
└── critical-patterns.md
```

## Solution File Format

Each solution file has YAML frontmatter for grep-based retrieval:

```yaml
---
title: "API timeout on large payload upload"
project: my-api
date: 2026-02-14
problem_type: debugging
component: api
symptoms:
  - "TimeoutError after 30s on POST /upload"
  - "Works fine for files under 5MB"
solution_summary: "Increase gunicorn timeout and add streaming upload support"
severity: high
root_cause: resource_limit
resolution_type: config_change
tags: [timeout, upload, gunicorn, streaming]
environment: "Python 3.12, Gunicorn 21.2, FastAPI"
---

## Problem
...
```

See `references/yaml-schema.md` for the full schema and enum values.

## Schema Reference

### Required fields
`title`, `project`, `date`, `problem_type`, `component`, `symptoms`, `solution_summary`, `severity`

### Problem types
`debugging`, `infrastructure`, `patterns`, `workflow`, `performance`, `security`, `ci_cd`, `configuration`, `migration`, `integration`

### Severity levels
`critical`, `high`, `medium`, `low`

See the full schema in [`skills/compound-knowledge/references/yaml-schema.md`](skills/compound-knowledge/references/yaml-schema.md).

## License

MIT
