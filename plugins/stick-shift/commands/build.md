---
name: build
description: Stick Shift phase 3 — implement ONE task with TDD (red→green→refactor), then stop. Run once per task.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
argument-hint: "[task number or name, optional]"
---

# /build — one task, test-first

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

Implement exactly ONE task with TDD, then stop.

1. **Pick the task:** if $ARGUMENTS names one, use it; else take the next task from
   `specs/{slug}-plan.md`. Mark it in flight: `python3 $STATE task <id>`.
2. **RED:** write a failing test that pins the behavior. Run it; confirm it fails for
   the right reason.
3. **GREEN:** write the minimal code to pass. Run the test; confirm green.
4. **REFACTOR:** clean up while green. Run the full suite.
5. **Record + commit:** `python3 $STATE task <id> --done`, `python3 $STATE note-progress
   --what "<id> green"`, `python3 $STATE transition BUILD --reason "closed <id>, M left"`,
   then `git add -A && git commit -m "feat({slug}): <task>"`.
6. **Stop. Hand control back.** End with what you built, the test that proves it, and
   "Task done. `/build` the next one, or `/verify` when the tasks are complete — your
   call."

If you hit ambiguity, decide and log it (`python3 $STATE decide`). One task per command.
