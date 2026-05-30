# Promote Workflow

Detailed procedure for the `compound-graduate` promote face.

## Candidate selection (priority order)

1. **Wiki theses** (`wiki/theses/**`) marked `[solid]` — distilled, high-confidence positions.
   These are the best fuel: already synthesized, unlike individual lessons.
2. **Wiki theses marked `[evolving]`** — promote only the stable core, phrased provisionally.
3. **`critical-patterns.md`** entries in any read path.
4. **Solution files** with frontmatter `severity: critical` or `severity: high`.
5. Recurring patterns: the same lesson appearing across 3+ solution files is itself a signal.

Skip: `[hypothesis]` / `[questioning]` theses, low-severity one-offs, anything project-specific
that would not generalize to the target context file.

## Propose-then-apply protocol

For each candidate:

1. Draft the smallest edit that captures the pattern. One pattern per edit.
2. Write evergreen prose: describe the rule as it is, not how it evolved. No "recently",
   "now we", "as of", or change-log phrasing.
3. Place it in the matching section of the target (`CLAUDE.md` / `AGENTS.md`); create a section
   only if none fits.
4. Show the proposed diff. Wait for confirmation. Do not batch-apply silently.
5. On confirmation, apply with `Edit`. On rejection, drop it and move on.

## Hard rules

- **Never write wiki files.** Promote reads `wiki/theses/`; only `wiki-ingest` writes the wiki.
  This prevents a synthesis loop between the two.
- **Living context is high-trust.** Always propose before editing `CLAUDE.md` / `AGENTS.md`.
- **`critical-patterns.md` is lower-trust.** Elevating a broadly-useful pattern into
  `{write_path}/critical-patterns.md` may be applied directly, then reported.

## Verification checklist (per promotion)

- Would a fresh session, reading only the updated context file, now avoid the mistake or apply
  the pattern without being told? If no, the edit is too vague — sharpen it.
- Is the edit evergreen (no temporal references)?
- Is it generalizable, not a project-specific detail that belongs in a solution file instead?
