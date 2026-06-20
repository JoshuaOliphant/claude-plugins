---
name: plan
description: Stick Shift phase 2 — decompose the spec into a short task list, log key decisions, and stop. You choose when to /build.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
---

# /plan — decompose and decide

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

Do exactly one phase, then stop.

1. **Orient:** `python3 $STATE status`; read `specs/{slug}-spec.md`.
2. **Decompose** into 3–4 right-sized tasks (each TDD-able in a few minutes). Write them
   to `specs/{slug}-plan.md` as a numbered list with a one-line purpose each, noting
   which acceptance criteria each task covers.
3. **Log the load-bearing design decisions** with `python3 $STATE decide` (e.g. "Decimal
   not float for money / exact rounding"). These are your judgment beats — make them
   explicit.
4. **Record + commit:** `python3 $STATE transition PLAN --reason "N tasks"`, then
   `git add -A && git commit -m "plan({slug}): N tasks"`.
5. **Stop. Hand control back.** End with the task list and a recommendation: "N tasks
   ready; I'd start with <task> because <reason> — your call. Run `/build`."

Do NOT start coding. One phase per command.
