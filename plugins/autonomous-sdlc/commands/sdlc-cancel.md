---
name: sdlc-cancel
description: Stop an active SDLC loop cleanly — sets BLOCKED(cancelled) so the driver releases, then cleans up
allowed-tools:
  - Bash
  - Read
---

# Cancel SDLC Loop

Cancelling means transitioning the state machine, not deleting it — the driver
(Stop hook, or a user-armed `/loop`) releases as soon as the state is terminal, and the
loop stays resumable.

## 1. Stop the loop

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py transition BLOCKED --reason "cancelled by user"
```

If the driver is `loop` (the user armed a bare `/loop`), the next wakeup sees BLOCKED
and ends the loop itself; to stop it sooner the user presses `Esc` while it waits.
A legacy `goal` driver needs the user to run `/goal clear`.

## 2. Clean up parallel work (if any)

```bash
git worktree list                 # remove any task worktrees the loop created
git worktree prune
git branch | grep "feature/.*/"   # delete leftover task branches (not the feature branch)
```

Beads stay open — close them manually if the work is truly abandoned
(`bd close <id> --reason="cancelled"`).

## 3. Keep or discard state

- **Keep `.sdlc/`** (default): re-running `/sdlc` later resumes from where it stopped.
- **Discard**: `rm -rf .sdlc` only if the user explicitly wants a fresh start; the
  decision journal goes with it.

Report what was stopped: feature, state at cancellation, iterations used, and whether
state was kept for resume.
