---
name: sdlc
description: Start an autonomous SDLC workflow with parallel worktrees and verification-driven development
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - Write
argument-hint: "<description of what to build>"
---

# Autonomous SDLC Workflow

You are starting an autonomous software development lifecycle workflow. This workflow uses:

- **Beads** for work tracking and dependency management
- **Git worktrees** for isolated parallel development
- **TDD** for test-driven implementation
- **Verification** as automation gates (not manual approval)

## Arguments

The user has requested: $ARGUMENTS

## Workflow Steps

### Step 1: Create SDLC Marker

Create a marker to enable auto-approval during the workflow:

```bash
mkdir -p .sdlc
echo "$(date -Iseconds)" > .sdlc/started
```

### Step 2: Spawn Architect Agent

Use the Task tool to spawn the architect agent:

```python
Task(
    subagent_type="autonomous-sdlc:architect",
    description="Break down requirements into Beads",
    prompt=f"""
Analyze this request and create a dependency graph of Beads tasks:

{user_request}

Instructions:
1. Explore the codebase to understand existing patterns
2. Break down into granular, implementable tasks
3. Create Beads with `bd create`
4. Set dependencies with `bd dep add`
5. Report the task graph when done
"""
)
```

### Step 3: Spawn Worktree Manager

After the architect completes, spawn the worktree manager:

```python
Task(
    subagent_type="autonomous-sdlc:worktree-manager",
    description="Orchestrate parallel implementation",
    prompt="""
Manage the implementation of ready Beads:

1. Run `bd ready` to find unblocked tasks
2. Create worktrees for each ready Bead
3. Spawn async implementer agents for parallel execution
4. Monitor progress and iterate until all Beads are closed
"""
)
```

### Step 4: Spawn Reviewer

After all implementation is complete, spawn the reviewer:

```python
Task(
    subagent_type="autonomous-sdlc:reviewer",
    description="Review and merge completed work",
    prompt="""
Review all completed feature branches:

1. Check each feature branch for code quality
2. Run full verification
3. Merge approved branches to main
4. Clean up worktrees and branches
"""
)
```

### Step 5: Cleanup

After the workflow completes:

```bash
# Remove SDLC marker
rm -rf .sdlc

# Sync Beads
bd sync

# Report completion
echo "SDLC workflow complete"
```

## Coordination Pattern

```
/sdlc command
    ↓
Architect (Opus)
    ↓ creates Beads with deps
Worktree Manager
    ↓ spawns parallel implementers
Implementer 1 ←──────→ Implementer 2 ←──────→ Implementer 3
    ↓ all complete
Reviewer (Opus)
    ↓ merges to main
Done
```

## Error Handling

If any agent fails:
1. Check Beads status: `bd list --status=open`
2. Check worktree status: `git worktree list`
3. Resume from the failed point or clean up and restart

## Progress Tracking

Use TodoWrite to track high-level progress:

```python
TodoWrite([
    {"content": "Architect: Break down requirements", "status": "in_progress"},
    {"content": "Worktree Manager: Parallel implementation", "status": "pending"},
    {"content": "Reviewer: Merge to main", "status": "pending"},
    {"content": "Cleanup and sync", "status": "pending"}
])
```

Update todos as each phase completes.
