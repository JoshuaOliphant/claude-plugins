---
name: sdlc-cancel
description: Cancel an active SDLC workflow and clean up resources
allowed-tools:
  - Bash
  - Read
---

# Cancel SDLC Workflow

Safely cancel an active SDLC workflow and clean up resources.

## Cancellation Process

### 1. Confirm Active Workflow

```bash
if [ ! -d ".sdlc" ]; then
    echo "No active SDLC workflow to cancel"
    exit 0
fi

echo "Active workflow found"
cat .sdlc/description 2>/dev/null
cat .sdlc/mode 2>/dev/null
```

### 2. List Active Resources

```bash
echo "=== Active Worktrees ==="
git worktree list | grep trees/

echo ""
echo "=== Open Beads ==="
bd list --status=open | head -20

echo ""
echo "=== Coordination Mode ==="
cat .sdlc/mode 2>/dev/null || echo "unknown"
```

### 3. Clean Up Worktrees

```bash
# Remove all SDLC worktrees
for worktree in $(git worktree list --porcelain | grep "worktree.*trees/" | cut -d' ' -f2); do
    echo "Removing worktree: $worktree"
    git worktree remove "$worktree" --force 2>/dev/null || true
done

# Prune stale references
git worktree prune
```

### 4. Clean Up Branches

```bash
# Delete task branches that were created
for branch in $(git branch | grep "feature/.*beads-"); do
    branch=$(echo "$branch" | sed 's/^[* ]*//')
    echo "Deleting branch: $branch"
    git branch -D "$branch" 2>/dev/null || true
done
```

### 5. Remove SDLC Marker

```bash
rm -rf .sdlc
echo "SDLC workflow cancelled"
```

### 6. Beads Cleanup (Optional)

The Beads themselves are NOT automatically deleted. You may want to:

```bash
# View what was created
bd list --status=open

# Manually close abandoned Beads
# bd close <bead-id> --reason="Cancelled"
```

## Post-Cancellation

After cancellation:
- Worktrees are removed
- Task branches are deleted
- SDLC marker is removed
- Beads remain open (manual cleanup if needed)

The repository is returned to a clean state.
