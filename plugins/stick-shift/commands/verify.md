---
name: verify
description: Stick Shift phase 4 — run the suite + the project's own checks, prove every acceptance criterion is backed by a passing test, apply pertinent review skills, then stop.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
---

# /verify — prove the spec in code, not by reading

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

1. **Mechanical + project checks:** run the full test suite (e.g. `uv run pytest -q`) and
   the project's own gates it already exposes — linters, type checkers, `make`/`just`
   targets, `scripts/*verify*`, `pre-commit`, `package.json` scripts (see
   `${CLAUDE_PLUGIN_ROOT}/references/validations.md`). Report real results — never paper
   over a failure.
2. **Spec compliance, in code:** read the `Test convention:` from `specs/{slug}-spec.md`
   (see `${CLAUDE_PLUGIN_ROOT}/references/test-conventions.md`) and confirm **each**
   criterion AC-1, AC-2, … is backed by a **passing** test in that convention:
   - pytest-bdd → the AC's `Scenario` passed.
   - plain pytest / unittest → the AC's `test_acN_*` (or `@pytest.mark.ac(N)`) passed.
   - other frameworks → the AC's named test/block passed.
   Map every AC to its test result. A criterion with **no** test, or a **failing** one,
   is unmet — this makes "passing ≠ satisfied" mechanical, not a judgment call.
3. **Apply pertinent verification skills (decide-log-proceed).** Consider the review/
   quality skills installed and run those pertinent to *these* changes — without asking
   first; log what you ran with `python3 $STATE note-progress`. `/code-review` for
   correctness, `vet` for a diff review, `security-review` when the change touches a
   security surface; `/simplify` is fine too but it **mutates code**, so run it only after
   the above is green and re-run the gates after (revert it if it broke something). Bring
   a finding to the user only when it genuinely needs their call. See
   `${CLAUDE_PLUGIN_ROOT}/references/validations.md`.
4. **Record + commit fixes:**
   - Every criterion has a passing test and the checks are clean → `python3 $STATE
     transition DONE --reason "all N criteria proven"`.
   - Any criterion unmet/untested, or a check failing → `python3 $STATE transition BUILD
     --reason "<gap>"` and name it so the next `/build` fixes it.
5. **Stop. Hand control back.** End with a per-criterion table (AC → test → met/unmet),
   the extra checks/skills you ran, and the next move.

One phase per command.
