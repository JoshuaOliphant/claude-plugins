---
title: "Modernizing Claude Code plugins for v2.1+ native features"
date: 2026-03-16
project: claude-plugins
problem_type: patterns
component: claude-code-plugins
severity: medium
solution_summary: "Replace manual orchestration patterns with declarative frontmatter — native worktree isolation, task management, agent memory, and permission modes"
symptoms:
  - "Plugin agents manually creating/managing git worktrees with shell commands"
  - "TodoWrite used for task tracking without dependency support"
  - "Only builder agent has permissionMode: none, others prompt for permissions"
  - "Architect agent loses codebase knowledge between sessions"
  - "Agent teams feature gate checks stale CLAUDE_CODE_EXPERIMENTAL env var"
root_cause: "Plugin was built against Claude Code v1.0 capabilities; v2.0-2.1 shipped native worktree isolation, task management with dependencies, agent memory, and matured agent teams"
resolution_type: refactor
tags:
  - claude-code-plugins
  - agent-frontmatter
  - worktree-isolation
  - task-management
  - declarative-config
environment: "Claude Code v2.1.49+"
related_solutions:
  - "workflow/parallel-worktree-builders-claude-plugins-20260317.md"
  - "principles/dogfood-plugin-on-own-codebase-20260317.md"
---

## Problem

The autonomous-sdlc plugin (v0.6.0) was scripting behaviors that Claude Code now handles natively. The worktree-manager reference document was 199 lines of manual `git worktree add/remove/prune` instructions. Task tracking used `TodoWrite` which lacks dependency support. Only the builder agent had `permissionMode: "none"`, causing permission prompts during autonomous workflows.

## Investigation

Cross-referenced the full release notes (v0.2.21 through v2.1.76) against every agent definition, command, skill, and hook in the plugin. Identified 15 relevant new features, prioritized by impact.

### Key Release Note → Plugin Impact Mapping

| Release | Feature | Plugin Impact |
|---------|---------|---------------|
| v2.1.49 | `isolation: "worktree"` on Task tool | Replaces entire worktree-manager lifecycle |
| v2.1.16 | TaskCreate/TaskUpdate with dependencies | Replaces TodoWrite for task tracking |
| v2.1.33 | `memory` frontmatter for agents | Architect can learn across sessions |
| v2.0.43 | `permissionMode` in agent frontmatter | All autonomous agents should use it |
| v2.1.32+ | Agent teams matured (many fixes) | Feature gate docs were stale |
| v2.1.72 | `model` parameter restored on Task tool | Per-invocation model overrides possible |
| v2.1.0 | Hooks in skill/command frontmatter | Already adopted (builder PostToolUse) |

## Solution

### 1. Native Worktree Isolation

**Before** (manual lifecycle):
```bash
git worktree add ../trees/{bead-id} -b feature/{name}/{bead-id}
cd ../trees/{bead-id}
# ... work ...
git worktree remove ../trees/{bead-id}
git worktree prune
rm -rf ../trees/
```

**After** (declarative):
```python
Task(
    subagent_type="autonomous-sdlc:builder",
    isolation="worktree",  # Automatic creation, isolation, cleanup
    run_in_background=True
)
```

This eliminated ~80% of the worktree-manager.md content.

### 2. TaskCreate Replaces TodoWrite

**Before**: `TodoWrite([{"content": "...", "status": "pending"}])` — flat list, no dependencies.

**After**: `TaskCreate(description="...", status="in_progress")` + `TaskUpdate(taskId=id, status="completed")` — proper dependency tracking built in.

Changed in: sdlc.md command (allowed-tools + progress tracking + decompose phase), architect.md (tools), integrator.md (tools).

### 3. Agent Memory

Added `memory: project` to architect agent frontmatter. This lets the architect accumulate knowledge about codebase patterns, architecture decisions, and conventions across sessions — the agent most likely to benefit since it does deep codebase exploration.

### 4. Permission Mode on All Agents

Added `permissionMode: "none"` to all 6 agents (architect, validator, integrator, documenter, pr-creator — builder already had it). Without this, autonomous workflows are interrupted by permission prompts.

### 5. Agent Teams Documentation

Updated feature gate from checking a stale env var pattern to documenting the research preview status, `name` parameter for addressable teammates, `TeammateIdle`/`TaskCompleted` hooks, and model inheritance behavior.

## Key Principle

**Declarative over imperative**: As Claude Code's plugin infrastructure matures, the winning pattern shifts from "tell the agent how to do it" to "declare what the agent needs." Each frontmatter field (`isolation`, `memory`, `permissionMode`, `skills`, `hooks`) replaces dozens of lines of procedural instructions.

## Evaluation Methodology

When evaluating a plugin against new Claude Code releases:

1. **Read the full release notes** — don't skim; features interact
2. **Read every file in the plugin** — agents, commands, skills, hooks
3. **Map features to files** — which release note changes which file?
4. **Prioritize by blast radius** — features affecting multiple files > single-file improvements
5. **Check for removed patterns** — things the plugin scripts that Claude Code now handles natively are the highest-value changes

## Verification

```bash
# Zero TodoWrite references remaining
grep -r "TodoWrite" plugins/autonomous-sdlc/  # Should return nothing

# All agents have permissionMode
grep -r "permissionMode" plugins/autonomous-sdlc/agents/  # Should show 6 files

# Native worktree isolation adopted
grep -r 'isolation.*worktree' plugins/autonomous-sdlc/  # Should show multiple references
```
