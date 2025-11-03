# ADW Infrastructure Upgrades

This document explains how to upgrade existing ADW infrastructure from one phase to another.

## Overview

ADW Bootstrap supports **progressive enhancement** with three phases:
- **Minimal** → **Enhanced** → **Scaled**

You can upgrade at any time without losing customizations.

## When to Upgrade

### Minimal → Enhanced
Upgrade when you:
- Want SDK-based execution for better type safety
- Need compound workflows (plan + implement in one command)
- Want interactive session support
- Are building a production application

**What it adds:**
- SDK execution module (`agent_sdk.py`)
- SDK CLI wrapper (`adw_sdk_prompt.py`)
- Slash command executor (`adw_slash_command.py`)
- Compound workflow script (`adw_chore_implement.py`)
- Richer slash commands (feature.md, prime.md)

### Enhanced → Scaled
Upgrade when you:
- Need state management across workflow phases
- Want git worktree isolation for parallel development
- Require GitHub integration (issues, PRs, comments)
- Need complete SDLC automation
- Building enterprise/team workflows

**What it adds:**
- State management module (`state.py`)
- Git operations module (`git_ops.py`)
- Worktree isolation module (`worktree_ops.py`)
- Workflow composition module (`workflow_ops.py`)
- GitHub integration module (`github.py`)
- Multi-phase workflows (`adw_sdlc_iso.py`, `adw_ship_iso.py`, etc.)
- 15+ advanced slash commands
- Worktree directory structure (`trees/`)

## Upgrade Process

### 1. Detection

The skill automatically detects existing ADW setup by checking for:
- `adws/adw_modules/agent.py` (primary indicator)
- Other key files to determine current phase

### 2. Classification

Based on file presence, classifies as:
- **Minimal**: Has agent.py, basic commands, no SDK
- **Enhanced**: Has SDK support, compound workflows, no state management
- **Scaled**: Has state management, worktree ops, GitHub integration

### 3. User Confirmation

Shows current phase and available upgrades:
```
🔍 Existing ADW setup detected!

Current Phase: Enhanced

Available upgrades:
- Scaled: Adds state management, worktree isolation, GitHub integration

Would you like to upgrade to Scaled?
```

### 4. Safety Backup

Before making changes:
```bash
mkdir -p .adw_backups
cp -r adws .adw_backups/adws_$(date +%Y%m%d_%H%M%S)
cp -r .claude .adw_backups/.claude_$(date +%Y%m%d_%H%M%S)
```

### 5. Customization Detection

Before adding each file:
- Check if file already exists
- Compare content with reference version
- If customized: Preserve and warn user
- If not customized: Safe to update
- When in doubt: Create `<file>.new` instead of overwriting

**Files never overwritten:**
- Any file with recent modification timestamp
- Any file with content differing from reference
- Any file in a `custom_` directory

### 6. Add New Capabilities

Only adds files that don't exist or aren't customized:
- New modules in `adws/adw_modules/`
- New workflow scripts in `adws/`
- New slash commands in `.claude/commands/`
- Directory structure (trees/, .adw_backups/)

### 7. Dependency Updates

**For Enhanced:**
- Ensure `claude-code-sdk` is in script dependencies
- Update inline deps in uv scripts (PEP 723)

**For Scaled:**
- Verify `gh` CLI is available
- Add extended data types if needed
- Create utility functions

### 8. Documentation Updates

Updates CLAUDE.md (if unmodified):
- Document new capabilities
- Add usage examples
- Update command reference

### 9. Validation

Runs checks:
```bash
# Check executability
chmod +x adws/*.py

# Test a simple prompt
./adws/adw_prompt.py "test upgrade" --model haiku
```

If validation fails, offers automatic rollback.

### 10. Report Results

```
🎉 Upgrade to Scaled completed successfully!

Added:
- 5 new modules
- 3 new workflows
- 15 new slash commands

Your customizations were preserved:
- adws/adw_prompt.py (customized)

Backup location: .adw_backups/20251103_102530

Try the new capabilities:
- ./adws/adw_sdlc_iso.py 123
- ./adws/adw_ship_iso.py 123 abc12345

To rollback: cp -r .adw_backups/20251103_102530/* ./
```

## Rollback

If upgrade fails or you want to revert:

```bash
# List available backups
ls -la .adw_backups/

# Rollback to specific backup
cp -r .adw_backups/adws_20251103_102530 adws/
cp -r .adw_backups/.claude_20251103_102530 .claude/

# Or restore from most recent
LATEST=$(ls -t .adw_backups/ | head -1)
cp -r .adw_backups/$LATEST/* ./
```

## Skip Phases

You can jump phases:

**Minimal → Scaled (skip Enhanced):**
The skill adds both Enhanced and Scaled capabilities in one upgrade.

This is safe because:
- All files are additive
- No breaking changes between phases
- Dependencies are properly managed

## Customization Preservation

The skill intelligently preserves customizations:

**Safe to update:**
- Files identical to reference versions
- Files with only minor formatting differences
- New files being added

**Preserved:**
- Files with significant code changes
- Files with custom functionality
- Files modified recently (within 7 days)
- Files in custom_* directories

**Resolution options:**
1. Keep custom version, skip update
2. Create `<file>.new` with new version, let user merge
3. Ask user to choose (for important files)

## Testing Upgrades

Before upgrading production:

1. Test on a branch:
```bash
git checkout -b test-adw-upgrade
# Run upgrade
# Test new capabilities
git checkout main
```

2. Use backup feature:
```bash
# Upgrade creates automatic backup
# If issues: cp -r .adw_backups/latest/* ./
```

3. Validate thoroughly:
```bash
./adws/adw_prompt.py "test" --model haiku
# Try new workflows
# Check customizations still work
```

## Upgrade Triggers

The skill activates upgrade mode when you say:
- "Upgrade my ADWs"
- "Upgrade ADW infrastructure"
- "Add enhanced ADW features"
- "Upgrade to scaled ADWs"
- "Add scaled capabilities"

## Advanced: Partial Upgrades

If you only want specific features:
- "Add git worktree support to my ADWs"
- "Add state management to my ADWs"
- "Add GitHub integration"

The skill can add individual modules without full phase upgrade.

## Troubleshooting

### Upgrade fails mid-process
- Automatic rollback to backup
- Check error message for specific issue
- Common causes: file permissions, missing dependencies

### New features don't work
- Check dependencies installed: `uv pip list`
- Verify gh CLI available: `gh --version`
- Check file permissions: `chmod +x adws/*.py`

### Customizations lost
- Check `.adw_backups/` directory
- Rollback and report issue
- Manual merge may be needed

### Validation fails
- Check error output
- Verify Claude Code CLI: `claude --version`
- Test manually: `./adws/adw_prompt.py "test"`

## Best Practices

1. **Commit before upgrading**
   ```bash
   git add .
   git commit -m "Pre-ADW upgrade checkpoint"
   ```

2. **Review what changed**
   ```bash
   git diff  # After upgrade
   ```

3. **Test new features**
   - Try each new capability
   - Verify existing workflows still work
   - Update documentation

4. **Clean up backups periodically**
   ```bash
   # Keep last 3 backups
   cd .adw_backups && ls -t | tail -n +4 | xargs rm -rf
   ```

5. **Document customizations**
   - Add comments explaining changes
   - Create custom_* files for major modifications
   - Keep notes in CLAUDE.md

## Phase Comparison

| Feature | Minimal | Enhanced | Scaled |
|---------|---------|----------|--------|
| Subprocess execution | ✅ | ✅ | ✅ |
| Basic CLI | ✅ | ✅ | ✅ |
| Basic slash commands | ✅ | ✅ | ✅ |
| SDK execution | ❌ | ✅ | ✅ |
| Interactive sessions | ❌ | ✅ | ✅ |
| Compound workflows | ❌ | ✅ | ✅ |
| State management | ❌ | ❌ | ✅ |
| Git worktree isolation | ❌ | ❌ | ✅ |
| GitHub integration | ❌ | ❌ | ✅ |
| Multi-phase workflows | ❌ | ❌ | ✅ |
| Port management | ❌ | ❌ | ✅ |
| Advanced commands | 2 | 7 | 20+ |

## Support

If you encounter issues during upgrade:
1. Check `.adw_backups/` for rollback
2. Review error messages carefully
3. Verify all dependencies installed
4. Test in clean environment
5. Report issue with upgrade log
