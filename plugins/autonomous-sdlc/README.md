# Autonomous SDLC Plugin

Verification-driven software development lifecycle for Claude Code. This plugin enables autonomous feature development through:

- **Plan-First Architecture**: Comprehensive plan documents before implementation
- **Parallel Worktrees**: Each feature is implemented in an isolated git worktree
- **Builder/Validator Pairs**: Separate agents for implementation and verification
- **Automatic Validation Hooks**: Ruff + type checking runs after every file edit
- **Beads Integration**: Work tracking via `bd` commands with dependency management
- **Verification-Driven**: Tests, linting, and type checking as automated gates
- **TDD Workflow**: Test-first development with red-green-refactor cycle
- **Documentation Sync**: Automatic documentation updates after implementation

## Quick Start

```bash
# Start an SDLC workflow
/autonomous-sdlc:sdlc "Add user authentication with JWT tokens"

# Check status
/autonomous-sdlc:sdlc-status

# Cancel workflow (if needed)
/autonomous-sdlc:sdlc-cancel
```

## Workflow Architecture

```
/sdlc "description"
    ↓
┌─────────────────────────────────────────────────────────────┐
│ ARCHITECT (Opus)                                             │
│   1. Explore codebase                                        │
│   2. Create specs/{feature}-plan.md                          │
│   3. Create Beads from plan with dependencies                │
│   4. Report task graph                                       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ WORKTREE MANAGER (Sonnet)                                    │
│   1. bd ready → find unblocked tasks                         │
│   2. git worktree add for each ready Bead                    │
│   3. Spawn Builder agents in parallel                        │
│   4. After each Builder, spawn Validator                     │
│   5. Monitor, iterate until all Beads closed                 │
└─────────────────────────────────────────────────────────────┘
    ↓ (for each ready Bead)
┌─────────────────────────────────────────────────────────────┐
│ BUILDER (Sonnet) + VALIDATOR (Sonnet)                        │
│                                                              │
│   Builder:                                                   │
│   1. Implement task with TDD                                 │
│   2. PostToolUse hooks run Ruff + type check automatically   │
│   3. Commit changes                                          │
│                                                              │
│   Validator (read-only):                                     │
│   1. Verify acceptance criteria met                          │
│   2. Run verification stack                                  │
│   3. Report PASS/FAIL                                        │
│   4. If PASS → bd close {bead-id}                            │
└─────────────────────────────────────────────────────────────┘
    ↓ (all Beads closed)
┌─────────────────────────────────────────────────────────────┐
│ DOCUMENTER (Haiku)                                           │
│   1. Scan for undocumented new code                          │
│   2. Update README.md with new features                      │
│   3. Add/update docstrings                                   │
│   4. Add ABOUTME comments to new files                       │
└─────────────────────────────────────────────────────────────┘
    ↓
Done! (PR review happens in CI/CD pipeline)
```

## Components

### Commands

| Command | Description |
|---------|-------------|
| `/autonomous-sdlc:sdlc <description>` | Start autonomous workflow |
| `/autonomous-sdlc:sdlc-status` | Check workflow progress |
| `/autonomous-sdlc:sdlc-cancel` | Cancel active workflow |
| `/autonomous-sdlc:prime` | Orient to codebase before starting |

### Agents

| Agent | Model | Purpose | Key Feature |
|-------|-------|---------|-------------|
| **Architect** | Opus | Creates plan + Beads | Plan-first approach |
| **Worktree Manager** | Sonnet | Orchestrates parallel work | Spawns builder/validator pairs |
| **Builder** | Sonnet | Implements one task | PostToolUse validation hooks |
| **Validator** | Sonnet | Verifies implementation | Read-only, can't modify code |
| **Documenter** | Haiku | Updates docs | Runs after all validation |
| **Implementer** | Sonnet | Legacy TDD agent | Use Builder instead |

### Skills

| Skill | Purpose |
|-------|---------|
| `beads-workflow` | Beads commands for SDLC |
| `verification-stack` | Full verification pipeline |
| `tdd-workflow` | Test-driven development process |

### Validation Hooks

Builders have PostToolUse hooks that run automatically after every Write/Edit:

- **ruff_validator.py**: Runs Ruff linter on modified Python files
- **type_validator.py**: Runs mypy type checker on modified Python files

Issues are reported immediately so builders can fix them before accumulating debt.

## Prerequisites

- Claude Code v2.1.0+
- Git (for worktrees)
- Beads CLI (`bd` command)
- Project with test infrastructure
- `uv` for Python package management

## Key Concepts

### Plan Documents

Every SDLC workflow creates a plan document at `specs/{feature}-plan.md` containing:
- Task description and objectives
- Solution approach
- Team orchestration (builders, validators, documenter)
- Step-by-step tasks with dependencies
- Acceptance criteria
- Validation commands

### Builder/Validator Separation

- **Builders** focus on implementation with automatic quality checks
- **Validators** are read-only and cannot modify code
- This ensures unbiased verification of what was built

### Verification Stack

```
Tests (pytest) → Lint (ruff) → Types (mypy) → Build
```

If any gate fails, the agent fixes it before proceeding. No manual approval required.

### CI/CD Integration

PR review is handled by CI/CD pipelines, not in the SDLC workflow. This keeps the workflow focused on implementation while review is a separate concern.

## Differences from Previous Version

1. **Plan-First**: Architect creates `specs/{feature}-plan.md` BEFORE Beads
2. **Builder/Validator Pairs**: Separate agents for implementation and verification
3. **Automatic Validation**: PostToolUse hooks run Ruff + mypy on every edit
4. **Read-Only Validator**: Validator cannot modify code, only verify
5. **Documenter Step**: Ensures docs stay in sync with code
6. **No Reviewer**: PR review handled by CI/CD pipeline, not in-workflow
