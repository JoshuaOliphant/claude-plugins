# Knowledge Retrieval: Builder Agents Committing to Main Instead of Worktree Branches

La Boeuf, good news -- we have documented this exact problem. Here is what the knowledge base says.

---

## Direct Hit: Documented Solution

**File**: `knowledge/solutions/workflow/parallel-worktree-builders-claude-plugins-20260317.md`

This was encountered on 2026-03-17 when dogfooding the autonomous-sdlc plugin on its own codebase. Five builders were dispatched with `isolation: "worktree"`, but **4 of 5 committed directly to main** while only the 5th (the most complex task) actually used its worktree branch.

### Root Cause

**Task complexity determines isolation behavior.** Simple tasks (frontmatter edits, single-file changes) may resolve without creating a separate worktree branch, while complex tasks (creating new files, modifying multiple files across directories) trigger the full worktree lifecycle. This is a Claude Code runtime behavior, not a plugin bug.

### The Fix (Integration Pattern for Mixed Worktree/Direct Commits)

After parallel builders complete, follow this sequence:

1. **Check main branch** -- `git log` to see which builders committed directly
2. **Check worktree branches** -- `git branch | grep worktree` for any remaining
3. **Check uncommitted changes** -- `git status` on main for worktree builder spillover
4. **For worktree branches**: Merge or commit the spillover changes directly (they are the same content)
5. **Clean up**: `git worktree remove`, `git branch -D`, `git worktree prune`

### Critical Detail: Spillover

A worktree builder can write to **both** its worktree AND the main working directory. This causes `git merge` to fail with "local changes would be overwritten." The workaround is to commit the main working directory changes directly and then delete the worktree branch, since the content is identical.

---

## Related Knowledge

### Plugin Modernization Context
**File**: `knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`

The `isolation: "worktree"` feature was adopted as part of the v2.1+ modernization, replacing ~80% of the manual worktree-manager.md content. The declarative approach (`Task(isolation="worktree")`) replaced manual `git worktree add/remove/prune` scripting. This is the correct approach -- the variable isolation behavior is a known characteristic of the runtime, not a misconfiguration.

### File-Location Isolation Principle
**File (cross-project)**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/file-location-isolation-for-parallel-agents-second-brain-20260301.md`

When decomposing work across parallel agents, assign tasks so each agent writes to a **disjoint set of file paths**. This doesn't prevent the worktree/direct-commit variation, but it does prevent merge conflicts regardless of which path the runtime takes.

### Dogfooding Principle
**File**: `knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`

This exact bug was discovered through dogfooding -- using the autonomous-sdlc plugin to modify its own codebase. That experience validated that the integration step (checking both main and worktree branches after builders complete) is essential and cannot be automated away.

---

## Recommendations

1. **This is not a bug to fix** -- it is a known Claude Code runtime behavior. The integrator agent should always check both main and worktree branches after parallel builders complete.
2. **Update your integrator instructions** (if not already done) to include the 5-step integration pattern above.
3. **Consider file-location isolation** when decomposing tasks -- even if worktree isolation does not trigger, disjoint file paths prevent conflicts.
4. **Watch for spillover** -- always run `git status` on main after worktree builders finish.

---

*Knowledge gap noted*: There is no solution documenting whether newer Claude Code versions (post-v2.1.49) have changed this behavior. If you discover the threshold has changed, consider capturing that with `compound-capture`.
