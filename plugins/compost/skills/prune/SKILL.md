---
name: prune
description: Finds doc drift, where documentation says something the code no longer does, and settles it in the code's favour. What a doc says that the code could say moves into names, types, tests, or a comment at the point of use; the doc then goes, leaving only the core docs (README, AGENTS.md, CONTEXT.md, ADRs). Use when the user says "prune the docs", "the docs are stale", "check the docs against the code", "find doc drift", "we have too much documentation", "clean up docs/", or compost:setup offers it.
---

# Prune

A doc that restates the code drifts from it, and an agent can't tell the stale sentence from the
true one: it reads both as instructions. Code can't drift from itself. Prune checks each doc
against the code, takes the code as the more likely truth, moves whatever is still worth saying
into the code, and deletes the rest. What remains is the core docs, the few files that say what
code can't. The why is in [core docs](../../canon/core-docs.md) and
[subtract before you add](../../canon/subtract-before-you-add.md).

## Steps

1. **Read the policy.** Read `docs/agents/docs.md` for the repo's core docs and the files that are
   not docs at all. If it is missing, write it now from [the template](../setup/references/docs.md)
   and say so. Files that are product rather than documentation stay out of the scan: skill and
   prompt files, templates, generated reference, vendored docs. Ask only when exploration finds a
   published docs site (`mkdocs.yml`, `docusaurus.config.*`, a `docs/` a build turns into pages),
   since pruning it changes what users read.

2. **Scan.** Run `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/doc_refs.py scan`, with a `--core` and an
   `--exclude` for each pattern docs.md lists. It prints every tracked markdown file, non-core
   first and most suspicious first, with `missing` (paths it names that don't exist) and `stale`
   (files it names, with the commits each has had since the doc last changed). These are leads,
   not verdicts. A missing path can be an example (`src/orders.py` in a template) or a file the
   tool creates at runtime; a doc with no leads can still describe behaviour the code dropped.

3. **Check every doc against the code.** When the non-core docs fit in one careful read, check them
   yourself with the brief in [check](references/check.md). When there are more, send subagents in
   one message, one per handful of docs, each with that brief and its docs' scan entries. Either way
   every doc's claims are sorted into four kinds with the file:line that settles each:
   - **Drifted:** the code says otherwise.
   - **Restated:** true today, and already said by the code: a signature, a config file, a test.
   - **Keeper:** something the code can't say: why it is this way, an alternative that was
     rejected, a domain term, an operational step, a constraint from outside the repo.
   - **Plan:** future work, a design never built, or a plan already carried out.

   Code is the likely truth, not the certain one. When a doc states a requirement the code breaks,
   look for backing: a test that pins the doc's version, an issue, an ADR, the user's word. Backed
   means a bug, not drift: leave the doc, file an issue per `docs/agents/issue-tracker.md`, and
   offer `compost:diagnose`. An ADR is a record and is never edited to match the code; flag the
   conflict as `docs/agents/domain.md` says. Core docs get checked too, and fixed in place, never
   deleted.

4. **Give each keeper a home in the code.** Walk the ladder in [homes](references/homes.md) and
   stop at the first rung that holds the claim:
   1. A name that says it, so the sentence becomes unnecessary.
   2. A type or a check that enforces it, so breaking it fails loudly.
   3. A test that shows it, named in the domain's terms.
   4. A comment where the code it explains lives: why, never what.
   5. A core doc: a term to `CONTEXT.md`, a decision to an ADR (offered only for decisions that pass
      the test in [domain docs](../spec/references/domain-docs.md)), a command or convention to
      `AGENTS.md`, what the project is and how to run it to the README.

   Drifted and restated claims have no home; they go. A plan still wanted becomes an issue, and
   one that isn't is deleted, since git keeps the history. A rename across a public interface or
   a deploy boundary doesn't happen here: file it as an issue
   ([expand, migrate, contract](../../canon/expand-contract.md)).

5. **Present the plan.** Per doc: delete, shrink to its keepers, or fix in place. Per keeper: its
   rung and the file it lands in. Per backed contradiction: the issue you will file. Lead with the
   count of docs that go. Wait for the user's yes, for all of it or doc by doc. Inside an
   unattended run, prune nothing; post the plan where the run reports and stop.

6. **Prune, then plant.** Commit the deletions and trims first, on their own
   (`docs: prune docs that drifted from the code`), then the code moves. Re-run the scan and fix
   every `missing` that points at a deleted doc. A rename or a new type is a code change, so run
   `compost:verify` on the moves before calling it done.

7. **Record the policy.** Update `docs/agents/docs.md` to list the core docs as they now stand and
   the patterns the scan left out. Add or update the `### Docs` entry in the `## Agent skills`
   block, as in [instruction files](../setup/references/instruction-files.md). That entry is what
   keeps the repo pruned: every agent that reads it learns that a new fact goes in the code or a
   core doc, not a new file. Commit it as `chore: record the core docs`.

## Next moves

- `compost:diagnose` when a doc turned out to be right and the code wrong.
- `compost:deepen` when keepers for one module keep landing as comments: the module is hard to
  read, and its shape is the fix.
- `compost:spec` when a plan doc describes a feature that is still wanted.
- `compost:finish` to open the pull request.
