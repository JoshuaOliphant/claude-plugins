# jev-lint

Semantic lint for Python, used in verify's comment check (step 8) and whenever someone asks to
find narrating comments, silent failures, or weakened tests. `ast` and `tokenize` find the units
(comments, except handlers, functions, log calls, diff hunks); Jev answers one plain-language
question per rule about each unit; findings at or above each rule's threshold are reported.

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/lint/jev_lint.py --diff <base>        # hunks and files of the branch
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/lint/jev_lint.py path/to/code          # a whole tree
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/lint/jev_lint.py src --rules comment-kind,silent-failure
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/lint/jev_lint.py src --json            # every judgment
```

It finds the TypeSafe key the same way `jev.py` does (`TYPESAFE_API_KEY`, then the Keychain item
`typesafe`). Exit codes: 0 clean, 1 findings, 2 Jev failed for at least one unit, 3 no key found (or, run with plain
`python3`, no uv that can install typesafe-sdk),
4 bad input (missing path, git diff failure, unreadable files, or nothing to lint). Codes 2 and 4
mean the run was incomplete, not clean: say so rather than reporting the findings as the whole
picture. Code 3 means do the pass by hand.

## Acting on findings

| Label | Action |
|---|---|
| `comment-kind [narrates]`, `[section_banner]`, `[commented_out_code]` | delete the comment |
| `comment-kind [change_history]` | delete it; the history belongs in the commit message |
| `comment-kind [belongs_in_docs]` | move the text to the README or docs, then delete it |
| `comment-kind [misleading]` | fix the comment or the code so they agree |
| `docstring-quality [restates_name]` | delete or rewrite with what the name cannot say |
| `docstring-quality [omits_surprise]`, `[contradicts]` | fix the docstring |
| `silent-failure` | re-raise, raise a domain error, report it at error level, or return a sentinel the docstring promises |
| `log-exposure [secret]`, `[personal_data]`, `[financial]` | remove or redact the value from the log call |
| `io-mixed-with-logic` | pull the decisions into a pure function; keep I/O at the edge |
| `name-hides-side-effects` | rename to announce the effect, or move the effect out |
| `test-smell`, `test-weakening` | make the test able to fail when the behavior breaks |
| `symptom-workaround` | find and fix the cause instead |

Findings tagged `[ruff: CODE]` are syntactic, and the report ends with the ruff rules that catch
them deterministically (`ERA001` for commented-out code; `E722`, `BLE001`, `S110`, `S112` for bare
or broad handlers). Recommend enabling those in `[tool.ruff.lint] extend-select` so Jev spends its
judgments only on what needs meaning.

Probabilities are judgments, not proof. Read the flagged code before changing it, especially near
a rule's threshold.

## Rules and how well they hold

Measured on the live API at each rule's default threshold, against samples labeled without seeing
Jev's answers. Rules marked "tuned" were tuned on the sample they are measured on, so treat those
numbers as upper bounds.

| Rule | Unit | Threshold | Precision / recall |
|---|---|---|---|
| `comment-kind` | comment block | 0.5 | 1.00 / 0.86 (20); 88% of 65 comments real cleanups deleted |
| `silent-failure` | except clause | 0.7 | 0.86 / 0.90 (50, across 20 repos) |
| `io-mixed-with-logic` | function | 0.7 | 1.00 / 0.83 (20) |
| `name-hides-side-effects` | function | 0.5 | 0.86 / 0.86 (50, tuned) |
| `docstring-quality` | function with a docstring | 0.7 | 0.90 / 0.82 (20) |
| `log-exposure` | logger call | 0.5 | 0.93 / 0.93 (30) |
| `test-smell` | `test_*` function | 0.7 | no false alarms on 11 real tests; recall unmeasured |
| `symptom-workaround` | diff hunk | 0.7 | 1.00 / 0.67 (30, tuned) |
| `test-weakening` | diff hunk in a test file | 0.7 | 1.00 / 0.89 (30, tuned) |

`silent-failure` is strict: best-effort cleanup and silent fallbacks to a substitute resource count
as hiding a failure; a documented sentinel the caller must check, and an exception that is itself
the expected answer, do not.

`scripts/lint/run_eval.py` re-scores the labeled cases in `scripts/lint/cases.py` against the live
API; pass a JSONL of comments that cleanup commits deleted to score comment recall as well.
