# Test conventions: detect and adapt

Stick Shift runs in arbitrary projects, so it never hardcodes a test framework. The test
convention is decided **once per session** (at `/spec`), recorded in the session, and
honored by every later phase. The goal: each Given/When/Then criterion is backed by a
runnable test, so `/verify` proves the spec in code instead of by reading.

## Detection ladder (decide-log-proceed)

Run top to bottom; stop at the first match. Only the last rung asks a question.

1. **Adopt an existing pattern — no question.** Inspect the project for an established
   test style and reuse it exactly:
   - pytest-bdd: `pytest-bdd` in deps, or `*.feature` files + `@scenario`/step modules.
   - plain pytest: `test_*.py` / `*_test.py` under `tests/`.
   - unittest, jest/vitest (`*.test.ts`, `*.spec.ts`), go test (`*_test.go`),
     rspec (`*_spec.rb`), etc.
   If a convention is already in use, match it. This is the common case and the strongest
   signal — follow the surrounding code.

2. **No tests yet, but the stack is clear → default and log it — no question.** Pick the
   idiomatic default for the detected stack and record it with `python3 $STATE decide`:
   - Python (pyproject.toml / uv) → **pytest, with pytest-bdd as the BDD layer** for the
     Given/When/Then criteria.
   - JS/TS (package.json) → vitest or jest (whichever is already a dep; else vitest).
   - Go → `testing` (add a gherkin runner like godog only if the project signals BDD).
   - Ruby → RSpec.
   State it and proceed — "Detected a pytest project; expressing criteria as pytest-bdd
   scenarios — logged." No mid-flow setup prompt.

3. **Greenfield or genuinely ambiguous → ask, with a recommendation.** Only here. Offer
   the idiomatic default for whatever language the user names; let them confirm or
   override. A one-time setup question.

## Recording the convention (decide once, honor throughout)

When the convention is chosen, `/spec`:
- writes it into the spec header — `Test convention: <name>` in `specs/{slug}-spec.md`, and
- logs it — `python3 $STATE decide --decision "test convention: <name>" --why "<detected|defaulted|chosen>"`.

`/build` and `/verify` read the spec header to stay consistent. The convention is part of
the durable session, so it appears in `/journal`.

## Tying criteria to tests (executable compliance)

Each acceptance criterion AC-N maps to at least one runnable test, in the chosen
convention:
- **pytest-bdd:** a `Scenario` per criterion; the `.feature` Given/When/Then mirrors the
  spec AC. The scenario name or a tag references AC-N.
- **plain pytest / unittest:** name the test for the criterion — `test_ac1_*`,
  `test_ac2_*` — or mark it `@pytest.mark.ac(N)` if the project registers markers.
- **other frameworks:** the nearest equivalent (a `describe`/`it` block named for AC-N).

`/verify` then runs the suite and maps each AC-N to its test result — met only if its
test(s) pass. "Passing ≠ satisfied" becomes mechanical: every criterion has a green test
that proves it, and a criterion with no test is a gap, not a pass.
