# Instruction files and the AGENTS.md migration

## How Claude Code picks the project instructions

By default (Project instructions set to `claude-md-or-agents-md`), Claude Code v2.1.277 and later
reads `AGENTS.md` only when no `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` exists in the
working directory or any directory above it. If one exists, it reads the `CLAUDE.md` files and
ignores `AGENTS.md`, unless a `CLAUDE.md` imports it with `@AGENTS.md`.

These don't count, and keep loading alongside `AGENTS.md`: `~/.claude/CLAUDE.md`, the
organization's managed `CLAUDE.md`, and `.claude/rules/` files. That is why personal preferences
belong in `~/.claude/CLAUDE.md`, and project instructions, shared with the team and with other
coding agents, belong in `AGENTS.md`.

`AGENTS.local.md`, `AGENTS.override.md`, and anything under `.agents/` are never read.

Check the version with `claude --version`. Below v2.1.277, or with the built-in `agents-md` plugin
disabled, Claude reads `CLAUDE.md` only; there, a `CLAUDE.md` containing just `@AGENTS.md` is the
way to share one file.

## What to offer, case by case

Moving is always `git mv`, never a copy, so the two files are never both present and never drift
apart. Every move is an offer the user accepts first.

| Found | Offer |
|---|---|
| Project `CLAUDE.md` (or `.claude/CLAUDE.md`), no `AGENTS.md` | Move it to `AGENTS.md`. Personal lines go to `~/.claude/CLAUDE.md` (below). |
| `CLAUDE.md` and `AGENTS.md`, `CLAUDE.md` holding only `@AGENTS.md` or a symlink to it | Nothing is broken. Offer to delete the `CLAUDE.md` if the Claude Code version reads `AGENTS.md` natively. |
| `CLAUDE.md` and `AGENTS.md` with separate content | Claude sees only `CLAUDE.md` today. Offer to fold `CLAUDE.md`'s content into `AGENTS.md`, removing duplicates, then delete `CLAUDE.md`. |
| `CLAUDE.md` that tells Claude in words to read `AGENTS.md` | Claude opens `AGENTS.md` only if it decides to. Offer to delete the `CLAUDE.md`. |
| `CLAUDE.local.md` | It counts, so it blocks `AGENTS.md`. Offer to move general lines to `~/.claude/CLAUDE.md`, or to set Project instructions to `claude-md-and-agents-md` so both load. |
| A `CLAUDE.md` in a directory above the repo | It blocks `AGENTS.md` for this repo too. Report its path; it isn't this repo's file to move. |
| A `SessionStart` hook that prints `AGENTS.md` | Once `AGENTS.md` loads natively the hook adds a second copy. Offer to remove it. |
| Only `AGENTS.md` | Nothing to migrate. |
| Neither | Ask which to create, recommending `AGENTS.md`. |

If the user declines a migration, edit whichever file holds the project instructions today and
never create the other one.

The `claude-md-and-agents-md` setting goes in `~/.claude/settings.json`; project and local settings
files ignore it:

```json
{
  "pluginConfigs": {
    "agents-md@builtin": {
      "options": { "instructionFiles": "claude-md-and-agents-md" }
    }
  }
}
```

## Sorting personal from project lines

While moving, sort the lines into three piles and show them before writing anything:

- **Project:** true for anyone working in this repo (build commands, architecture, conventions).
  These go to `AGENTS.md`.
- **Personal:** true for this user in every repo (how to address them, their preferred tools,
  their workflow habits). Propose moving these to `~/.claude/CLAUDE.md`, dropping any that already
  say the same thing there.
- **Superseded:** instructions that contradict or restate the compost skills: a different issue
  tracker or task list than `docs/agents/issue-tracker.md` names, a test ritual, a spec or plan
  file location. Propose removing these so Claude isn't torn between two versions.

`~/.claude/CLAUDE.md` is the user's own file outside the repo; change it only with their yes.

## The Agent skills block

Add this to the file that holds the project instructions. If a `## Agent skills` section already
exists, replace its contents in place and leave the rest of the file alone.

```markdown
## Agent skills

### Issue tracker

<One line: where issues live, e.g. "GitHub issues via gh; specs are parent issues labelled spec.">
See `docs/agents/issue-tracker.md`.

### Domain docs

<One line: "Single context: CONTEXT.md and docs/adr/ at the root." or "Multiple contexts, listed in
CONTEXT-MAP.md.">. See `docs/agents/domain.md`.

### Tests and gates

<One line: the test convention and the coverage threshold.> See `docs/agents/testing.md`.
```

## After a migration

The next session in the repo should show a line like
`no CLAUDE.md found; AGENTS.md loaded: /path/to/repo/AGENTS.md`. If it doesn't, check for a
`CLAUDE.md` in a parent directory, a leftover `CLAUDE.local.md`, or an old Claude Code version.
