# Knowledge Retrieval: Builder Agents Committing to Main Instead of Worktree Branches

## Search Summary

- **Knowledge bases searched**: claude-plugins local KB (3 solutions), second-brain cross-project KB (379 solutions)
- **Search strategy**: Parallel grep on frontmatter fields (project, component, tags, symptoms) + full-text search for "worktree", "commit main", "branch builder"
- **Candidates evaluated**: 16 worktree-related files, 7 claude-plugins project files, 18 agent-related files
- **Critical patterns checked**: `critical-patterns.md` reviewed — no patterns apply to this task
- **Top results read in full**: 3

---

## Direct Hit: This Exact Problem Is Documented

**File**: `knowledge/solutions/workflow/parallel-worktree-builders-claude-plugins-20260317.md`

La Boeuf, you've hit this before — just yesterday, in fact. Here's what happened and what fixed it:

### Root Cause

Claude Code's worktree isolation behavior varies by **task complexity**. When you dispatch parallel builders with `isolation: "worktree"`:

- **Simple tasks** (frontmatter edits, single-file changes) often resolve without creating a separate branch — they commit directly to main
- **Complex tasks** (creating new files, modifying multiple files) use the full worktree lifecycle with an isolated branch

This means in a batch of 5 builders, you'll typically see 4 commit to main and only 1 actually use its worktree branch. This is a characteristic of Claude Code v2.1.49+, not a bug in your plugin.

### The Fix: Integration Pattern for Mixed Worktree/Direct Commits

After parallel builders complete, run this integration sequence:

1. **Check main branch** — `git log` to see which builders committed directly
2. **Check worktree branches** — `git branch | grep worktree` for any remaining
3. **Check uncommitted changes** — `git status` on main for worktree builder spillover (a worktree builder may write to BOTH its worktree AND the main working directory)
4. **For worktree branches**: Either merge, or if spillover exists, commit the main working dir changes directly (they're the same content)
5. **Clean up**: `git worktree remove`, `git branch -D`, `git worktree prune`

### Concrete Example from Last Time

```bash
# 4 builders committed directly to main — no integration needed
# 1 builder (wave transitions) had changes in BOTH worktree and main working dir
# Solution: committed the main working dir changes directly, deleted the worktree branch
git add plugins/autonomous-sdlc/hooks/hooks.json ...
git commit -m "feat: wave transition hooks"
git worktree remove .claude/worktrees/agent-ac10983c
git branch -D worktree-agent-ac10983c
git worktree prune
```

---

## Supporting Principles

### File-Location Isolation for Parallel Agents
**File**: `second_brain/knowledge/solutions/principles/file-location-isolation-for-parallel-agents-second-brain-20260301.md`

An alternative approach to worktree isolation: assign tasks so each agent writes to a **disjoint set of file paths**. If no two agents touch the same file, you don't need worktree isolation at all — they can all work on main without conflicts. This is more reliable than depending on worktree behavior.

### Unique Naming for Parallel Resources
**File**: `second_brain/knowledge/solutions/patterns/unique-naming-parallel-resources-adw-cli-20260122.md`

If you do use worktree branches, ensure branch names include a timestamp or UUID to prevent collisions. This is high-severity and has caused real failures in the adw-cli project.

---

## Recommendations

1. **For immediate relief**: Use the integration pattern above after your builder wave completes. Expect most builders to commit directly to main — that's normal behavior.

2. **For a more robust approach**: Consider switching from `isolation: "worktree"` to **file-location isolation** — decompose tasks so each builder writes to different directories. This eliminates the mixed-commit problem entirely.

3. **Knowledge gap noted**: There's no solution documenting how to *force* worktree isolation for all builders regardless of task complexity. If you discover a way (e.g., a Task tool parameter or minimum complexity threshold), that would be worth capturing with `/compound-knowledge:capture`.
