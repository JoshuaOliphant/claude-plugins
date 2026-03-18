---
name: beads-workflow
description: >
  MUST use when creating, updating, or closing Beads issues via `bd` commands. Use proactively when
  starting work (bd update --status=in_progress) and completing work (bd close). Trigger: any mention
  of "issue", "task tracking", "what should I work on", "bd create/ready/close", or when the session
  hook indicates beads is active. Provides full bd CLI reference and workflow patterns.
version: 1.0.0
---

# Beads Workflow for SDLC

## Goal

Use the Beads CLI (`bd`) to track work items as git-native files with explicit dependencies. Beads enables autonomous SDLC by making blocking relationships visible — `bd ready` shows what can be worked on now, `bd close` unblocks dependents.

## Dependencies

### Tools

- **`bd` CLI** — Git-native issue tracker. Commands: `bd create`, `bd ready`, `bd close`, `bd dep add`, `bd show`, `bd list`, `bd sync`.
- **Bash** — Runs all `bd` commands.
- **git** — Beads stores work items as files in the repo.

### Connectors

- **Git worktrees** (optional) — Each Bead can map to an isolated worktree for parallel execution.

## Context

### Core Commands

**Finding work:**
```bash
bd ready                         # Tasks with no blockers (ready now)
bd list --status=open           # All open tasks
bd list --status=in_progress    # Active work
bd show <bead-id>               # Full details with dependencies
bd blocked                      # All blocked tasks
```

**Creating work:**
```bash
# Priority: 0=critical, 1=high, 2=medium, 3=low, 4=backlog
# Types: task, feature, bug, epic, chore
bd create --title="Implement feature X" --type=task --priority=1
```

**Managing dependencies:**
```bash
# First arg DEPENDS ON second arg
bd dep add <task-that-needs> <task-it-needs>
bd dep remove <task> <dependency>
```

**Completing work:**
```bash
bd close <bead-id>                    # Unblocks dependents
bd close <id1> <id2> <id3>           # Close multiple at once
bd close <bead-id> --reason="Done"   # Close with reason
```

**Syncing:**
```bash
bd sync              # Sync with git remote
bd stats             # Project statistics
bd doctor            # Check for issues
```

### Best Practices

1. **Granular tasks** — Each Bead should be implementable in one focused session
2. **Clear dependencies** — Use `bd dep add` to make blocking relationships explicit
3. **Close immediately** — Run `bd close` as soon as verification passes
4. **Sync often** — Run `bd sync` after completing work
5. **Check ready first** — Always start with `bd ready` to find unblocked work

## Process

### Step 0: Load Stored Feedback

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback
```

Apply relevant feedback: **beads_workflow**, **general**.

### Step 1: Architect Creates Feature Graph

Break requirements into Beads with dependencies:

```bash
bd create --title="Database schema for users" --type=task --priority=1     # → beads-abc
bd create --title="User model and repository" --type=task --priority=1     # → beads-def
bd create --title="Auth middleware" --type=task --priority=1               # → beads-ghi
bd create --title="Login/logout endpoints" --type=feature --priority=1    # → beads-jkl

# Dependency chain
bd dep add beads-def beads-abc   # Model depends on schema
bd dep add beads-ghi beads-def   # Middleware depends on model
bd dep add beads-jkl beads-ghi   # Endpoints depend on middleware
```

### Step 2: Find Ready Work

```bash
bd ready  # Shows beads-abc (no blockers)
```

When `bd ready` returns multiple tasks, they can be implemented in parallel (no mutual dependencies).

### Step 3: Implement and Close

```bash
# After implementation passes verification
git add -A
git commit -m "feat(beads-abc): implement database schema for users"
bd close beads-abc   # Unblocks beads-def
bd sync
```

### Step 4: Worktree Integration (Optional)

Each Bead can map to an isolated worktree. Claude Code provides native worktree isolation via `isolation: "worktree"` on the Task tool — worktree creation and cleanup are automatic:

```python
# Spawn a builder in an isolated worktree for this Bead
Task(
    subagent_type="autonomous-sdlc:builder",
    description=f"Build beads-abc",
    prompt="Implement the task...",
    isolation="worktree",
    run_in_background=True
)
# On completion: bd close beads-abc
```

## Output

A dependency graph of Beads tracked as git-native files. The graph drives autonomous workflow: `bd ready` determines what to work on, `bd close` cascades unblocking, and `bd sync` shares progress.
