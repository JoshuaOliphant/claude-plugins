# Autonomous SDLC Plugin

Verification-driven software development lifecycle for Claude Code. This plugin enables autonomous feature development from initial requirements through PR creation.

## Key Features

- **Feature Branches**: One branch per feature, task branches underneath
- **Plan-First Architecture**: Comprehensive plan documents before implementation
- **Wave-Based Integration**: Merge after each dependency wave
- **Parallel Worktrees**: Isolated development environments
- **Builder/Validator Pairs**: Separate implementation and verification
- **Automatic Validation Hooks**: Ruff + type checking on every edit
- **Documentation Sync**: Automatic doc updates after implementation
- **PR Generation**: Rich PR descriptions from plan documents

## Quick Start

```bash
# Start an SDLC workflow
/autonomous-sdlc:sdlc "Add user authentication with JWT tokens"

# Check status
/autonomous-sdlc:sdlc-status

# Cancel workflow (if needed)
/autonomous-sdlc:sdlc-cancel
```

## Complete Workflow

```
/sdlc "Add user authentication"
    ↓
┌─────────────────────────────────────────────────────────────┐
│ ARCHITECT (Opus)                                             │
│   1. Explore codebase                                        │
│   2. Create feature branch: feature/user-auth                │
│   3. Create specs/user-auth-plan.md                          │
│   4. Create Beads with dependencies                          │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ WORKTREE MANAGER - Wave Loop                                 │
│                                                              │
│   WAVE 1 (tasks with no deps):                               │
│   ├─ Builders in parallel → Validators → INTEGRATE           │
│          ↓                                                   │
│   WAVE 2 (depends on Wave 1):                                │
│   ├─ Builders (see Wave 1 code!) → Validators → INTEGRATE    │
│          ↓                                                   │
│   ... repeat until all Beads closed ...                      │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ DOCUMENTER (Haiku)                                           │
│   Update README, docstrings, ABOUTME comments                │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ PR-CREATOR (Sonnet)                                          │
│   Create PR/MR with rich description from plan               │
└─────────────────────────────────────────────────────────────┘
    ↓
Done! PR ready for human review
```

## Agents

| Agent | Model | Purpose | Key Feature |
|-------|-------|---------|-------------|
| **Architect** | Opus | Creates feature branch + plan + Beads | Plan-first |
| **Worktree Manager** | Sonnet | Orchestrates waves | Inter-wave integration |
| **Builder** | Sonnet | Implements one task | PostToolUse hooks |
| **Validator** | Sonnet | Verifies implementation | Read-only |
| **Integrator** | Sonnet | Merges task branches | Conflict resolution |
| **Documenter** | Haiku | Updates docs | Fast, efficient |
| **PR-Creator** | Sonnet | Creates PR/MR | GitHub + GitLab |
| **Implementer** | Sonnet | Legacy TDD agent | Use Builder instead |

## Commands

| Command | Description |
|---------|-------------|
| `/autonomous-sdlc:sdlc <description>` | Start autonomous workflow |
| `/autonomous-sdlc:sdlc-status` | Check workflow progress |
| `/autonomous-sdlc:sdlc-cancel` | Cancel active workflow |
| `/autonomous-sdlc:prime` | Orient to codebase |

## Skills

| Skill | Purpose |
|-------|---------|
| `beads-workflow` | Beads CLI commands |
| `verification-stack` | Full verification pipeline |
| `tdd-workflow` | Test-driven development |

## Branch Strategy

```
main
 └── feature/user-auth                    ← Feature branch
      ├── feature/user-auth/beads-abc     ← Task branch (Wave 1)
      ├── feature/user-auth/beads-def     ← Task branch (Wave 1)
      └── feature/user-auth/beads-ghi     ← Task branch (Wave 2)
```

- **Architect** creates the feature branch
- **Worktree Manager** creates task branches FROM the feature branch
- **Integrator** merges task branches INTO the feature branch after each wave
- **PR-Creator** opens a PR from feature branch to main

## Wave-Based Integration

**Why integrate between waves?**

Wave 2 tasks often depend on Wave 1 code. Without integration:
- Wave 1 Builder creates `User` model
- Wave 2 Builder needs `User` but doesn't see it!

With integration:
- Wave 1: Create `User` model → merge into feature branch
- Wave 2: Branch from feature branch → sees `User` model ✅

## Validation Hooks

Builders have PostToolUse hooks that run automatically:

| Hook | Purpose |
|------|---------|
| `ruff_validator.py` | Lint Python files |
| `type_validator.py` | Type check Python files |

Issues are reported immediately so builders fix them inline.

## Prerequisites

- Claude Code v2.1.0+
- Git (for worktrees)
- Beads CLI (`bd` command)
- `gh` CLI (GitHub) or `glab` CLI (GitLab)
- `uv` for Python package management

## Plan Documents

Every workflow creates `specs/{feature}-plan.md` containing:

- Task description and objectives
- Solution approach
- Team orchestration (builders, validators)
- Step-by-step tasks with dependencies
- Acceptance criteria
- Validation commands

## Verification Stack

```
Tests (pytest) → Lint (ruff) → Types (mypy) → Build
```

If any gate fails, the agent fixes it before proceeding.

## Example Output

```markdown
## SDLC Workflow Complete

**Feature**: Add user authentication
**Feature Branch**: feature/user-auth
**Plan**: specs/user-auth-plan.md

### Execution Summary
| Phase | Status |
|-------|--------|
| Architect | ✅ Complete |
| Wave 1 (3 tasks) | ✅ Integrated |
| Wave 2 (2 tasks) | ✅ Integrated |
| Documenter | ✅ Complete |
| PR-Creator | ✅ Complete |

### Pull Request
**URL**: https://github.com/owner/repo/pull/123
**Status**: Open (ready for review)
```

## Version History

### v0.3.0 (Current)
- Added feature branch strategy
- Added wave-based integration (inter-wave merging)
- Added Integrator agent for branch merging
- Added PR-Creator agent for GitHub/GitLab PRs
- Task branches now created from feature branch

### v0.2.0
- Added Builder/Validator agent pairs
- Added PostToolUse validation hooks
- Added Documenter agent
- Removed Reviewer (PR review in CI/CD)

### v0.1.0
- Initial release with Architect, Implementer, Worktree Manager, Reviewer
