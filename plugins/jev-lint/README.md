# jev-lint

A semantic linter for Python. Rules are plain-language questions answered by
[TypeSafe](https://docs.typesafe.ai)'s Jev, a model that returns typed judgments and
probabilities instead of generated text. `ast` and `tokenize` pick out the units to
judge; code turns each answer into a finding.

Requires `TYPESAFE_API_KEY`. Runs with `uv run scripts/jev_lint.py [PATH ...] [--diff REF]`.

## Rules

| Rule | Unit | Question | Default threshold |
|---|---|---|---|
| `comment-kind` | comment block | Choice: why / todo / narrates / section_banner / commented_out_code / change_history / misleading / belongs_in_docs | 0.5 |
| `silent-failure` | except clause | Does it hide a failure that matters from callers? | 0.5 |
| `io-mixed-with-logic` | function | Does it both do I/O and hold testable domain logic? | 0.7 |
| `name-hides-side-effects` | function | Does it do something significant its name does not announce? | 0.7 |
| `docstring-quality` | function with docstring | Choice: accurate / restates_name / contradicts / omits_surprise | 0.7 |
| `log-exposure` | logger call | Choice: harmless / secret / personal_data / financial | 0.5 |
| `test-smell` | `test_*` function | Choice: meaningful / smoke / tautology / mocks_unit_under_test / overclaims / no_real_assertion | 0.7 |
| `symptom-workaround` | diff hunk | Does the change hide a symptom instead of fixing its cause? | 0.5 |
| `test-weakening` | diff hunk in a test file | Does the change weaken the tests? | 0.5 |

Choice rules flag on the probability mass outside their acceptable labels, so a
comment split between "why" and "narrates" still surfaces. Findings whose pattern is
purely syntactic also name the ruff rule that catches them (`ERA001`, `E722`,
`BLE001`, `S110`, `S112`), and the report ends with the ruff rules worth enabling.

## Measured

All numbers are from the live API (`jev-1.13.0`), at each rule's default threshold.

| Rule | Blind-labeled repo sample: precision / recall | Other evidence |
|---|---|---|
| `comment-kind` | 1.00 / 0.86 (20 items) | catches 86% of 65 comments deleted in real cleanup commits |
| `io-mixed-with-logic` | 1.00 / 0.83 (20 items) | |
| `docstring-quality` | 0.90 / 0.82 (20 items) | |
| `silent-failure` | 0.60 / 1.00 (20 items) | labeler was lenient on bare `except: pass`; see notes |
| `name-hides-side-effects` | 1.00 / 1.00 (20 items, only 2 positives) | was 0.17 precision before naming conventions entered the criteria |
| `test-smell` | no false alarms on 11 real tests | 4/4 on synthetic smells |
| `log-exposure`, `symptom-workaround`, `test-weakening` | not measured on real code yet | 100% on 5–6 synthetic cases each |

The whole repository (37 files, 589 units, 1,211 judgments) lints in about 6 seconds.
`evals/run_eval.py` replays the labeled cases; pass a JSONL of comments that cleanup
commits deleted to score comment recall.

A `vendor-leak` rule was tried and removed: on clean code it flagged 8 of 16 functions,
because a snippet cannot show whether a class is the project's own wrapper or a
third-party type.
