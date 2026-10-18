---
name: setup
description: Configures a repo once for the compost skills, recording its issue tracker, domain doc layout, core docs, test convention, verify gates, and observability stack under docs/agents/, and offers to move CLAUDE.md into AGENTS.md. Use when the user says "set up compost", "configure this repo", "set up the issue tracker", "migrate CLAUDE.md to AGENTS.md", "record our test gates", "set up observability", or a compost skill finds docs/agents/issue-tracker.md missing.
---

# Setup

The other compost skills assume a few facts about the repo: where issues live, where the glossary
and ADRs live, which docs are core, how tests are written, which gates must pass before
anything counts as done, and how to read what the running code emits.
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
   - Markdown outside the core docs (`docs/`, architecture notes, plan files), files that are
     product rather than prose (skill or prompt files, templates), and a published docs site
     (`mkdocs.yml`, `docusaurus.config.*`).
   - Monorepo signals: `pnpm-workspace.yaml`, a `workspaces` field in `package.json`,
     `[tool.uv.workspace]` in `pyproject.toml`, a Cargo `[workspace]`, `go.work`, or a populated
     `packages/*` whose members have their own sources.
   - Tests and gates: the test layout and framework in use, coverage configuration, linters, type
     checkers, formatters, `.pre-commit-config.yaml`, `Makefile` or `justfile` targets, package
     scripts, the commands CI runs in `.github/workflows/` or `.gitlab-ci.yml`, and mutation
     testing config (`cosmic-ray.toml`, `[tool.mutmut]`, `stryker.config.*`,
     `.cargo/mutants.toml`, a pitest plugin).
   - Telemetry: `.claude/harness/observability/`, and Logfire, Sentry, or OpenTelemetry in the
     dependencies or the app's startup code.

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
   creating duplicates. For GitHub or GitLab, list the tracker's labels
   (`gh api repos/{owner}/{repo}/labels --paginate --jq '.[].name'` / `glab label list`) and create
   every label in the table that it lacks (the template's label command / `glab label create`) now,
   so the first issue labelled `spec` doesn't fail.

4. **Domain docs.** Default to a single context: one `CONTEXT.md` and `docs/adr/` at the root.
   Write that without asking. Offer a `CONTEXT-MAP.md` with one `CONTEXT.md` per context only
   when exploration found monorepo signals, and confirm the layout then
   ([ubiquitous language](../../canon/ubiquitous-language.md)). Write `docs/agents/domain.md` from
   [domain](references/domain.md). Don't create `CONTEXT.md` or `docs/adr/` now; `compost:spec`
   creates them when the first term or decision settles.

5. **Core docs.** Write `docs/agents/docs.md` from [docs](references/docs.md): the core docs that
   exist, any the repo needs beyond the defaults, and the patterns that are product rather than
   documentation. Don't ask; the user edits the file if a default is wrong. Then run
   `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/doc_refs.py scan` with those patterns. If it lists
   non-core docs, tell the user how many, how many name paths that no longer exist or files that
   changed since, and that `compost:prune` will check them against the code, move what is worth
   keeping into names, types, tests, and comments, and delete the rest. Offer it as the next move
   after setup; pruning is its own change, never part of this commit
   ([core docs](../../canon/core-docs.md)).

6. **Test convention and gates.** Work out the convention with the detection ladder in
   [testing](references/testing.md): adopt the pattern already in use, default by stack when there
   are no tests, and ask only for a greenfield repo with no clear stack. Then list the gates
   `compost:verify` will run: the suite command, the coverage command and threshold (100% line
   coverage unless the project already sets one), linters, type checkers, and anything CI treats
   as required. Run each gate once. Record the ones that pass as gates; record a gate that fails
   or doesn't run as broken, with its output's first error, rather than dropping it. Record the
   mutation tool the same way: adopt one already configured, or offer the stack's default from
   [mutation testing](../verify/references/mutation.md), and run it once over the last commit
   that changed source. Write `docs/agents/testing.md` from the template in the same reference.

7. **Observability.** Find the telemetry the repo's running code emits with the detection ladder
   in [observability](references/observability.md): the observability harness, another stack
   already wired, or, with nothing found, one question offering the harness, the user's own
   stack, or none. Run one query against what you record, and record a stack you cannot read as
   broken with its first error. Write `docs/agents/observability.md` from the template in the same
   reference ([read the running system](../../canon/read-the-running-system.md)). Another skill
   that finds the file missing runs this step on its own: then also add the `### Observability`
   entry to the `## Agent skills` block (step 8) and commit both as
   `chore: record the observability stack`, so the next skill finds them.

8. **Instructions file and the AGENTS.md migration.** Claude Code reads `AGENTS.md` natively only
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

9. **Check the Jev key.** Run `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py status`. It looks for
   a TypeSafe key (`TYPESAFE_API_KEY`, then the macOS Keychain item `typesafe`) and builds the
   client, but sends no request. Exit 0 means the Jev tools will answer. Exit 3 means every Jev step
   will fall back to your own judgment: tell the user what they lose (cheaper test placement, review
   triage, the Stop guard in unattended runs) and pass on the fix its one line names. With no key,
   that is a command for them to run themselves, for example as
   `! security add-generic-password -s typesafe -a "$USER" -w`; when the client could not start,
   it is the key's format or the proxy setting it quotes. Never ask for the key
   in chat or write it anywhere. The key belongs to the machine, not the repo, so record nothing.

10. **Switch off what compost replaces.** Run
    `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/pile.py replaced`. It reads the `[replaces]` table in
    compost's `pile.toml` and reports which superseded plugins and skills are still active on this
    machine; it changes nothing. Leaving them on gives Claude two answers to every request. Show
    the user the report and, with their yes, run it again with `--apply`: it disables the plugins
    through `claude plugin disable` and sets the skills to `"off"` in `skillOverrides` in
    `~/.claude/settings.json`, keeping everything else there. Plugins synced from claude.ai can
    only be turned off in the user's claude.ai settings, so pass those on. None of this deletes
    anything: re-enabling a plugin or removing an override turns it back on.

    The report also lists, under its own heading, **orphaned installs**: plugins still installed
    whose marketplace's clone no longer lists them, enabled or not. They load stale copies and fail
    every marketplace update. `--apply` uninstalls them through `claude plugin uninstall`, keeping
    their data directories, and unlike disabling this cannot be undone, since the marketplace no
    longer offers them. Ask about them as a separate yes: if the user wants the superseded ones
    turned off but the orphans kept, run `--apply --keep-orphans`. This is per machine, so on a
    second repo the report usually says nothing is active.

11. **Check and commit.** Re-read every file you wrote. List the directories above the repo that
    still hold a `CLAUDE.md`, since any of them stops `AGENTS.md` from loading. Run
    `git check-ignore -v` on every file you wrote in the repo: each `docs/agents/*.md`, the
    instructions file, and any `CONTEXT-MAP.md` or `CONTEXT.md`. It prints a
    `source:line:pattern` line for each ignored path, and a broad rule (`agents/` also matches
    `docs/agents/`) leaves a file out of the commit without a word. For each hit, show the user the
    rule and offer to anchor it (`/agents/`) or narrow it, editing the file it came from only with
    their yes; if they keep it, say which files the commit leaves out. Commit the changes as one
    `chore: configure agent skills` commit. Tell the user which compost skills now read
    these files, that they can edit `docs/agents/*.md` directly, and, after a migration, to look
    for the `AGENTS.md loaded` line at the start of their next session. Also tell them that in
    manual permission mode the `/compost:review-changes` workflow asks for permission on every run
    until they pick "Yes, and don't ask again", or until they add `Workflow(compost:review-changes)`
    to their allow rules.

## Next moves

- `compost:prune` when the core-docs step found docs outside the core, so the repo starts with
  docs the code backs.
- `compost:spec` when there is a feature or change to define.
- `compost:slice` when a spec already exists as an issue or doc.
- `compost:diagnose` when a gate came back broken and the repo should be green before other work.
