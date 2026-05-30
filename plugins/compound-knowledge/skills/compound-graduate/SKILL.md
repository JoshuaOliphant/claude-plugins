---
name: compound-graduate
description: >
  Promote accumulated knowledge into living context. Use when the user says "graduate
  knowledge", "promote lessons", "update CLAUDE.md from what we've learned", "what should be
  in my CLAUDE.md", "compound graduate", "improve the system from my notes", or after a run of
  captures when patterns recur. Scans the read corpus (solutions + wiki theses) and proposes
  concrete edits to CLAUDE.md / AGENTS.md. Not for capturing (use compound-capture) or
  searching (use compound-retrieve).
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash]
---

# Compound Graduate (promote)

## Goal

Close the compound loop's "improve" edge: turn captured knowledge into visible improvements to
the always-loaded living context (`CLAUDE.md` / `AGENTS.md`). This is the *promote* face. The
garden/prune face is future work and out of scope here.

## When to run

After enough knowledge has accumulated that patterns recur, or on explicit request. Promotion
edits the file read every session, so it is high-trust: always propose before applying.

## Workflow

1. **Resolve the corpus.** Run the resolver to get the read corpus and semantic root:

   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_paths.py
   ```

   Use `read_paths` as the scan corpus and `vault_root` (if set) for semantic queries.

2. **Gather candidates** (prefer the most synthesized layer first):
   - `[solid]` and `[evolving]` theses under any `wiki/theses/` directory in `read_paths`.
   - High-severity solution files (`severity: critical` or `severity: high`) and any
     `critical-patterns.md` in `read_paths`.
   - Use `Grep` for keywords; when `vault_root` is set, use the `vault-recommender` MCP for
     topic clusters keyword search would miss.

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

## Additional Resources

- `scripts/resolve_paths.py` — resolves `write_path`, `read_paths`, `vault_root` from config.
- `references/promote-workflow.md` — detailed promotion procedure.
