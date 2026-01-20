---
name: beads-workflow
description: Use when managing work items with Beads CLI, creating task dependencies, tracking feature implementation progress, or orchestrating SDLC workflows with bd commands
version: 1.0.0
---

# Beads Workflow for SDLC

Beads is a git-native issue tracker that stores work items as files. This skill teaches how to use Beads effectively for autonomous SDLC workflows.

## Core Commands

### Finding Work

```bash
bd ready                         # Show tasks with no blockers (ready to implement)
bd list --status=open           # All open tasks
bd list --status=in_progress    # Active work
bd show <bead-id>               # Full task details with dependencies
bd blocked                      # Show all blocked tasks
```

### Creating Work

```bash
# Create a task (priority: 0=critical, 1=high, 2=medium, 3=low, 4=backlog)
bd create --title="Implement feature X" --type=task --priority=1

# Create with full details
bd create --title="Add JWT authentication" --type=feature --priority=1

# Types: task, feature, bug, epic, chore
```

### Managing Dependencies

```bash
# Add dependency: first arg DEPENDS ON second arg
bd dep add <task-that-needs> <task-it-needs>

# Example: tests depend on feature implementation
bd create --title="Implement auth" --type=feature  # → beads-001
bd create --title="Write auth tests" --type=task   # → beads-002
bd dep add beads-002 beads-001  # tests depend on auth

# Remove dependency
bd dep remove <task> <dependency>
```

### Completing Work

```bash
bd close <bead-id>                    # Mark complete (unblocks dependents)
bd close <id1> <id2> <id3>           # Close multiple at once
bd close <bead-id> --reason="Done"   # Close with reason
```

### Synchronization

```bash
bd sync              # Sync with git remote
bd sync --status     # Check sync status
bd stats             # Project statistics
bd doctor            # Check for issues
```

## SDLC Workflow Pattern

### 1. Architect Creates Feature Graph

The architect agent breaks down requirements into Beads with dependencies:

```bash
# Create features in dependency order
bd create --title="Database schema for users" --type=task --priority=1     # → beads-abc
bd create --title="User model and repository" --type=task --priority=1     # → beads-def
bd create --title="Auth middleware" --type=task --priority=1               # → beads-ghi
bd create --title="Login/logout endpoints" --type=feature --priority=1    # → beads-jkl

# Set up dependency chain
bd dep add beads-def beads-abc   # Model depends on schema
bd dep add beads-ghi beads-def   # Middleware depends on model
bd dep add beads-jkl beads-ghi   # Endpoints depend on middleware
```

### 2. Worktree Manager Finds Ready Work

```bash
bd ready  # Shows beads-abc (no blockers)
```

### 3. Implementer Completes Work

```bash
# In worktree, after implementation passes verification
git add -A
git commit -m "feat(beads-abc): implement database schema for users"
bd close beads-abc   # Unblocks beads-def
bd sync
```

### 4. Parallel Execution

When `bd ready` returns multiple tasks, spawn async subagents:

```bash
bd ready
# Output:
# 1. beads-xyz: API validation helpers
# 2. beads-uvw: Error response formatting

# Both can be implemented in parallel (no mutual dependencies)
```

## Best Practices

1. **Granular Tasks**: Each Bead should be implementable in one focused session
2. **Clear Dependencies**: Use `bd dep add` to make blocking relationships explicit
3. **Close Immediately**: Run `bd close` as soon as verification passes
4. **Sync Often**: Run `bd sync` after completing work to share progress
5. **Check Ready First**: Always start with `bd ready` to find unblocked work

## Integration with Worktrees

Each Bead maps to a worktree:

```bash
# Create worktree for a bead
git worktree add ../trees/beads-abc -b feature/beads-abc

# Work in isolation
cd ../trees/beads-abc

# After completion
bd close beads-abc
git worktree remove ../trees/beads-abc
```
