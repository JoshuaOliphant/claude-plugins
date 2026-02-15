---
name: worktree-manager
description: >-
  Reference pattern for worktree and wave management. Not a spawnable agent —
  the lead orchestrator consults this guide when using worktrees for parallel
  isolation. Contains wave processing logic, worktree lifecycle, and integration
  patterns.
---

# Worktree & Wave Management Reference

This is a reference document for the lead orchestrator. It describes patterns for managing git worktrees and wave-based parallel execution. The lead absorbs this role — there is no separate worktree-manager agent.

## When to Use Worktrees

Use worktrees when:
- Multiple builders modify overlapping files in parallel
- Heavy parallel test runs interfere with each other
- You want full git isolation between concurrent work

Skip worktrees when:
- Tasks are sequential
- Teammates coordinate file ownership via messaging
- Single builder at a time
- Simple/moderate tasks

## Wave-Based Integration

Tasks form dependency waves. Each wave contains tasks whose dependencies are satisfied.

```
WAVE 1 (no dependencies):
  Builder A ──→ Validator A ──┐
  Builder B ──→ Validator B ──┼──→ INTEGRATE into feature branch
  Builder C ──→ Validator C ──┘

         ↓ feature branch now has Wave 1 code

WAVE 2 (depends on Wave 1):
  Builder D ──→ Validator D ──┐
  Builder E ──→ Validator E ──┼──→ INTEGRATE into feature branch
                              ┘

         ↓ feature branch now has Wave 1 + 2

WAVE 3 (depends on Wave 2):
  Builder F ──→ Validator F ──────→ INTEGRATE
```

**Why integrate between waves?** Wave 2 tasks depend on Wave 1 code. Without integration, Wave 2 builders don't see Wave 1 changes.

## Worktree Lifecycle

### Create Worktrees FROM Feature Branch

```bash
# Branch from feature branch, NOT from main
git worktree add ../trees/{bead-id} -b feature/{feature-name}/{bead-id}

# Verify it was created from feature branch
cd ../trees/{bead-id}
git log --oneline -3  # Should show feature branch history
```

### Task Branch Naming
```
feature/{feature-name}/{bead-id}
```
Example: `feature/user-auth/beads-abc`

### Worktree Directory Layout
```
trees/
├── beads-abc/      # Branch: feature/user-auth/beads-abc
├── beads-def/      # Branch: feature/user-auth/beads-def
└── beads-ghi/      # Branch: feature/user-auth/beads-ghi
```

## Wave Processing Loop

```python
wave = 1
while True:
    # Get ready tasks (no unresolved dependencies)
    ready_tasks = get_ready_beads()  # bd ready

    if not ready_tasks:
        break  # All done

    print(f"=== WAVE {wave}: {len(ready_tasks)} tasks ===")

    # Create worktrees and spawn builders (parallel, background)
    for bead_id in ready_tasks:
        create_worktree(bead_id, feature_branch)
        spawn_builder(bead_id, run_in_background=True)

    # Wait for builders, then spawn validators
    wait_for_builders()
    for bead_id in ready_tasks:
        spawn_validator(bead_id)
    wait_for_validators()

    # INTEGRATE this wave into feature branch
    integrate_wave(feature_branch, task_branches=ready_tasks)

    wave += 1
```

## Spawning Builders in Worktrees

```python
Task(
    subagent_type="autonomous-sdlc:builder",
    description=f"Build {bead_id}",
    prompt=f"""
Implement Bead {bead_id} in worktree ../trees/{bead_id}

Task: {bead_title}

Instructions:
1. cd ../trees/{bead_id}
2. Follow TDD workflow
3. Hooks run Ruff + mypy after each edit automatically
4. Commit your changes
5. Close the Bead when done

Read specs/*-plan.md for acceptance criteria.
""",
    run_in_background=True
)
```

## Spawning Validators in Worktrees

```python
Task(
    subagent_type="autonomous-sdlc:validator",
    description=f"Validate {bead_id}",
    prompt=f"""
Verify the implementation of Bead {bead_id} in worktree ../trees/{bead_id}

Instructions:
1. cd ../trees/{bead_id}
2. Read the plan file for acceptance criteria
3. Run full verification stack
4. Report PASS/FAIL

You CANNOT modify code — only verify.
"""
)
```

## Integration After Each Wave

Use the integrator agent or merge yourself:

```python
# Option A: Dedicated integrator
Task(
    subagent_type="autonomous-sdlc:integrator",
    description=f"Integrate Wave {wave}",
    prompt=f"""
Merge task branches into feature/{feature_name}:
{task_branches}
"""
)

# Option B: Merge yourself
for branch in task_branches:
    git merge branch --no-ff
```

## Cleanup

After all waves complete:

```bash
# Verify all tasks are closed
bd list --status=open  # Should be empty

# Clean up worktrees
git worktree list
git worktree prune

# Remove worktree directories
rm -rf ../trees/

# Sync
bd sync
```

## Error Handling

**Builder fails**: Check worktree for partial work, review hook output, fix or create blocker task.

**Validator fails**: Issues are communicated to builder (team mode) or reported to lead (subagent mode).

**Integration fails**: Integrator reports conflicts or verification failures. Fix before next wave.
