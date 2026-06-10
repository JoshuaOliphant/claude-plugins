---
name: sdlc-status
description: Show the state of the SDLC loop — current state, iteration budget, decisions, progress
allowed-tools:
  - Read
  - Bash
---

# SDLC Loop Status

The loop's entire state is on disk. Render it; don't infer it.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py status   # exits with a message if no loop
tail -15 .sdlc/progress.md 2>/dev/null
cat .sdlc/escalation.md 2>/dev/null                          # only present when BLOCKED
bd ready 2>/dev/null || echo "(beads not in use)"
git log --oneline -5
```

## Report

```
## SDLC Loop: {feature}

**State**: {STATE} ({iteration}/{max_iterations} iterations)
**Current task**: {current_task or —}
**Decisions logged**: {N} (reviewable in .sdlc/decisions.jsonl)

### Recent progress
{last few lines of progress.md}

### If BLOCKED
{escalation.md summary + how to resume: answer/fix, then re-run /sdlc}

### If DONE
{PR URL from progress.md}
```
