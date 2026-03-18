La Boeuf, good news -- we have documented this exact issue. Here is what the knowledge base turned up.

## Search Context

- **Task**: Builder agents committing directly to main instead of using worktree branches in autonomous-sdlc plugin
- **Keywords**: autonomous-sdlc, worktree, builder, commit, main, branch, isolation
- **Solutions Paths**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/` (primary), `~/Dropbox/python_workspace/second_brain/knowledge/solutions/` (cross-project)
- **Registry**: 2 registered KBs
- **Files Scanned**: 12 candidates after grep filtering

## Critical Patterns

None of the 6 critical patterns in `critical-patterns.md` apply to this issue (they cover Kubernetes secrets, Docker CVEs, AWS cross-account access, Fastlane pricing, iOS screenshots, and TestFlight build numbers).

## Relevant Solutions

### 1. Parallel Builder Dispatch with Worktree Isolation (DIRECT MATCH)
- **File**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/workflow/parallel-worktree-builders-claude-plugins-20260317.md`
- **Source KB**: claude-plugins (primary)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: This documents the exact behavior you are seeing -- builders committing to main instead of using worktree branches.
- **Key Insight**: Task complexity determines isolation behavior. When 5 builders were dispatched with `isolation: "worktree"`, 4 of 5 committed directly to main. Only the most complex task (creating new files, modifying multiple files) actually used its worktree branch. Simpler tasks (frontmatter edits, single-file changes) resolved without creating a separate branch.
- **Severity**: medium

**Root cause from the doc**: "Claude Code's worktree isolation behavior varies by task complexity -- simpler tasks (frontmatter edits) may resolve without creating a separate branch, while complex tasks (creating scripts, modifying hooks.json + multiple .md files) do."

**The documented workaround (integration pattern)**:
1. After builders complete, check `git log` to see which committed directly to main
2. Check `git branch | grep worktree` for any remaining worktree branches
3. Check `git status` on main for worktree builder spillover (a builder may write to BOTH its worktree AND the main working directory)
4. For worktree branches, merge or commit the spillover changes directly
5. Clean up: `git worktree remove`, `git branch -D`, `git worktree prune`

### 2. Modernizing Claude Code Plugins for v2.1+ Native Features
- **File**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins (primary)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: Documents the shift from manual worktree management to declarative `isolation: "worktree"` on the Task tool -- the feature whose behavior is causing this issue.
- **Key Insight**: The `isolation: "worktree"` parameter on the Task tool replaced ~80% of the old worktree-manager.md content, but the native isolation behavior is not as deterministic as the manual approach was. The old approach always created a worktree; the native approach may skip it for simple tasks.
- **Severity**: medium

### 3. Prompt Objects Replace Procedural Agent Instructions
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/prompt-objects-replace-procedural-agents-claude-plugins-20260214.md`
- **Source KB**: second-brain (cross-project)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: Documents the earlier v0.3.0 to v0.4.0 refactor where the worktree-manager middleman was absorbed into the lead orchestrator. The symptom "Builders assumed worktree paths even when running in shared directories" is related.
- **Key Insight**: The fix was to make agents context-aware (detect whether they are in a worktree or shared directory) rather than assuming a fixed path structure. Agent prompt objects include "Context Awareness: You may be in a worktree OR shared directory."
- **Severity**: medium

## Relevant Principles

### 1. File-Location Isolation for Parallel Agents
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/file-location-isolation-for-parallel-agents-second-brain-20260301.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: "When decomposing work across parallel agents, assign tasks such that each agent writes to a disjoint set of file paths."
- **Confidence**: high
- **Relevance**: If builders are committing to main, file-location isolation becomes even more important -- without worktree branches separating their work, parallel commits to main can conflict.

### 2. Unique Naming for Parallel Resource Creation
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/unique-naming-parallel-resources-adw-cli-20260122.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: Use timestamp or UUID suffixes for resources created by parallel workflows.
- **Confidence**: high (from real failures)
- **Relevance**: If worktree branches ARE created, naming collisions can occur between parallel builders. Use timestamp-based naming to avoid this.

## Recommendations

1. **This is a known Claude Code behavior, not a bug in your plugin.** The `isolation: "worktree"` parameter on the Task tool does not guarantee worktree creation for every task. Simple tasks may commit directly to main. Your integration step needs to handle both paths (worktree branch merge AND direct main commits).

2. **Add a post-builder integration check to your workflow.** After all builders complete, the lead should run `git log`, `git worktree list`, and `git status` to determine what happened, then handle accordingly. The documented pattern in solution #1 above gives the exact sequence.

3. **If you need guaranteed branch isolation**, consider whether the old manual worktree approach (from the pre-v2.1 plugin) is preferable for your use case -- the declarative approach trades determinism for convenience.

4. **Watch for spillover.** A worktree builder can write to both its worktree AND the main working directory. Always check `git status` on main after worktree builders complete.
