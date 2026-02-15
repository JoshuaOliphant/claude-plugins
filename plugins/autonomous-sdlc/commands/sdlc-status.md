---
name: sdlc-status
description: Check the status of an active SDLC workflow
allowed-tools:
  - Read
  - Bash
  - Glob
---

# SDLC Status

Check the current status of an autonomous SDLC workflow.

## Status Checks

### 1. Workflow Active?

```bash
if [ -d ".sdlc" ]; then
    echo "SDLC workflow is ACTIVE"
    cat .sdlc/started 2>/dev/null && echo "Started at above timestamp"
    cat .sdlc/description 2>/dev/null && echo "Description: $(cat .sdlc/description)"
    cat .sdlc/mode 2>/dev/null && echo "Coordination mode: $(cat .sdlc/mode)"
else
    echo "No active SDLC workflow"
fi
```

### 2. Beads Status

```bash
echo "=== Open Beads ==="
bd list --status=open

echo ""
echo "=== Blocked Beads ==="
bd blocked

echo ""
echo "=== Ready to Work ==="
bd ready
```

### 3. Worktree Status

```bash
echo "=== Active Worktrees ==="
git worktree list

echo ""
echo "=== Feature Branches ==="
git branch -a | grep feature/
```

### 4. Agent Teams Status

```bash
echo "=== Agent Teams ==="
if [ -n "$CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" ]; then
    echo "Agent teams: ENABLED"
else
    echo "Agent teams: NOT AVAILABLE"
fi
```

### 5. Recent Completions

```bash
echo "=== Recently Closed Beads ==="
bd list --status=closed --limit=10
```

## Summary Report

Provide a summary in this format:

```
## SDLC Workflow Status

**State**: Active / Inactive
**Started**: {timestamp}
**Coordination Mode**: {solo | subagents | agent-teams}

### Progress
- Total Beads: X
- Completed: Y
- In Progress: Z
- Blocked: W

### Active Worktrees
- trees/beads-xxx (feature/beads-xxx)

### Environment
- Agent Teams: Available / Not Available
- Beads CLI: Available / Not Available
- Worktrees: Available / Not Available

### Next Steps
- {What needs to happen next}
```
