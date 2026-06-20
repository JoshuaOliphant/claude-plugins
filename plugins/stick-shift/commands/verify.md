---
name: verify
description: Stick Shift phase 4 — run the suite and walk each acceptance criterion ("passing ≠ satisfied"), then stop.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
---

# /verify — prove the spec, not just green tests

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

1. **Mechanical:** run the full test suite (e.g. `uv run pytest -q`) and the linters the
   project uses. Report the real result — never paper over a failure.
2. **Spec compliance:** open `specs/{slug}-spec.md` and walk AC-1, AC-2, … one by one.
   For each, point to the test or behavior that demonstrably satisfies it. Tests passing
   is not the same as the spec being met.
3. **Record + commit fixes:**
   - All green and every criterion met → `python3 $STATE transition DONE --reason "all N
     criteria met"`.
   - Anything red or unmet → `python3 $STATE transition BUILD --reason "AC-k unmet"` and
     name the gap so the next `/build` fixes it.
4. **Stop. Hand control back.** End with a per-criterion checklist (met/unmet) and the
   next move. Optionally suggest the built-in `/code-review` skill before the close.

One phase per command.
