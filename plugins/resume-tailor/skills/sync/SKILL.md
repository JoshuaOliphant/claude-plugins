---
name: sync
description: >
  Sync and manage the master resume source of truth. Three commands: sync (markdown → YAML),
  drift (detect differences between markdown and YAML), and export (output parsed data as JSON).
  The master resume at ~/.claude/resume-tailor/master-resume.md is the canonical source — edit it
  directly, then run sync to update the structured YAML. Use drift to check if they're out of
  sync. Trigger phrases include "sync my resume", "check resume drift", "update master resume",
  "are my resume files in sync", "export resume data", "master resume", and "resume source of truth".
args:
  - name: action
    description: "Action: sync, drift, or export (default: drift)"
    required: false
user-invokable: true
---

# Resume Sync Manager

Maintain the two-tier master resume system: a human-editable markdown file and a script-consumable YAML file.

## Files

| File | Purpose | Who edits it |
|------|---------|-------------|
| `~/.claude/resume-tailor/master-resume.md` | Canonical source of truth | You (directly) |
| `~/.claude/resume-tailor/master-resume.yaml` | Structured data for scripts/agents | Auto-generated |

## Commands

### Sync (markdown → YAML)

Parse the master markdown and regenerate the YAML:

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/master_sync.py sync
```

Run this after editing `master-resume.md` to keep the YAML in sync.

### Drift Detection

Check if the markdown and YAML are out of sync:

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/master_sync.py drift
```

Reports:
- **in_sync**: Both files match
- **drifted**: Shows specific differences (jobs added/removed, bullet count changes, skill category changes, project changes)
- **no_yaml**: YAML doesn't exist yet, needs initial sync

Present drift results as a readable table showing what's different.

### Export

Output the parsed master markdown as JSON (useful for debugging or piping to other tools):

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/master_sync.py export
```

## Workflow

1. Edit `~/.claude/resume-tailor/master-resume.md` (add a new role, update bullets, change skills)
2. Run `/resume-tailor:sync drift` to see what changed
3. Run `/resume-tailor:sync sync` to update the YAML
4. Next time `/resume-tailor` runs, it uses the master data as the starting point

## Integration with Main Pipeline

The main resume-tailor skill should check for `master-resume.md` during Phase 0. If it exists
and the user didn't provide a resume path, use the master as the starting point instead of
asking for a file path.
