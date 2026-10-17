---
allowed-tools: [Read, Write, Edit, Bash, Glob]
description: Initialize compound knowledge directory structure and optional path configuration
argument-hint: "[path]"
---

# Compound Knowledge Setup

Initialize the directory structure for capturing solutions and optionally configure a custom storage path.

## Setup Workflow

### Step 1: Determine Solutions Path

Start from what the capture and retrieve skills will use. Run the resolver on the project root:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_paths.py" "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

It prints JSON with `write_path` and `config_source`: `project` when
`{project_root}/.claude/compound-knowledge.local.md` exists, else `user` when
`~/.claude/compound-knowledge.local.md` exists, else `default`. The two files are not merged: when
a project config exists, the user config does not apply in this project at all. Exit 1 only means
`write_path` does not exist yet.

- **Argument given** (e.g., `/compound-knowledge:setup ~/my-knowledge/solutions/`): use that path,
  and write it to a config in Step 4.
- **The config the resolver read sets the path** (that file has a `write_path:` or
  `solutions_path:` line): the skills will write to the resolver's `write_path`. Tell the user
  which file set it and use that path; creating it is what setup is for. Only if they want a
  different location, ask for it as option 2 below.
- **Otherwise** (no config, or a config without either key): if a project config exists and the
  user config sets a path, tell the user that path doesn't apply in this project. Then ask:

> Where should solutions be stored?
>
> 1. **`knowledge/solutions/` in this project** (default — good for project-specific knowledge)
> 2. **Custom path** (e.g., a shared second brain — good for cross-project knowledge)

If option 1: use the resolver's `write_path` (the project's `knowledge/solutions/`).
If option 2: ask for the absolute path.

Write the chosen path the way the resolver prints paths: absolute, `~` expanded, one trailing
slash, so it compares with the resolver's `write_path` as a plain string. The chosen path is `{write_path}` below.

### Step 2: Create Directory Structure

Create the following directories under the chosen path:

```
{write_path}/
├── debugging/
├── infrastructure/
├── patterns/
├── workflow/
├── performance/
├── security/
├── ci-cd/
├── configuration/
├── migration/
├── integration/
├── principles/
└── critical-patterns.md
```

Use `mkdir -p` via Bash for the directories.

### Step 3: Create `critical-patterns.md`

Write the starter file at `{write_path}/critical-patterns.md`:

```markdown
# Critical Patterns

High-severity patterns that should be considered for every task. The knowledge-researcher agent reads this file on every search.

Add entries here when you encounter patterns with `severity: critical` or `severity: high` that apply broadly across projects.

## Format

### [Pattern Title]
- **Component**: {component}
- **Pattern**: {1-2 sentence description}
- **Why it matters**: {consequence of ignoring}
- **Source**: `{category}/{solution-file}.md`
```

### Step 4: Write the `.local.md` Config (If the Path Changed)

Skip this step when `{write_path}` is the `write_path` the resolver printed in Step 1.

Otherwise ask, every time:
> Should this be the default for **all projects** (user-level) or just **this project** (project-level)?

The config at that scope is `{project_root}/.claude/compound-knowledge.local.md` (project-level) or
`~/.claude/compound-knowledge.local.md` (user-level). If a project config exists, recommend
project-level: a user-level path won't apply here. If the file at the chosen scope exists, Edit it:
set its `write_path:` line (replacing a `solutions_path:` line if that is what it has) and keep
every other key, such as `read_paths` and `vault_root`. If it doesn't exist, Write it:

```markdown
# Compound Knowledge Settings
write_path: {write_path}
```

### Step 5: Verify

Run the resolver from Step 1 again, whether or not Step 4 ran. It must exit 0 and print
`{write_path}` as its `write_path`. If it doesn't, the skills will write somewhere else: report what
it printed and which config (`config_source`) won, and don't report success in Step 6.

### Step 6: Report

Print a summary of what was created:

```
Compound Knowledge initialized!

  Solutions directory: {write_path}
  Categories created: 10
  Config file: {config_path} (or "none — using default location")
  Resolver: exit 0, write_path {write_path}
  Registry: registered in ~/.claude/compound-knowledge-registry.md

  Next steps:
  - Solve a problem, then say "capture that" or invoke /compound-knowledge
  - Search past solutions with "check if we've seen this before"
  - Add critical patterns to critical-patterns.md as you discover them
```

### Step 7: Register Knowledge Base

Register this knowledge base in the cross-project registry so solutions are discoverable from other projects.

1. Read `~/.claude/compound-knowledge-registry.md`
   - If the file does not exist, create it with this header:
     ```markdown
     # Compound Knowledge Registry

     Central directory of all knowledge bases on this machine.
     Updated automatically when solutions are captured or `/compound-knowledge:setup` is run.

     ## Registered Knowledge Bases
     ```
2. Determine the project name from the current working directory (last path component, lowercase, hyphens)
3. Check if an entry already exists for `{write_path}` (search for the path string in the file)
4. **If entry exists**: Update `last_updated` to today's date, `solution_count` to 0, `primary_components` to []
5. **If new entry**: Append:
   ```markdown

   ### {project-name}
   - **path**: {write_path}
   - **last_updated**: {YYYY-MM-DD}
   - **solution_count**: 0
   - **primary_components**: []
   ```

See `${CLAUDE_PLUGIN_ROOT}/skills/compound-capture/references/registry-format.md` for the full schema and update rules.
