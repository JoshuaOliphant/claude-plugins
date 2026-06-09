# Autonomous SDLC Plugin

Adaptive autonomous software development lifecycle for Claude Code. The lead orchestrator chooses the right coordination mode — solo, subagents, or agent teams — based on task complexity.

## Key Features

- **Adaptive Orchestration**: Lead decides coordination mode per-task (solo, subagents, agent teams)
- **Agent Teams Support**: Teammates message each other directly when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- **Prompt Objects**: Agents use identity/context/success-criteria instead of step-by-step scripts
- **Optional Worktrees**: Parallel isolation when needed, shared directory when not
- **Plan-First Architecture**: Comprehensive plan documents before implementation
- **Builder/Validator Pairs**: Separate implementation and verification with direct feedback
- **Automatic Validation Hooks**: Ruff + type checking on every edit
- **Graceful Degradation**: Works without agent teams, without Beads, without worktrees

## Quick Start

```bash
# Start an SDLC workflow
/autonomous-sdlc:sdlc "Add user authentication with JWT tokens"

# Check status
/autonomous-sdlc:sdlc-status

# Cancel workflow (if needed)
/autonomous-sdlc:sdlc-cancel
```

## How It Works

The lead orchestrator assesses your request and picks a coordination mode:

### Simple Tasks (1-2 tasks)
Lead does it directly or uses a single subagent. No worktrees needed.

### Moderate Tasks (3-5 tasks)
Subagents with optional worktrees. Architect plans, builders implement, validators verify.

### Complex Tasks (6+ tasks)
Agent teams preferred (if available). Teammates self-coordinate, builders and validators communicate directly.

## Workflow Phases

```
/sdlc "Add user authentication"
    ↓
┌───────────────────────────────────────────┐
│ LEAD ORCHESTRATOR (Fable or Opus)           │
│                                             │
│  1. Orient — understand codebase            │
│  2. Plan — feature branch + plan doc        │
│  3. Decompose — break into tasks            │
│  4. Build — solo, subagents, or team        │
│  5. Verify — validators check work          │
│     ↳ Refine — simplify + re-verify (opt.)  │
│  6. Integrate — merge if using worktrees    │
│  7. Document — update docs                  │
│     ↳ Review Gate — semantic review (opt.)  │
│  8. Ship — create PR                        │
│                                             │
│  Phases are flexible, not sequential.       │
│  Lead may skip, reorder, or combine.        │
└───────────────────────────────────────────┘
    ↓
Done! PR ready for human review
```

## Agents

| Agent | Model | Purpose | Key Feature |
|-------|-------|---------|-------------|
| **Architect** | Fable | Creates feature branch + plan + tasks | Plan-first |
| **Builder** | Opus | Implements one task with TDD | PostToolUse hooks |
| **Validator** | Sonnet | Verifies implementation (read-only) | Direct builder feedback |
| **Integrator** | Sonnet | Merges task branches (optional) | Conflict resolution |
| **Documenter** | Haiku | Updates docs | Fast, efficient |
| **PR-Creator** | Haiku | Creates PR/MR | GitHub + GitLab |

Reference patterns (not spawnable):
| Pattern | Purpose |
|---------|---------|
| **Worktree/Wave Guide** | Worktree creation, wave processing, integration loops |

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
| `bdd-spec` | Acceptance criteria co-authoring |
| `bdd-generate` | BDD test scaffolding with pytest-bdd |

## Coordination Modes

### Subagent Mode (Default)
Wave-based processing with background subagents. The lead spawns builders in parallel, validators after, integrates between waves.

### Agent Teams Mode
Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Teammates communicate directly — validators message builders with feedback instead of creating fix tasks. Faster iteration cycles.

### Solo Mode
For simple tasks, the lead just does the work directly.

## Branch Strategy

```
main
 └── feature/user-auth                    ← Feature branch
      ├── feature/user-auth/beads-abc     ← Task branch (if using worktrees)
      ├── feature/user-auth/beads-def     ← Task branch (if using worktrees)
      └── feature/user-auth/beads-ghi     ← Task branch (if using worktrees)
```

Without worktrees, all work happens directly on the feature branch.

## Validation Hooks

Builders have PostToolUse hooks that run automatically:

| Hook | Purpose |
|------|---------|
| `ruff_validator.py` | Lint Python files |
| `type_validator.py` | Type check Python files |

Issues are reported immediately so builders fix them inline.

## Recommended Settings

Add the following to your project's `.claude/settings.json` to align Claude Code's built-in `/plan` mode with the `specs/` convention used by the Architect agent:

```json
{
  "plansDirectory": "specs"
}
```

**Why this matters**: The Architect agent writes plan documents to `specs/{feature-slug}-plan.md`. Claude Code v2.1.9+ also has a `/plan` mode that stores plan files — but by default it stores them in a different location. Setting `plansDirectory: "specs"` ensures that `/plan` mode output and Architect-generated plans land in the same directory, so the full team (lead, builders, validators) always finds plans where they expect them.

## Prerequisites

- Claude Code v2.1.0+
- Git
- `gh` CLI (GitHub) or `glab` CLI (GitLab)
- `uv` for Python package management
- Optional: Beads CLI (`bd` command) for task tracking
- Optional: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` for agent teams

## Verification Stack

```
Tests (pytest) → Lint (ruff) → Types (mypy) → Build
```

If any gate fails, the agent communicates the issue and fixes it.

## Version History

### v1.2.0 (Current)
- Added `effort` and `allowed-tools` frontmatter to all 6 SKILL.md files
- Fixed invalid `permissionMode: "none"` on all 6 agents (now correctly set per agent role)
- Added `background: true` to builder for default parallel wave execution
- Added `if: "Write(*.py)|Edit(*.py)"` condition to builder PostToolUse hooks (prevents subprocess spawning on non-Python files)
- Added PostCompact hook: re-injects in-progress Beads context after context compaction
- Added WorktreeCreate/WorktreeRemove hooks: lifecycle logging + systemMessage injection
- Added StopFailure hook: logs API errors and surfaces them as systemMessage alerts

### v1.1.0
- Eval suites for all 5 skills (bdd-spec, bdd-generate, tdd-workflow, verification-stack, beads-workflow)
- Beads project configuration (.beads/ directory with config.yaml)
- Git attributes for Beads JSONL merge strategy

### v0.4.0
- Adaptive orchestration — lead chooses coordination mode per-task
- Agent teams support with direct builder-validator communication
- Prompt objects replace procedural step-by-step instructions
- Worktrees are optional, not required
- Worktree-manager absorbed into lead (now a reference pattern)
- Removed legacy implementer agent
- Graceful degradation without agent teams, Beads, or worktrees

### v0.3.0
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
