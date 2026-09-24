# Jev calls in build

Two judgments in build go to Jev first: where each acceptance criterion's test belongs, and whether
a test you added re-covers one that already exists. Jev is a typed model that answers in a second
or two for a fraction of a cent. Write the input JSON to a temp file and run:

```sh
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py <tool> --input <file>
```

Exit 0 prints the judgment as JSON. Exit 2 means the input is malformed: fix it. Exit 3 means Jev
is unavailable (no key, or the API failed): do the step by hand as the step describes. Jev only
picks among tests the code lists and checks pairs the code chose; you still write every test, and
the raw probabilities sit beside each decision so you can overrule it out loud.

## find-test (step 4, and diagnose step 7)

Input: the repo root (node ids come back relative to it) and one criterion per AC-N, with its
Given/When/Then. Python and JS/TS tests are found by name, so no test runner is needed.

```json
{"repo": ".",
 "criteria": ["AC-2: Given pile.toml names a source whose license is empty, When pile.py loads it, Then it fails naming the license field.",
              "AC-3: Given a pile.toml source with role vendored, When pile.py loads it, Then it fails listing the allowed roles."]}
```

Output: one placement per criterion. `action: "extend"` means the chosen test already exercises the
behavior (rule 1 or 2 of step 4: change its expectation or add its row). `"add-beside"` means write
the new case next to `test`, on its fixtures (rule 2 or 3). `covered` is Jev's probability that
`test` already exercises the criterion; code extends at 0.7 or more. `alternatives` are the next
two candidates when `test` looks wrong to you.

```json
{"placements": [
  {"criterion": "AC-2: ...license is empty...", "action": "add-beside",
   "test": "tests/test_pile.py::test_load_names_what_is_wrong_with_the_file", "confidence": 0.88, "covered": 0.06,
   "alternatives": ["tests/test_pile.py::test_load_reads_sources_with_their_feeds", "..."]},
  {"criterion": "AC-3: ...role vendored...", "action": "extend",
   "test": "tests/test_pile.py::test_load_names_what_is_wrong_with_the_file", "confidence": 0.97, "covered": 0.88,
   "alternatives": ["..."]}]}
```

Here AC-2 is a new row in that parametrized table and AC-3 is already one of its rows. Measured on
34 criteria over skill-atlas's and compost's suites: the right test first for 33, in the top three
for all 34, and the extend call right for 33.

## duplicate-test (step 10, before committing)

Input: the repo root and the base ref the change started from. Every test added or changed since
`base` (working tree included) is paired with its five nearest tests by shared words, and Jev
judges each pair.

```json
{"repo": ".", "base": "main"}
```

Output: per added or changed test, `recommendation` is `"keep"` or `"fold into <node id>"`, with
the pairs at or above 0.5 in `duplicates` and all five in `neighbours`.

```json
{"base": "main", "tests": [
  {"test": "tests/test_pile.py::test_role_outside_the_allowed_set_is_rejected", "status": "added",
   "recommendation": "fold into tests/test_pile.py::test_load_names_what_is_wrong_with_the_file",
   "duplicates": [{"test": "tests/test_pile.py::test_load_names_what_is_wrong_with_the_file",
                   "same_behavior": 0.78, "similarity": 0.41}],
   "neighbours": ["...five pairs..."]}]}
```

Fold each flagged test into the named one as a row or an assertion, then delete it; a recommendation
you disagree with gets one line in the commit message saying why the test stays. Measured on 23
labeled pairs (10 duplicates, 13 near neighbours that test something else): all 23 right at 0.5.
