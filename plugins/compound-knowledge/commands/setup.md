---
allowed-tools: [Read, Write, Bash, Glob]
description: Initialize compound knowledge directory structure and optional path configuration
argument-hint: "[path]"
---

# Compound Knowledge Setup

Initialize the directory structure for capturing solutions and optionally configure a custom storage path.

## Setup Workflow

### Step 1: Determine Solutions Path

Check if an argument was provided:
- **Argument given** (e.g., `/compound-knowledge:setup ~/my-knowledge/solutions/`): Use that path
- **No argument**: Ask the user:

> Where should solutions be stored?
>
> 1. **`knowledge/solutions/` in this project** (default — good for project-specific knowledge)
> 2. **Custom path** (e.g., a shared second brain — good for cross-project knowledge)

If option 1: use `{project_root}/knowledge/solutions/`
If option 2: ask for the absolute path

### Step 2: Create Directory Structure

Create the following directories under the chosen path:

```
{solutions_path}/
├── debugging/
├── infrastructure/
├── patterns/
├── workflow/
├── performance/
├── security/
├── ci-cd/
├── configuration/
├── migration/
├── integration/
└── critical-patterns.md
```

Use `mkdir -p` via Bash for the directories.

### Step 3: Create `critical-patterns.md`

Write the starter file at `{solutions_path}/critical-patterns.md`:

```markdown
# Critical Patterns

High-severity patterns that should be considered for every task. The knowledge-researcher agent reads this file on every search.

Add entries here when you encounter patterns with `severity: critical` or `severity: high` that apply broadly across projects.

## Format

### [Pattern Title]
- **Component**: {component}
- **Pattern**: {1-2 sentence description}
- **Why it matters**: {consequence of ignoring}
- **Source**: `{category}/{solution-file}.md`
```

### Step 4: Create `.local.md` Config (If Non-Default Path)

If the user chose a custom path (not `{project_root}/knowledge/solutions/`), create a config file:

**Project-level** (recommended for project-specific overrides):
Write `{project_root}/.claude/compound-knowledge.local.md`:

```markdown
# Compound Knowledge Settings
solutions_path: {absolute_path_to_solutions}/
```

**User-level** (for a single shared knowledge base across all projects):
If the user indicates this should be their default for all projects, write `~/.claude/compound-knowledge.local.md` instead.

Ask the user which level they prefer:
> Should this be the default for **all projects** (user-level) or just **this project** (project-level)?

### Step 5: Report

Print a summary of what was created:

```
Compound Knowledge initialized!

  Solutions directory: {solutions_path}
  Categories created: 10
  Config file: {config_path} (or "none — using default location")

  Next steps:
  - Solve a problem, then say "capture that" or invoke /compound-knowledge
  - Search past solutions with "check if we've seen this before"
  - Add critical patterns to critical-patterns.md as you discover them
```
