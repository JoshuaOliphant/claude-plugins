---
name: spec
description: Stick Shift phase 1 — start a session from a task description OR an existing spec file, capture 3–5 Given/When/Then criteria, pick the test convention, and stop. You choose when to /plan.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
argument-hint: "<what to build, or a path to an existing spec/plan file>"
---

# /spec — define "done" before any code

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py` (run with `python3`).

Input: $ARGUMENTS — either a free-text task ("Build a cart pricing engine") or a path to
an existing spec/plan file (e.g. a `/blueprint` plan or a superpowers design doc).

Do exactly one phase, then stop and hand control back.

1. **Init / adopt the session.** Derive a short `{slug}`.
   - `python3 $STATE init --feature {slug} --request "<task, or 'spec: <path>'>"`
   - If it prints `RESUME`, a session already exists — read `.sdlc/`. If that session was
     driven by another harness (its `state.json` has `driver` of `auto`/`stop-hook`, i.e.
     autonomous-sdlc), run `python3 $STATE takeover` to stand its loop down so it won't
     fight your manual driving; narrate it ("found an autonomous session — taking the
     wheel, standing down the autopilot").
   - Create a branch if not on one: `git checkout -b stickshift/{slug}`.
2. **Capture the acceptance criteria** into `specs/{slug}-spec.md`, numbered AC-1, AC-2,
   … in Given/When/Then form. Branch on the input type:
   - **`$ARGUMENTS` is a path to an existing file** → read it and **extract/normalize**
     its criteria into testable AC. Upstream `/blueprint`/superpowers docs are usually
     design/plan prose, so distil them into concrete Given/When/Then. Add a
     `Source: <path>` header so provenance is explicit (point-in-time — don't try to
     re-sync). Derive `{slug}` from the file/content.
   - **`$ARGUMENTS` is a task description** → write 3–5 AC from it. Keep it tight — a cold
     live build, not an exhaustive spec.
   Either way, each criterion must be concrete and testable.
3. **Determine the test convention** (once per session) via the detection ladder in
   `${CLAUDE_PLUGIN_ROOT}/references/test-conventions.md`: adopt any existing test
   pattern; else default by stack (Python → pytest-bdd) and log it; ask only if the
   project is greenfield and ambiguous. Record it in the spec header
   (`Test convention: <name>`) and log it:
   `python3 $STATE decide --decision "test convention: <name>" --why "<detected|defaulted|chosen>"`.
4. **Log any other assumption you make** with `python3 $STATE decide --decision "..."
   --why "..."` (e.g. "discounts apply before tax"). Decide, don't ask.
5. **Record + commit:** `python3 $STATE transition SPEC --reason "wrote N criteria"`,
   then `git add -A && git commit -m "spec({slug}): N acceptance criteria"`.
6. **Stop. Hand control back.** End with the criteria, the source (if ingested), the test
   convention chosen, and one line: "Spec ready. Run `/plan` when you want me to
   decompose it — your call."

Do NOT start planning or coding. One phase per command.
