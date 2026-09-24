---
name: setup
description: Configures a repo once for the compost skills, recording its issue tracker, domain doc layout, test convention, and verify gates under docs/agents/, and offers to move CLAUDE.md into AGENTS.md. Use when the user says "set up compost", "configure this repo", "set up the issue tracker", "migrate CLAUDE.md to AGENTS.md", "record our test gates", or a compost skill finds docs/agents/issue-tracker.md missing.
---

# Setup

The other compost skills assume a few facts about the repo: where issues live, where the glossary
and ADRs live, how tests are written, and which gates must pass before anything counts as done.
Setup finds those facts, confirms the ones that branch, and writes them to `docs/agents/`, where
every skill reads them. It also points the repo's instructions file at those docs and offers to
consolidate the instructions into `AGENTS.md`.

Setup is idempotent. Running it again updates what changed and keeps everything else, including
edits the user made by hand.

## Steps

1. **Explore.** Read what exists; assume nothing.
   - `git remote -v`: GitHub, GitLab (gitlab.com or a self-hosted host), or none.
   - Instruction files in the repo root and in every directory above it: `CLAUDE.md`,
     `.claude/CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/AGENTS.md`. Note any existing
     `## Agent skills` block and whether a `CLAUDE.md` is an `@AGENTS.md` import or a symlink.
   - `docs/agents/`: the output of an earlier run.
   - `CONTEXT.md`, `CONTEXT-MAP.md`, `docs/adr/`, and any `*/docs/adr/` in subpackages.
   - `.scratch/`: a sign a local tracker is already in use.
   - Monorepo signals: `pnpm-workspace.yaml`, a `workspaces` field in `package.json`,
     `[tool.uv.workspace]` in `pyproject.toml`, a Cargo `[workspace]`, `go.work`, or a populated
     `packages/*` whose members have their own sources.
   - Tests and gates: the test layout and framework in use, coverage configuration, linters, type
     checkers, formatters, `.pre-commit-config.yaml`, `Makefile` or `justfile` targets, package
     scripts, and the commands CI runs in `.github/workflows/` or `.gitlab-ci.yml`.

2. **Present findings and ask only where the answer branches.** Summarize what is present and
   what is missing, then take the sections below in order, one answer each. Lead with the
   recommendation so it can be accepted in a word. Skip a section entirely when exploration
   settled it. On a rerun, show what would change against the existing files instead.

3. **Issue tracker.** Recommend GitHub when a remote points there, GitLab when one points there,
   and otherwise offer GitHub, GitLab, local markdown under `.scratch/`, or other (Jira, Linear:
   the user describes the workflow in a paragraph and you record it as prose). Write
   `docs/agents/issue-tracker.md` from the matching template:
   [GitHub](references/issue-tracker-github.md), [GitLab](references/issue-tracker-gitlab.md),
   or [local](references/issue-tracker-local.md). Each carries the label vocabulary compost uses;
   if the tracker already has labels for the same roles, map them in the table rather than
   creating duplicates.

4. **Domain docs.** Default to a single context: one `CONTEXT.md` and `docs/adr/` at the root.
   Write that without asking. Offer a `CONTEXT-MAP.md` with one `CONTEXT.md` per context only
   when exploration found monorepo signals, and confirm the layout then
   ([ubiquitous language](../../canon/ubiquitous-language.md)). Write `docs/agents/domain.md` from
   [domain](references/domain.md). Don't create `CONTEXT.md` or `docs/adr/` now; `compost:spec`
   creates them when the first term or decision settles.

5. **Test convention and gates.** Work out the convention with the detection ladder in
   [testing](references/testing.md): adopt the pattern already in use, default by stack when there
   are no tests, and ask only for a greenfield repo with no clear stack. Then list the gates
   `compost:verify` will run: the suite command, the coverage command and threshold (100% line
   coverage unless the project already sets one), linters, type checkers, and anything CI treats
   as required. Run each gate once. Record the ones that pass as gates; record a gate that fails
   or doesn't run as broken, with its output's first error, rather than dropping it. Write
   `docs/agents/testing.md` from the template in the same reference.

6. **Instructions file and the AGENTS.md migration.** Claude Code reads `AGENTS.md` natively only
   when no `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` exists in the working directory
   or above it; `~/.claude/CLAUDE.md` doesn't count and still loads alongside. Follow
   [instruction files](references/instruction-files.md) for each combination you found. In short:
   - A project `CLAUDE.md` and no `AGENTS.md`: offer to move it into `AGENTS.md` with `git mv`,
     so both are never present. Personal preferences in it belong in `~/.claude/CLAUDE.md`; show
     which lines and move them only with the user's yes.
   - Both present: offer to fold `CLAUDE.md` into `AGENTS.md` and remove it.
   - Neither present: ask which to create, recommending `AGENTS.md`.
   - Never create one file while the other exists without offering first.

   Then add or update the `## Agent skills` block in whichever file holds the project
   instructions. Replace an existing block in place; leave the surrounding sections alone.

7. **Check and commit.** Re-read every file you wrote. List the directories above the repo that
   still hold a `CLAUDE.md`, since any of them stops `AGENTS.md` from loading. Commit the changes
   as one `chore: configure agent skills` commit. Tell the user which compost skills now read
   these files, that they can edit `docs/agents/*.md` directly, and, after a migration, to look
   for the `AGENTS.md loaded` line at the start of their next session.

## Next moves

- `compost:spec` when there is a feature or change to define.
- `compost:slice` when a spec already exists as an issue or doc.
- `compost:diagnose` when a gate came back broken and the repo should be green before other work.
