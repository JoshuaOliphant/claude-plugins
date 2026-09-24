# Jev calls in verify

Three checks in verify go to Jev first: whether a coverage gap is worth a test, whether each
acceptance criterion's test asserts its Then, and whether the report's claims are backed by the
output you captured. Jev is a typed model that answers in a second or two for a fraction of a cent.
Write the input JSON to a temp file and run:

```sh
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py <tool> --input <file>
```

Exit 0 prints the judgment as JSON. Exit 2 means the input is malformed: fix it. Exit 3 means Jev
is unavailable (no key, or the API failed): do the check by hand as the step describes. Jev grades
what you hand it and never writes the report; the raw probability or score sits beside each
decision so you can overrule it out loud.

## test-value (step 3)

Input: the repo root and either the coverage report (`coverage json -o coverage.json`, or
`pytest --cov-report=json`) or explicit lines. Consecutive missing lines become one block, shown to
Jev with four lines of context and the definition that holds them.

```json
{"repo": ".", "coverage": "coverage.json"}
{"repo": ".", "uncovered": [{"file": "scripts/pile.py", "lines": [208, 209]}]}
```

Output: `score` runs from 0 (a test would prove nothing: a `__main__` guard, a constant, an
exception class, a framework hand-off) to 3 (it guards behavior a user depends on). Below 1.5 the
`decision` is `exclude`, and `exclude` lists those blocks as `file:first-last`: that is the proposed
exclusion to bring to the user. Every `test` block goes back to `compost:build`.

```json
{"blocks": [
  {"file": "scripts/pile.py", "lines": [208, 209], "decision": "exclude", "score": 0.03,
   "probabilities": {"0": "...one per level"}},
  {"file": "scripts/pile.py", "lines": [153, 153], "decision": "test", "score": 2.12,
   "probabilities": {"0": "..."}}],
 "exclude": ["scripts/pile.py:208-209"]}
```

Measured on 24 real blocks from compost and skill-atlas: every block sorted right at 1.5, with no
block between 1.24 and 2.02.

## ac-exercised (step 4)

Input: the repo root and the AC table, each AC-N with its Given/When/Then and the node id of its
test, parametrized case included when a row stands for it.

```json
{"repo": ".", "criteria": [
  {"id": "AC-2", "text": "Given a token whose expires_at is exactly now, When it is authorized, Then the decision is Denied(\"expired\").",
   "test": "tests/test_auth.py::test_authorize_denies[expired-at-exact-instant]"}]}
```

Output: `exercised` per criterion, with Jev's `probability` that the test's assertions check the
Then (true at 0.5 or more). `to_read` lists the criteria to read yourself: every one Jev doubts, and
every one whose node id matched no test (`probability: null`). A criterion you confirm unmet goes
back to `compost:build`.

```json
{"criteria": [{"id": "AC-2", "test": "tests/test_auth.py::test_authorize_denies[expired-at-exact-instant]",
               "exercised": true, "probability": 0.85}],
 "to_read": []}
```

Measured on 22 labeled pairs: 20 right. The misses were a test whose constant hid the environment
variable the criterion named, and a mock-based test of a nearby expiry instead of the exact one.

## claim-backed (step 8)

Input: each claim the report will make, with the output of the command that backs it, inline or
as a file you saved with `| tee`. Long output is clipped to its first 2,000 and last 8,000
characters, where the summary lines sit.

```json
{"claims": [
  {"claim": "154 passed, coverage 100%", "output_file": "/tmp/verify-pytest.txt"},
  {"claim": "ruff clean", "output": "All checks passed!\n"}]}
```

Output: `backed` per claim with Jev's `probability` (true at 0.5 or more); `unbacked` lists the
claims to fix or drop before you say done.

```json
{"claims": [{"claim": "154 passed, coverage 100%", "backed": false, "probability": 0.08},
            {"claim": "ruff clean", "backed": true, "probability": 0.65}],
 "unbacked": ["154 passed, coverage 100%"]}
```

Measured on 22 claims over real pytest, ruff, node, and build output: all 22 right at 0.5.
