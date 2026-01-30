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

### Step 4: Spawn Reviewer (When Appropriate)

After implementation completes, decide whether to spawn the reviewer based on:

**Always spawn reviewer when:**
- Feature branches exist that need merging
- Complex changes were made (refactoring, new features, business logic)
- Multiple files were modified in non-trivial ways

**Use judgment - reviewer may be skipped when:**
- Simple deletions or cleanup (removing deprecated code/plugins)
- Documentation-only changes
- Trivial configuration updates
- The worktree manager already verified the changes thoroughly

When spawning the reviewer:

```python
Task(
    subagent_type="autonomous-sdlc:reviewer",
    description="Review and merge completed work",
    prompt="""
Review completed work:

1. If feature branches exist:
   - Check each branch for code quality
   - Run full verification
   - Merge approved branches to main
   - Clean up worktrees and branches

2. If changes were made directly on main:
   - Review recent commits (git log/diff)
   - Verify changes match requirements
   - Confirm no issues or incomplete work
   - Report findings
"""
)
```

**Note:** The coordinator has full context about what was implemented. Use that context to decide if a second pair of eyes adds value before marking the workflow complete.

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
    ↓
Complex changes? ──YES──→ Reviewer (Opus) ──→ merges/validates
    │                              ↓
    └──NO (simple)─────────────────┘
    ↓
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
