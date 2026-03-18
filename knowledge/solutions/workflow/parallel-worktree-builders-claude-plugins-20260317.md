---
title: "Parallel builder dispatch with worktree isolation — behaviors and integration patterns"
date: 2026-03-17
project: claude-plugins
problem_type: workflow
component: claude-code-plugins
severity: medium
solution_summary: "When dispatching 5 parallel builders with isolation: worktree, 4 of 5 committed directly to main while 1 used its worktree branch — integration requires checking both paths"
symptoms:
  - "Worktree branches not created for all builders despite isolation: worktree"
  - "Some builders commit to main directly even when worktree isolation requested"
  - "Integration step finds uncommitted changes in main working directory from worktree builder"
root_cause: "Claude Code's worktree isolation behavior varies by task complexity — simpler tasks (frontmatter edits) may resolve without creating a separate branch, while complex tasks (new files, multiple file changes) use the full worktree lifecycle"
resolution_type: workaround
tags:
  - parallel-builders
  - worktree-isolation
  - agent-orchestration
  - integration
environment: "Claude Code v2.1.49+"
related_solutions:
  - "patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md"
---

## Problem

Dispatched 5 builders in parallel with `isolation: "worktree"` on the Task tool. Expected all 5 to work in isolated worktree branches. Instead, 4 committed directly to main and only the 5th (the most complex task — creating new files and modifying multiple files) used its worktree branch.

## Investigation

After all builders completed:

```bash
git log --oneline -10  # Showed 4 builder commits on main
git worktree list      # Showed 1 active worktree (builder-6xy)
git branch | grep worktree  # Only worktree-agent-ac10983c existed
```

The worktree builder also wrote some files to the main working directory, causing `git merge` to fail with "local changes would be overwritten."

## Solution

### Integration Pattern for Mixed Worktree/Direct Commits

After parallel builders complete, follow this integration sequence:

1. **Check main branch** — `git log` to see which builders committed directly
2. **Check worktree branches** — `git branch | grep worktree` for any remaining
3. **Check uncommitted changes** — `git status` on main for worktree builder spillover
4. **For worktree branches**: Either merge or commit the spillover changes directly (they're the same content)
5. **Clean up**: `git worktree remove`, `git branch -D`, `git worktree prune`

### What Actually Happened

```bash
# 4 builders committed directly to main — no integration needed
# 1 builder (wave transitions) had changes in BOTH worktree and main working dir
# Solution: committed the main working dir changes directly, deleted the worktree branch
cd /path/to/repo
git add plugins/autonomous-sdlc/hooks/hooks.json ...
git commit -m "feat: wave transition hooks"
git worktree remove .claude/worktrees/agent-ac10983c
git branch -D worktree-agent-ac10983c
git worktree prune
```

## Key Observations

1. **Task complexity determines isolation behavior**: Simple frontmatter edits (adding `context: fork`, updating tool lists) don't seem to trigger full worktree isolation. Complex tasks (creating scripts, modifying hooks.json + multiple .md files) do.

2. **Spillover is possible**: A worktree builder may write to both its worktree AND the main working directory. Check both after completion.

3. **Integration is still needed**: Even with native worktree isolation, the lead orchestrator must handle the merge/integration step. The automation handles lifecycle (creation, cleanup) but not merge strategy.

4. **Wall clock efficiency**: 5 parallel builders completed in ~6.5 minutes total. The longest (wave transitions) took ~6.5 min, the shortest (context: fork) took ~1 min. Parallelism saved significant time vs sequential.

## Verification

```bash
# After integration, verify all changes are on main
git log --oneline HEAD~8..HEAD  # Should show all builder commits
git worktree list               # Should show only main
git branch | grep worktree      # Should return nothing
bd ready                        # Should show no open issues
```
