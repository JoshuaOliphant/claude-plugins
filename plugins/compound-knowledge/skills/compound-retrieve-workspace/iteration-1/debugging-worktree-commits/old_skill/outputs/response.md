## Knowledge Retrieval Results

La Boeuf, good news -- we have documented this exact problem. Here is what the knowledge base turned up.

---

## Search Context

- **Task**: Builder agents committing directly to main instead of using worktree branches in autonomous-sdlc plugin
- **Keywords**: autonomous-sdlc, worktree, builder, commit, main, branch, isolation, agent
- **Solutions Path**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/` (primary), `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/` (cross-project)
- **Registry**: 2 registered KBs (second-brain, claude-plugins)
- **Files Scanned**: 23 candidates across both KBs

## Critical Patterns

No critical patterns from `critical-patterns.md` apply to this specific issue (the critical patterns cover Kubernetes secrets, Docker security scans, AWS cross-account access, Fastlane, and iOS screenshots).

## Relevant Solutions

### 1. Parallel Builder Dispatch with Worktree Isolation -- Behaviors and Integration Patterns

- **File**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/workflow/parallel-worktree-builders-claude-plugins-20260317.md`
- **Source KB**: claude-plugins (cross-project)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: Directly documents the exact symptom -- 4 of 5 builders committed to main despite `isolation: worktree` being set.
- **Key Insight**: Task complexity determines isolation behavior. Simple tasks (frontmatter edits, single-file changes) resolve without creating a worktree branch, while complex tasks (new files, multi-file changes) use the full worktree lifecycle. This is a Claude Code runtime behavior, not a plugin bug.
- **Severity**: medium

**Root Cause**: Claude Code's worktree isolation varies by task complexity. Simpler tasks may skip worktree creation entirely. Additionally, a worktree builder can "spill over" and write changes to both its worktree AND the main working directory.

**Documented Workaround** -- after parallel builders complete, follow this integration sequence:

1. Check main branch with `git log` to see which builders committed directly
2. Check worktree branches with `git branch | grep worktree` for any remaining
3. Check uncommitted changes with `git status` on main for worktree builder spillover
4. For worktree branches: either merge or commit the spillover changes directly
5. Clean up: `git worktree remove`, `git branch -D`, `git worktree prune`

### 2. Modernizing Claude Code Plugins for v2.1+ Native Features

- **File**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins (cross-project)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: Documents the migration from manual worktree shell commands to declarative `isolation: "worktree"` on the Task tool, which is the correct pattern but exhibits the variable behavior described above.
- **Key Insight**: The v2.1.49 `isolation: "worktree"` feature replaces the entire manual worktree lifecycle, but the integration/merge step still needs manual handling by the orchestrator.
- **Severity**: medium

## Relevant Principles

### 1. File-Location Isolation for Parallel Agents

- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/file-location-isolation-for-parallel-agents-second-brain-20260301.md`
- **Source KB**: second-brain (primary)
- **Statement**: "When decomposing work across parallel agents, assign tasks such that each agent writes to a disjoint set of file paths -- no shared files, no merge conflicts, no coordination overhead."
- **Confidence**: high
- **Relevance**: Even with worktree isolation, if multiple builders touch the same files, spillover conflicts can occur. Assigning disjoint file paths per builder is a complementary safeguard.

### 2. Hooks Beat Skills for Autonomous Agent Behavior

- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/hooks-beat-skills-for-autonomous-agent-behavior-second-brain-20260314.md`
- **Source KB**: second-brain (primary)
- **Statement**: "When an agent behavior must happen reliably, use system-level hooks instead of skills or MCP tools."
- **Confidence**: high
- **Relevance**: If you need to enforce worktree branch usage for ALL builders regardless of task complexity, a PreToolUse or PostToolUse hook that checks/enforces branch state would be more reliable than relying on the `isolation` parameter alone.

## Recommendations

1. **This is a known Claude Code behavior, not a bug in your plugin.** The `isolation: "worktree"` parameter does not guarantee all builders will create worktree branches. Simple tasks may commit directly to main. Your integrator agent should account for both code paths.

2. **Add a post-builder integration check** to your orchestrator/integrator that runs `git log`, `git branch | grep worktree`, and `git status` after all builders complete, following the documented sequence above.

3. **Consider a hook-based enforcement** if you strictly need all builders on separate branches. A PreToolUse hook on `Bash` that validates `git rev-parse --abbrev-ref HEAD` could warn or block direct-to-main commits during builder execution.

4. **Assign disjoint file paths** when dispatching parallel builders. This reduces the impact of the variable worktree behavior since builders writing to different files won't conflict even if some commit to main directly.
