Hey La Boeuf, I searched the knowledge base for past solutions related to your worktree/commit-to-main issue. Good news -- we have documented this exact problem.

## Search Context

- **Task**: Builder agents committing directly to main instead of using worktree branches in autonomous-sdlc plugin
- **Keywords**: autonomous-sdlc, worktree, builder, commit, main, branch, isolation
- **Solutions Path**: `knowledge/solutions/`
- **Registry**: 2 registered KBs (claude-plugins, second-brain)
- **Files Scanned**: 3 candidates from content search (frontmatter fields did not use standardized keywords)

## Critical Patterns

No `critical-patterns.md` file exists. Skipped.

## Relevant Principles

### 1. Dogfood Your Plugin on Its Own Codebase
- **File**: `knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`
- **Source KB**: claude-plugins (primary)
- **Statement**: "The best test of an orchestration plugin is to use it to orchestrate work on its own codebase. Dogfooding reveals integration gaps, incorrect assumptions, and UX issues that synthetic evals miss."
- **Confidence**: high
- **Relevance**: This exact worktree behavior was discovered through dogfooding -- using the autonomous-sdlc plugin to modify itself.

## Relevant Solutions

### 1. Parallel Builder Dispatch with Worktree Isolation (Score: 9)
- **File**: `knowledge/solutions/workflow/parallel-worktree-builders-claude-plugins-20260317.md`
- **Source KB**: claude-plugins (primary)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: Documents the exact symptom you are describing -- builders committing to main instead of using worktree branches.
- **Key Insight**: This is **expected behavior**, not a bug. Claude Code's worktree isolation behavior varies by task complexity. Simple tasks (frontmatter edits, single-file changes) may resolve without creating a separate branch, while complex tasks (creating new files, modifying multiple files) use the full worktree lifecycle. When we dispatched 5 parallel builders with `isolation: "worktree"`, 4 of 5 committed directly to main and only the most complex task used its worktree branch.
- **Severity**: medium

### 2. Modernizing Claude Code Plugins for v2.1+ Native Features (Score: 7)
- **File**: `knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins (primary)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: Documents the migration from manual worktree management to declarative `isolation: "worktree"` on the Task tool, which is the mechanism that exhibits this behavior.
- **Key Insight**: The shift to `isolation: "worktree"` replaced ~80% of the manual worktree-manager.md content, but the native isolation does not guarantee separate branches for all tasks. The integration step still requires the lead orchestrator to handle mixed commit paths.
- **Severity**: medium

## Recommendations

1. **This is not a bug -- it is documented behavior.** Claude Code's native worktree isolation decides at runtime whether a task needs a separate branch. Simple tasks skip the worktree entirely and commit directly to main. You do not need to "fix" this.

2. **Add a post-builder integration check.** After parallel builders complete, the orchestrating agent should:
   - Run `git log` to see which builders committed directly to main
   - Run `git branch | grep worktree` to find any remaining worktree branches
   - Run `git status` to check for uncommitted spillover from worktree builders
   - Merge or commit remaining changes, then clean up worktrees

3. **Watch for spillover.** A worktree builder may write files to both its worktree AND the main working directory. After completion, check `git status` on main for unexpected uncommitted changes.

4. **If you need guaranteed branch isolation**, the documented workaround is to handle it manually rather than relying on the declarative `isolation: "worktree"` -- but this sacrifices the simplicity gains from the v2.1+ migration.
