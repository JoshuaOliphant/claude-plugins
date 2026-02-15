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

### 3. Cross-project discovery (automatic)

Setup also registers the knowledge base in `~/.claude/compound-knowledge-registry.md`. This means solutions captured here are automatically discoverable when debugging in other projects.

### 4. Start capturing

After solving a non-trivial problem, say:
- "That worked, capture it"
- "Problem solved"
- `/compound-knowledge`

The skill creates a structured solution file with YAML frontmatter in the appropriate category directory.

### 5. Retrieve past solutions

When starting debugging or planning, the skill automatically searches for relevant past solutions. You can also trigger it explicitly:
- "Check if we've seen this before"
- "Search for solutions related to [topic]"

If local results are thin (<3 hits), the researcher automatically searches other registered knowledge bases via the registry.

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

## Cross-Project Knowledge

By default, each project's solutions are isolated. The **cross-project registry** bridges this gap.

### How it works

A central file at `~/.claude/compound-knowledge-registry.md` tracks every knowledge base on the machine. It records the path, last update date, solution count, and primary components for each registered KB.

### When cross-project search triggers

The knowledge-researcher agent searches the primary knowledge base first. If it finds **fewer than 3 results**, it reads the registry and searches other registered knowledge bases. Cross-project results receive a -1 score penalty so local results are always preferred when available.

### Registration is automatic

Knowledge bases are registered when:
- You run `/compound-knowledge:setup` in a project
- A solution is captured (updates count and components)
- The researcher first accesses a knowledge base

### Example registry

```markdown
### second-brain
- **path**: ~/Dropbox/python_workspace/second_brain/knowledge/solutions/
- **last_updated**: 2026-02-15
- **solution_count**: 69
- **primary_components**: [kubernetes, docker, mcp, claude-code, fastapi]

### my-api
- **path**: ~/projects/my-api/knowledge/solutions/
- **last_updated**: 2026-02-15
- **solution_count**: 3
- **primary_components**: [api, database, auth]
```

## How It Works

### Capture flow

```
Problem solved → Gather context → Check for duplicates → Validate YAML → Write solution file → Update registry
```

1. **Detect** confirmation ("that worked", "it's fixed", `/compound-knowledge`)
2. **Extract** title, project, component, symptoms, severity from conversation
3. **Deduplicate** — grep existing solutions for similar symptoms/titles
4. **Validate** YAML fields against schema enums
5. **Write** solution file to `{solutions_path}/{category}/{filename}.md`
6. **Cross-reference** related solutions
7. **Register** — update `~/.claude/compound-knowledge-registry.md` with current counts and components

### Retrieval flow

```
New task → Read registry → Extract keywords → Parallel grep → Score candidates → Cross-project search → Return top matches
```

1. **Resolve** solutions path from config
2. **Delegate** to `knowledge-researcher` agent (runs on haiku for speed)
3. **Read registry** to identify all knowledge bases on the machine
4. **Grep** frontmatter fields in parallel (project, component, symptoms, tags)
5. **Read** `critical-patterns.md` (always)
6. **Score** candidates by relevance (project +3, component +2, symptom +2, tags +1 each)
7. **Cross-project search** — if <3 primary hits, search other registered knowledge bases (with -1 score penalty)
8. **Return** top 2-5 solutions with key insights, labeled by source KB

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
