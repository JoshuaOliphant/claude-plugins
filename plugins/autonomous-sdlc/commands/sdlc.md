---
name: sdlc
description: Start an autonomous SDLC workflow with parallel worktrees, builder/validator pairs, and verification-driven development
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - Write
argument-hint: "<description of what to build>"
---

# Autonomous SDLC Workflow

You are starting an autonomous software development lifecycle workflow. This workflow uses:

- **Plan Documents** for comprehensive feature planning with team orchestration
- **Beads** for work tracking and dependency management
- **Git worktrees** for isolated parallel development
- **Builder/Validator pairs** for implementation and verification
- **TDD** for test-driven implementation
- **Automatic validation hooks** for real-time quality enforcement
- **Documenter** for keeping docs in sync with code

## Arguments

The user has requested: $ARGUMENTS

## New Workflow Architecture

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
│   3. Spawn Builder agents in parallel (run_in_background)    │
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

## Workflow Steps

### Step 1: Create SDLC Marker

Create a marker to enable auto-approval during the workflow:

```bash
mkdir -p .sdlc
echo "$(date -Iseconds)" > .sdlc/started
echo "$ARGUMENTS" > .sdlc/description
```

### Step 2: Spawn Architect Agent

Use the Task tool to spawn the architect agent:

```python
Task(
    subagent_type="autonomous-sdlc:architect",
    description="Create plan and Beads",
    prompt=f"""
Analyze this request and create an implementation plan:

{user_request}

Instructions:
1. Explore the codebase to understand existing patterns
2. Create a plan document at specs/{{feature-slug}}-plan.md
3. Include Team Orchestration section with builders/validators
4. Include Step by Step Tasks table with dependencies
5. Create Beads with `bd create` for each task
6. Set dependencies with `bd dep add`
7. Report the task graph when done

The plan document is the source of truth - create Beads FROM the plan.
"""
)
```

### Step 3: Spawn Worktree Manager

After the architect completes, spawn the worktree manager:

```python
Task(
    subagent_type="autonomous-sdlc:worktree-manager",
    description="Orchestrate parallel implementation",
    prompt="""
Manage the implementation of ready Beads using builder/validator pairs:

1. Run `bd ready` to find unblocked tasks
2. Create worktrees for each ready Bead
3. For each Bead:
   a. Spawn Builder agent (run_in_background=True)
   b. After Builder completes, spawn Validator agent
   c. Validator verifies and closes Bead if passing
4. Monitor progress and iterate until all Beads are closed

Use `autonomous-sdlc:builder` and `autonomous-sdlc:validator` agents.
Builders have automatic PostToolUse hooks for Ruff and type checking.
Validators are read-only and cannot modify code.
"""
)
```

### Step 4: Spawn Documenter

After all implementation and validation is complete:

```python
Task(
    subagent_type="autonomous-sdlc:documenter",
    description="Update documentation",
    prompt="""
Update documentation to match the implemented features:

1. Read the plan file from specs/ to understand what was built
2. Find new Python files and add ABOUTME comments
3. Add docstrings to new public functions
4. Update README.md with new features and usage examples
5. Commit documentation changes

The plan's acceptance criteria tell you what features to document.
"""
)
```

### Step 5: Cleanup

After the workflow completes:

```bash
# Remove SDLC marker
rm -rf .sdlc

# Sync Beads
bd sync

# Report completion
echo "SDLC workflow complete"
```

## Agent Summary

| Agent | Model | Purpose | Key Feature |
|-------|-------|---------|-------------|
| **Architect** | Opus | Creates plan + Beads | Plan-first approach |
| **Worktree Manager** | Sonnet | Orchestrates parallel work | Spawns builder/validator pairs |
| **Builder** | Sonnet | Implements one task | PostToolUse validation hooks |
| **Validator** | Sonnet | Verifies implementation | Read-only, can't modify code |
| **Documenter** | Haiku | Updates docs | Runs after all validation |

## Error Handling

If any agent fails:
1. Check Beads status: `bd list --status=open`
2. Check worktree status: `git worktree list`
3. Check plan file: `cat specs/*-plan.md`
4. Resume from the failed point or clean up and restart

## Progress Tracking

Use TodoWrite to track high-level progress:

```python
TodoWrite([
    {"content": "Architect: Create plan and Beads", "status": "in_progress"},
    {"content": "Worktree Manager: Parallel implementation", "status": "pending"},
    {"content": "Documenter: Update documentation", "status": "pending"},
    {"content": "Cleanup and sync", "status": "pending"}
])
```

Update todos as each phase completes.

## Key Differences from Previous Workflow

1. **Plan-First**: Architect creates `specs/{feature}-plan.md` BEFORE Beads
2. **Builder/Validator Pairs**: Separate agents for implementation and verification
3. **Automatic Validation**: PostToolUse hooks run Ruff + mypy on every edit
4. **Read-Only Validator**: Validator cannot modify code, only verify
5. **Documenter Step**: Ensures docs stay in sync with code
6. **No Reviewer**: PR review handled by CI/CD pipeline, not in-workflow

## Plan Document Location

Plans are stored at: `specs/{feature-slug}-plan.md`

Example slugs:
- "Add user authentication" → `specs/user-auth-plan.md`
- "Implement rate limiting" → `specs/rate-limiting-plan.md`

## CI/CD Integration

After SDLC workflow completes:
1. Feature branches are ready for PR
2. CI/CD pipeline runs Claude Code for PR review
3. Merge to main happens through normal PR process

This separation keeps the SDLC focused on implementation while PR review is a separate concern.
