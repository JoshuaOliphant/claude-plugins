---
name: sdlc
description: Start an autonomous SDLC workflow with feature branches, wave-based integration, and PR creation
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

- **Feature Branches**: One branch per feature, task branches underneath
- **Plan Documents**: Comprehensive feature planning with team orchestration
- **Beads**: Work tracking and dependency management
- **Git Worktrees**: Isolated parallel development
- **Builder/Validator Pairs**: Implementation and verification
- **Wave-Based Integration**: Merge after each wave so dependencies work
- **Automatic PR Creation**: Generate PR with rich description

## Arguments

The user has requested: $ARGUMENTS

## Complete Workflow Architecture

```
/sdlc "Add user authentication"
    ↓
┌─────────────────────────────────────────────────────────────┐
│ ARCHITECT (Opus)                                             │
│   1. Explore codebase                                        │
│   2. Create feature branch: feature/user-auth                │
│   3. Create specs/user-auth-plan.md                          │
│   4. Create Beads from plan with dependencies                │
│   5. Report task graph with waves                            │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ WORKTREE MANAGER (Sonnet) - Wave Loop                        │
│                                                              │
│   WAVE 1 (tasks with no deps):                               │
│   ├─ Create worktrees from feature branch                    │
│   ├─ Spawn Builders in parallel                              │
│   ├─ Spawn Validators after builders                         │
│   └─ INTEGRATE into feature branch                           │
│          ↓                                                   │
│   WAVE 2 (tasks that depended on Wave 1):                    │
│   ├─ Create worktrees (now sees Wave 1 code!)                │
│   ├─ Spawn Builders in parallel                              │
│   ├─ Spawn Validators after builders                         │
│   └─ INTEGRATE into feature branch                           │
│          ↓                                                   │
│   ... repeat until all Beads closed ...                      │
└─────────────────────────────────────────────────────────────┘
    ↓ (all waves complete)
┌─────────────────────────────────────────────────────────────┐
│ DOCUMENTER (Haiku)                                           │
│   1. Read plan for context                                   │
│   2. Add ABOUTME comments to new files                       │
│   3. Add/update docstrings                                   │
│   4. Update README with new features                         │
│   5. Commit documentation changes                            │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ PR-CREATOR (Sonnet)                                          │
│   1. Push feature branch to remote                           │
│   2. Generate PR description from plan                       │
│   3. Create PR/MR (GitHub or GitLab)                         │
│   4. Add labels and reviewers                                │
│   5. Return PR URL                                           │
└─────────────────────────────────────────────────────────────┘
    ↓
Done! PR ready for human review
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

The Architect creates the feature branch, plan, and Beads:

```python
Task(
    subagent_type="autonomous-sdlc:architect",
    description="Create feature branch, plan, and Beads",
    prompt=f"""
Create an implementation plan for:

{user_request}

Instructions:
1. Explore the codebase to understand existing patterns
2. Create feature branch: feature/{{feature-slug}}
3. Create plan document at specs/{{feature-slug}}-plan.md
4. Include Team Orchestration section with builders/validators
5. Include Step by Step Tasks table with dependencies
6. Create Beads with `bd create` for each task
7. Set dependencies with `bd dep add`
8. Report the feature branch name and task graph

The feature branch is the integration target. All task branches will be created from it.
"""
)
```

### Step 3: Spawn Worktree Manager

The Worktree Manager handles wave-based execution and integration:

```python
Task(
    subagent_type="autonomous-sdlc:worktree-manager",
    description="Execute waves with integration",
    prompt=f"""
Execute the SDLC workflow for feature/{feature_slug}:

Feature branch: feature/{feature_slug}
Plan file: specs/{feature_slug}-plan.md

Instructions:
1. Process tasks in waves (bd ready shows current wave)
2. For each wave:
   a. Create worktrees FROM feature/{feature_slug}
   b. Spawn Builders in parallel
   c. Spawn Validators after builders complete
   d. Spawn Integrator to merge wave into feature branch
3. Repeat until all Beads are closed
4. Clean up worktrees

Task branches should be named: feature/{feature_slug}/beads-xxx
Integrate after EACH wave so subsequent waves see previous code.
"""
)
```

### Step 4: Spawn Documenter

After all implementation is complete:

```python
Task(
    subagent_type="autonomous-sdlc:documenter",
    description="Update documentation",
    prompt=f"""
Update documentation for feature/{feature_slug}:

1. Read specs/{feature_slug}-plan.md for context
2. Find new Python files and add ABOUTME comments
3. Add docstrings to new public functions
4. Update README.md with new features and usage
5. Commit documentation changes to feature/{feature_slug}

Work on the feature branch, not main.
"""
)
```

### Step 5: Spawn PR-Creator

Create the pull request:

```python
Task(
    subagent_type="autonomous-sdlc:pr-creator",
    description="Create pull request",
    prompt=f"""
Create a PR for feature/{feature_slug}:

Feature branch: feature/{feature_slug}
Plan file: specs/{feature_slug}-plan.md
Target branch: main

Instructions:
1. Push feature branch to remote
2. Generate PR description from the plan document
3. Create PR using gh (GitHub) or glab (GitLab)
4. Include acceptance criteria as checklist
5. Link related Beads in description
6. Return the PR URL
"""
)
```

### Step 6: Cleanup

After PR is created:

```bash
# Remove SDLC marker
rm -rf .sdlc

# Sync Beads
bd sync

# Report completion with PR URL
echo "SDLC workflow complete"
echo "PR: {pr_url}"
```

## Agent Summary

| Agent | Model | Purpose | Key Feature |
|-------|-------|---------|-------------|
| **Architect** | Opus | Creates feature branch + plan + Beads | Plan-first approach |
| **Worktree Manager** | Sonnet | Orchestrates waves | Wave-based integration |
| **Builder** | Sonnet | Implements one task | PostToolUse validation hooks |
| **Validator** | Sonnet | Verifies implementation | Read-only, can't modify code |
| **Integrator** | Sonnet | Merges task branches | Runs per-wave |
| **Documenter** | Haiku | Updates docs | Fast, efficient |
| **PR-Creator** | Sonnet | Creates PR/MR | Supports GitHub + GitLab |

## Branch Strategy

```
main
 └── feature/user-auth                    ← Feature branch (Architect creates)
      ├── feature/user-auth/beads-abc     ← Task branch (Wave 1)
      ├── feature/user-auth/beads-def     ← Task branch (Wave 1)
      └── feature/user-auth/beads-ghi     ← Task branch (Wave 2)
```

After each wave, task branches merge INTO the feature branch.
After all waves, feature branch becomes PR against main.

## Wave-Based Integration

**Why integrate between waves?**

Without integration:
- Wave 1: Builder A creates `User` model
- Wave 2: Builder B needs `User` model but doesn't see it!

With integration:
- Wave 1: Builder A creates `User` model → merged into feature branch
- Wave 2: Builder B branches from feature branch → sees `User` model ✅

## Error Handling

If any agent fails:
1. Check Beads status: `bd list --status=open`
2. Check worktree status: `git worktree list`
3. Check plan file: `cat specs/*-plan.md`
4. Check feature branch: `git log feature/{name} --oneline -5`
5. Resume from the failed point or clean up and restart

## Progress Tracking

Use TodoWrite to track high-level progress:

```python
TodoWrite([
    {"content": "Architect: Create feature branch and plan", "status": "in_progress"},
    {"content": "Worktree Manager: Execute waves", "status": "pending"},
    {"content": "Documenter: Update documentation", "status": "pending"},
    {"content": "PR-Creator: Create pull request", "status": "pending"},
    {"content": "Cleanup and report", "status": "pending"}
])
```

## Key Features

1. **Feature Branch**: Single branch for entire feature, task branches underneath
2. **Plan-First**: Architect creates plan BEFORE Beads
3. **Wave-Based**: Tasks processed in dependency waves
4. **Inter-Wave Integration**: Each wave merges before next starts
5. **Builder/Validator Pairs**: Separate implementation and verification
6. **Automatic Validation**: PostToolUse hooks run Ruff + mypy
7. **Documentation Sync**: Documenter ensures docs match code
8. **PR Generation**: Automatic PR with rich description from plan

## Output

When complete, provide:

```markdown
## SDLC Workflow Complete

**Feature**: {description}
**Feature Branch**: feature/{slug}
**Plan**: specs/{slug}-plan.md

### Execution Summary
| Phase | Status |
|-------|--------|
| Architect | ✅ Complete |
| Wave 1 (3 tasks) | ✅ Integrated |
| Wave 2 (2 tasks) | ✅ Integrated |
| Wave 3 (1 task) | ✅ Integrated |
| Documenter | ✅ Complete |
| PR-Creator | ✅ Complete |

### Pull Request
**URL**: https://github.com/owner/repo/pull/123
**Title**: feat: Add user authentication
**Target**: main
**Status**: Open (ready for review)

### Next Steps
1. Review the PR
2. Address any review feedback
3. Merge when approved
```
