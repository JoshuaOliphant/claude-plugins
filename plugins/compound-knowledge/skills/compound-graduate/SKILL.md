---
name: compound-graduate
description: >
  Promote accumulated knowledge into living context, and garden the solutions corpus. Use when
  the user says "graduate knowledge", "promote lessons", "update CLAUDE.md from what we've
  learned", "what should be in my CLAUDE.md", "compound graduate", "improve the system from my
  notes", or after a run of captures when patterns recur (promote); or "prune the knowledge
  base", "garden solutions", "dedupe solutions", "clean up stale solutions" (garden). Promote
  proposes edits to CLAUDE.md / AGENTS.md; garden sorts each solution into keep, update, merge,
  replace, or archive. Not for capturing (use compound-capture) or searching (use
  compound-retrieve).
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash]
---

# Compound Graduate

## Goal

Close the compound loop's "improve" edge. Graduate has two faces:

- **Promote** turns captured knowledge into visible improvements to the always-loaded living
  context (`CLAUDE.md` / `AGENTS.md`).
- **Garden** keeps the solutions corpus small and true, so retrieval keeps landing on the right
  file as it grows.

Pick the face from the request; when it is unclear, garden first, since promoting from a corpus
full of duplicates promotes the duplicates.

## When to run

Promote after enough knowledge has accumulated that patterns recur, or on explicit request.
Promotion edits the file read every session, so it is high-trust: always propose before applying.

Garden when retrieval starts returning near-duplicates or stale fixes, or on explicit request.
It rewrites what retrieval returns, so it also proposes before applying.

## Promote

1. **Resolve the corpus.** Run the resolver to get the read corpus and semantic root:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_paths.py" "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
   ```

   Use `read_paths` as the scan corpus and `vault_root` (if set) for semantic queries. If it
   exits 1, the solutions directory (`write_path`) does not exist: pass on the fix it printed to
   stderr, and scan only the `read_paths` entries that exist. Any other failure prints no JSON:
   report the error rather than guessing paths.

2. **Gather candidates** (prefer the most synthesized layer first):
   - Theses with frontmatter `confidence: solid` (then `evolving`) under any `wiki/theses/`
     directory in `read_paths`. Read the YAML `confidence:` field — do NOT grep for inline
     `[solid]` markers; wiki pages encode confidence in frontmatter, not the body.
   - High-severity solution files (`severity: critical` or `severity: high`) and any
     `critical-patterns.md` in `read_paths`.
   - Use `Grep` for keywords; when `vault_root` is set, use the `vault-recommender` MCP for
     topic clusters keyword search would miss. See `references/promote-workflow.md` for the
     two confidence conventions and full candidate heuristics.

3. **Identify the target.** Use `CLAUDE.md` at the project root if present, else `AGENTS.md`.

4. **Propose, do not apply yet.** For each candidate draft a concrete, minimal, evergreen edit
   to the target (one pattern; no temporal phrasing like "recently" or "now we"). Show the
   proposed diff and get confirmation. **Never edit wiki files here** — promote *reads* theses;
   only `wiki-ingest` *writes* the wiki.

5. **Apply confirmed edits** with `Edit`. The propose-before-apply gate above is for the
   living context (`CLAUDE.md` / `AGENTS.md`). Elevating a broadly-useful pattern into
   `{write_path}/critical-patterns.md` is lower-trust and may be applied directly, then
   reported — see `references/promote-workflow.md`.

6. **Verify each promotion:** ask *"would the system catch this automatically next session now
   that it lives in the always-loaded context?"* If not, refine the edit.

See `references/promote-workflow.md` for candidate heuristics, the propose-then-apply protocol,
and the verification checklist.

## Garden

1. **Resolve the corpus** with the same resolver as promote. Garden tends `write_path` only;
   it never edits other `read_paths` entries (the wiki belongs to `wiki-ingest`). If the
   resolver exits 1 there is nothing to garden: pass on its fix and stop.

2. **Find candidates** from frontmatter alone: duplicates (shared `component` with overlapping
   `symptoms` or `tags`), rot (a path, command, or tool the project no longer has, checked with
   `Grep`/`Glob`, not guessed), contradictions (two fixes for one symptom), and retirements.
   Skip `critical-patterns.md` and anything under `_archive/`.

3. **Sort each candidate** into exactly one verdict: **keep**, **update** (fix the stale detail
   in place), **merge** (fold duplicates into the strongest file), **replace** (archive a file a
   newer one supersedes), or **archive** (the lesson no longer applies).

4. **Propose, do not apply yet.** Show one table of file, verdict, and the evidence for it, and
   get confirmation.

5. **Apply confirmed verdicts.** Never delete: archiving moves a file to
   `{write_path}/_archive/<category>/`, which retrieval skips. Then repair the corpus: repoint
   or drop `related_solutions` links (they stay bidirectional), repoint `critical-patterns.md`
   citations, and update the registry count.

6. **Verify** that a retrieval-style frontmatter `Grep` for each merged lesson's symptoms now
   lands on the survivor alone, and report the counts before and after.

See `references/garden-workflow.md` for the verdict table, candidate heuristics, and the
consistency rules.

## Additional Resources

- `scripts/resolve_paths.py` — resolves `write_path`, `read_paths`, `vault_root` from config.
- `references/promote-workflow.md` — detailed promotion procedure.
- `references/garden-workflow.md` — detailed garden procedure.
