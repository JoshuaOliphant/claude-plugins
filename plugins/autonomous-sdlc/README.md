# Autonomous SDLC Plugin

Verification-driven software development lifecycle for Claude Code. This plugin enables autonomous feature development through:

- **Parallel Worktrees**: Each feature is implemented in an isolated git worktree
- **Async Subagents**: Multiple features can be implemented concurrently
- **Beads Integration**: Work tracking via `bd` commands with dependency management
- **Verification-Driven**: Tests, linting, and type checking as automated gates (not manual approval)
- **TDD Workflow**: Test-first development with red-green-refactor cycle

## Quick Start

```bash
# Start an SDLC workflow
/sdlc "Add user authentication with JWT tokens"

# Check status
/sdlc-status

# Cancel workflow (if needed)
/sdlc-cancel
```

## How It Works

1. **Architect Agent** (Opus): Analyzes requirements, creates Beads with dependencies
2. **Worktree Manager**: Creates isolated worktrees, spawns async implementer agents
3. **Implementer Agents** (Sonnet): TDD implementation in parallel worktrees
4. **Reviewer Agent**: Final code review before merge

## Components

### Commands
- `/sdlc <description>` - Start autonomous workflow
- `/sdlc-status` - Check workflow progress
- `/sdlc-cancel` - Cancel active workflow

### Agents
- `architect` - Opus model, creates feature breakdown with Beads
- `implementer` - Sonnet model, TDD in isolated worktree
- `worktree-manager` - Orchestrates parallel worktrees
- `reviewer` - Final code review

### Skills
- `beads-workflow` - Beads commands for SDLC
- `verification-stack` - Full verification pipeline
- `tdd-workflow` - Test-driven development process

## Prerequisites

- Claude Code v2.1.0+
- Git (for worktrees)
- Beads CLI (`bd` command)
- Project with test infrastructure

## Verification Stack

The plugin uses verification as automation gates:

```
Tests (pytest/jest/etc) → Lint (ruff/eslint) → Types (mypy/tsc) → Build
```

If any gate fails, the agent fixes it before proceeding. No manual approval required.
