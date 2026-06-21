---
name: journal
description: Stick Shift close — render the durable session record (phase history + every logged decision + criterion status). The "session that survives" beat.
allowed-tools:
  - Read
  - Bash
---

# /journal — the durable session record

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

1. Run `python3 $STATE journal` and show the output: the phase history and every
   decision logged this session, straight from `.sdlc/`.
2. Read `specs/{slug}-spec.md` and append a final acceptance-criteria checklist
   (met / unmet), citing the test or behavior for each.
3. Narrate the close: this `.sdlc/` record is the durable session — it survived the
   whole build and is exactly what a shared corpus (e.g. compound-knowledge) would
   ingest. The harness was disposable; the session is the thing that survived.

Read-only — this command reports, it does not change state.
