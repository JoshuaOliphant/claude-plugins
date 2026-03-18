# Knowledge Retrieval: Builder Agents Committing Directly to Main

La Boeuf, good news -- we have documented this exact problem. Here is what the knowledge base says.

---

## KNOWN ISSUE: Worktree Isolation Varies by Task Complexity

**Source**: `knowledge/solutions/workflow/parallel-worktree-builders-claude-plugins-20260317.md`
**Severity**: Medium
**Date documented**: 2026-03-17

### What Happens

When you dispatch parallel builders with `isolation: "worktree"`, **not all of them actually use worktree branches**. In a documented case, 4 out of 5 builders committed directly to main while only the 5th (the most complex task) used its worktree branch.

### Root Cause

Claude Code's worktree isolation behavior varies by task complexity:

- **Simple tasks** (frontmatter edits, single-file changes) may resolve without creating a separate branch -- the agent completes the work directly on main.
- **Complex tasks** (creating new files, modifying multiple files across directories) trigger the full worktree lifecycle with branch creation and isolation.

This is a behavior of Claude Code itself (v2.1.49+), not a bug in the plugin.

### The Fix: Integration Pattern for Mixed Worktree/Direct Commits

After parallel builders complete, follow this integration sequence:

1. **Check main branch** -- `git log` to see which builders committed directly
2. **Check worktree branches** -- `git branch | grep worktree` for any remaining
3. **Check uncommitted changes** -- `git status` on main for worktree builder spillover
4. **For worktree branches**: Either merge or commit the spillover changes directly (they are the same content)
5. **Clean up**: `git worktree remove`, `git branch -D`, `git worktree prune`

### Watch Out For: Spillover

A worktree builder can write files to **both** its worktree AND the main working directory. This causes `git merge` to fail with "local changes would be overwritten." The workaround is to commit the main working directory changes directly (they are identical to the worktree branch content), then delete the worktree branch.

---

## Related Context

### Declarative Worktree Isolation (the "right" approach)

**Source**: `knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`

The plugin was modernized to use declarative `isolation: "worktree"` on the Task tool instead of manual `git worktree add/remove` scripting. This is the correct approach -- the issue above is about the *runtime behavior* of that declarative feature, not about how you invoke it.

```python
Task(
    subagent_type="autonomous-sdlc:builder",
    isolation="worktree",
    run_in_background=True
)
```

### Dogfooding Principle

**Source**: `knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`

This exact problem was discovered by dogfooding the autonomous-sdlc plugin on its own codebase. The principle holds: real usage reveals integration gaps that synthetic tests miss.

---

## Recommendations

1. **Your integrator agent should already handle this** -- update its integration step to expect mixed worktree/direct commits and follow the 5-step sequence above.
2. **Do not treat this as a bug to fix** -- it is a characteristic of Claude Code's worktree implementation. Design your workflow around it.
3. **If this keeps causing problems**, consider whether the tasks you are dispatching to builders are complex enough to warrant worktree isolation. For simple edits, `isolation: "worktree"` adds overhead without benefit since the agent commits to main anyway.

---

## Knowledge Gap

There is no solution documented for *forcing* worktree isolation regardless of task complexity. If you find a way (e.g., a Task tool parameter or agent instruction that guarantees branch creation), that would be worth capturing with `/compound-knowledge:capture`.
