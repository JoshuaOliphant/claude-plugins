---
name: worktree-manager
description: >-
  Reference pattern for worktree isolation and wave management. Not a spawnable
  agent — the lead orchestrator consults this guide when using worktrees for
  parallel isolation. Claude Code handles worktree lifecycle natively via
  isolation: "worktree" on the Task tool.
---

# Worktree & Wave Management Reference

This is a reference document for the lead orchestrator. Claude Code provides native worktree isolation — you no longer need to manually create, manage, or clean up worktrees.

## Native Worktree Isolation

Claude Code supports `isolation: "worktree"` on the Task tool. When used:

1. **Automatic creation**: A temporary git worktree is created for the agent
2. **Full isolation**: The agent works on an isolated copy of the repo
3. **Automatic cleanup**: If no changes are made, the worktree is cleaned up
4. **Branch returned**: If changes are made, the worktree path and branch name are returned in the result

```python
# Spawn a builder in an isolated worktree — no manual setup needed
Task(
    subagent_type="autonomous-sdlc:builder",
    description=f"Build {task_id}",
    prompt=f"Implement {task_title}...",
    isolation="worktree",
    run_in_background=True
)
```

### WorktreeCreate / WorktreeRemove Hooks

Claude Code fires `WorktreeCreate` and `WorktreeRemove` hook events during worktree lifecycle. Use these for custom setup (e.g., installing dependencies in the new worktree) or teardown.

### TaskCompleted / TeammateIdle Hooks

The plugin registers `TaskCompleted` and `TeammateIdle` hooks via `hooks/scripts/wave-transition-check.sh`. These fire automatically during agent team workflows:

- **`TaskCompleted`**: Fires when a teammate finishes its task. The lead should check `bd ready` or `TaskList` to determine if the current wave is done and spawn the next wave.
- **`TeammateIdle`**: Fires when a teammate goes idle. The lead should assign new tasks or wind down the team. Return `{"continue": false, "stopReason": "..."}` to stop the idle teammate.

Both events are logged to `.sdlc/events/hook-events.jsonl` for audit purposes when an SDLC workflow is active.

## When to Use Worktree Isolation

Use `isolation: "worktree"` when:
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

## Wave Processing Loop

```python
wave = 1
while True:
    # Get ready tasks (no unresolved dependencies)
    ready_tasks = get_ready_tasks()  # bd ready or TaskList

    if not ready_tasks:
        break  # All done

    print(f"=== WAVE {wave}: {len(ready_tasks)} tasks ===")

    # Spawn builders with native worktree isolation (parallel, background)
    builder_results = []
    for task in ready_tasks:
        result = Task(
            subagent_type="autonomous-sdlc:builder",
            description=f"Build {task.id}",
            prompt=f"Implement {task.title}...",
            isolation="worktree",
            run_in_background=True
        )
        builder_results.append(result)

    # Wait for builders — results contain worktree branch names
    # Then spawn validators (can also use worktree isolation)
    for task in ready_tasks:
        Task(
            subagent_type="autonomous-sdlc:validator",
            description=f"Validate {task.id}",
            prompt=f"Verify {task.title}..."
        )

    # INTEGRATE: merge worktree branches into feature branch
    # Each builder result includes the branch name if changes were made
    Task(
        subagent_type="autonomous-sdlc:integrator",
        description=f"Integrate wave {wave}",
        prompt=f"Merge task branches into feature branch..."
    )

    wave += 1
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

With native worktree isolation, cleanup is largely automatic. After all waves:

```bash
# Verify all tasks are closed
bd list --status=open  # Should be empty (or use TaskList)

# Prune any stale worktrees (Claude Code cleans up automatically, but belt-and-suspenders)
git worktree prune

# Sync beads
bd sync
```

## Error Handling

**Builder fails**: The worktree and branch are preserved if changes were made. Check the result for the worktree path, investigate, fix or create a blocker task.

**Validator fails**: Issues are communicated to builder (team mode) or reported to lead (subagent mode).

**Integration fails**: Integrator reports conflicts or verification failures. Fix before next wave.
