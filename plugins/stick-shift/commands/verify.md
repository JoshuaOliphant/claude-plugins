---
name: verify
description: Stick Shift phase 4 — run the suite and confirm every acceptance criterion is backed by a passing test in the project's convention ("passing ≠ satisfied", in code), then stop.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
---

# /verify — prove the spec in code, not by reading

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

1. **Mechanical:** run the full test suite (e.g. `uv run pytest -q`) and the linters the
   project uses. Report the real result — never paper over a failure.
2. **Spec compliance, in code:** read the `Test convention:` from `specs/{slug}-spec.md`
   (see `${CLAUDE_PLUGIN_ROOT}/references/test-conventions.md`) and confirm **each**
   criterion AC-1, AC-2, … is backed by a **passing** test in that convention:
   - pytest-bdd → the AC's `Scenario` passed.
   - plain pytest / unittest → the AC's `test_acN_*` (or `@pytest.mark.ac(N)`) passed.
   - other frameworks → the AC's named test/block passed.
   Map every AC to its test result. A criterion with **no** test, or a **failing** one,
   is unmet — this makes "passing ≠ satisfied" mechanical, not a judgment call.
3. **Record + commit fixes:**
   - Every criterion has a passing test → `python3 $STATE transition DONE --reason "all
     N criteria proven"`.
   - Any criterion unmet or untested → `python3 $STATE transition BUILD --reason "AC-k
     untested/failing"` and name the gap so the next `/build` writes or fixes that test.
4. **Stop. Hand control back.** End with a per-criterion table (AC → test → met/unmet)
   and the next move. Optionally suggest the built-in `/code-review` skill before the
   close.

One phase per command.
