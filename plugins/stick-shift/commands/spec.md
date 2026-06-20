---
name: spec
description: Stick Shift phase 1 — turn a task into 3–5 Given/When/Then acceptance criteria, init the session, and stop. You choose when to /plan.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
argument-hint: "<what to build>"
---

# /spec — define "done" before any code

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py` (run with `python3`).

The user wants to build: $ARGUMENTS

Do exactly one phase, then stop and hand control back.

1. **Init the session (idempotent).** Derive a short `{slug}` ("Build a cart pricing
   engine" → `cart-pricing`).
   - `python3 $STATE init --feature {slug} --request "$ARGUMENTS"`
   - If it prints `RESUME`, the session exists — read `.sdlc/` and continue rather than
     re-initializing.
   - Create a branch if not on one: `git checkout -b stickshift/{slug}`.
2. **Write 3–5 acceptance criteria** in Given/When/Then form to `specs/{slug}-spec.md`,
   numbered AC-1, AC-2, … Keep it tight — a cold live build, not an exhaustive spec.
   Each criterion must be concrete and testable.
3. **Log any assumption you make** with `python3 $STATE decide --decision "..." --why
   "..."` (e.g. "discounts apply before tax"). Decide, don't ask.
4. **Record + commit:** `python3 $STATE transition SPEC --reason "wrote N criteria"`,
   then `git add -A && git commit -m "spec({slug}): N acceptance criteria"`.
5. **Stop. Hand control back.** End with the criteria, any decision logged, and one
   line: "Spec ready. Run `/plan` when you want me to decompose it — your call."

Do NOT start planning or coding. One phase per command.
