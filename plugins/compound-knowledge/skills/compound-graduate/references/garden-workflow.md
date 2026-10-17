# Garden Workflow

Detailed procedure for the `compound-graduate` garden face: keep the solutions corpus small and
true enough that retrieval keeps landing on the right file.

## Scope

Garden tends `{write_path}` only, the schema'd solutions that `compound-capture` writes. It never
edits other `read_paths` entries: the wiki belongs to `wiki-ingest`, and journals or decision docs
are not the solutions corpus. `critical-patterns.md` is in scope only for repointing links (step 5).

Garden never deletes. Archiving moves a file to `{write_path}/_archive/<category>/`, which
retrieval skips, so every verdict can be undone with a move back.

## Verdicts

Sort each candidate into exactly one:

| Verdict | When | What changes |
|---|---|---|
| **keep** | Still accurate and not duplicated | Nothing |
| **update** | The lesson holds but a detail rotted: a renamed path, a retired command, a version that moved on | Edit the stale detail in place; leave `date` as the original solve date |
| **merge** | Two or more files teach the same lesson | Fold the others into the strongest file (union of `symptoms` up to 5, `tags` up to 8, the best `## Root Cause`), then archive the others |
| **replace** | A newer file supersedes an older one with a different fix | Archive the older file; carry over any of its `symptoms` that still describe the newer fix |
| **archive** | The lesson no longer applies: the tool, service, or project it describes is gone | Move it to `_archive/` |

The strongest file in a merge is the one with the clearest root cause and the most complete fix,
not the newest one.

## Finding candidates

Read frontmatter only (`limit: 20`) for every `**/*.md` under `{write_path}`, skipping
`critical-patterns.md` and `_archive/`. Then look for:

- **Duplicates:** files sharing `component` with overlapping `symptoms` or `tags`, or near-identical
  titles. Group them; a group is a merge or replace candidate.
- **Rot:** files whose body names a path, command, flag, or tool the project no longer has. Check
  with `Grep`/`Glob` against the project before calling it stale; a guess is not evidence.
- **Contradictions:** two files that give different fixes for the same symptom. The newer one is
  usually right, but read both before ruling.
- **Retirements:** files about a project or service that no longer exists anywhere in the
  cross-project registry or on disk.

Everything else is **keep** without a full read. Full-read only the candidates.

## Propose, then apply

Garden rewrites what retrieval returns, so it proposes before it changes anything:

1. Show one table: file, verdict, one-line reason with the evidence (the missing path, the
   duplicate's filename, the contradicting fix). Omit `keep` rows unless asked.
2. Wait for confirmation. The user can accept all, accept some, or change a verdict.
3. Apply confirmed verdicts with `Edit` for updates and merges, and `git mv` (or `mv` outside a
   repo) into `_archive/<category>/` for archives.

## Keep the corpus consistent

After applying:

- **Links:** for every archived file, remove it from other files' `related_solutions`; for a merge,
  point those entries at the surviving file instead. Links stay bidirectional (see
  `compound-capture`'s YAML schema).
- **Critical patterns:** repoint any `critical-patterns.md` entry that cited an archived file to the
  survivor, or drop the citation if nothing replaced it.
- **Registry:** update `solution_count` and `primary_components` for this `{write_path}` in
  `~/.claude/compound-knowledge-registry.md`; archived files do not count.

## Verify

For each merge and replace, run the same frontmatter `Grep` a retrieval would (`symptoms:.*<error>`)
over `{write_path}`: it should now return the surviving file and nothing under `_archive/`. Report
the counts before and after (files, merges, archives) so the user can see what the pass did.
