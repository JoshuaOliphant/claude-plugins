# jev-lint

A semantic linter for Python. Rules are plain-language questions answered by
[TypeSafe](https://docs.typesafe.ai)'s Jev, a model that returns typed judgments and
probabilities instead of generated text. `ast` and `tokenize` pick out the units to
judge; code turns each answer into a finding.

Requires `TYPESAFE_API_KEY`.

```bash
uv run scripts/jev_lint.py [PATH ...] [--diff REF] [--rules id,id] [--threshold P]
                           [--concurrency N] [--json]
```

Exit codes: 0 no findings, 1 findings reported, 2 Jev failed for at least one unit,
3 skipped because `TYPESAFE_API_KEY` is not set, 4 bad input (missing path, git diff
failure, unreadable files, or nothing to lint).

## Rules

| Rule | Unit | Question | Default threshold |
|---|---|---|---|
| `comment-kind` | comment block | Choice: why / todo / narrates / section_banner / commented_out_code / change_history / misleading / belongs_in_docs | 0.5 |
| `silent-failure` | except clause | Does it hide a failure that matters from callers? | 0.7 |
| `io-mixed-with-logic` | function | Does it both do I/O and hold testable domain logic? | 0.7 |
| `name-hides-side-effects` | function | Does it do something significant its name does not announce? | 0.5 |
| `docstring-quality` | function with docstring | Choice: accurate / restates_name / contradicts / omits_surprise | 0.7 |
| `log-exposure` | logger call | Choice: harmless / secret / personal_data / financial | 0.5 |
| `test-smell` | `test_*` function | Choice: meaningful / smoke / tautology / mocks_unit_under_test / overclaims / no_real_assertion | 0.7 |
| `symptom-workaround` | diff hunk | Does the change hide a symptom instead of fixing its cause? | 0.5 |
| `test-weakening` | diff hunk in a test file | Does the change weaken the tests? | 0.5 |

`silent-failure` follows a strict policy: best-effort cleanup and silent fallbacks to a
substitute resource count as hiding a failure; a documented sentinel the caller must
check, and an exception that is itself the expected answer, do not.

Choice rules flag on the probability mass outside their acceptable labels, so a
comment split between "why" and "narrates" still surfaces. Findings whose pattern is
purely syntactic also name the ruff rule that catches them (`ERA001` for commented-out
code; `E722`, `BLE001`, `S110`, `S112` for bare or broad handlers), and the report ends
with the ruff rules worth enabling.

## Measured

All numbers are from the live API (`jev-1.13.0`), at each rule's default threshold,
against samples a reviewer labeled without seeing Jev's answers.

| Rule | Precision / recall | Sample |
|---|---|---|
| `comment-kind` | 1.00 / 0.86 | 20 comments from this repo; separately, 88% of 65 comments deleted by real cleanup commits are caught |
| `silent-failure` | 0.86 / 0.90 | 50 except clauses across 20 repositories |
| `name-hides-side-effects` | 0.86 / 0.86 | 50 functions across 20 repositories, but tuned on that sample, so treat as optimistic |
| `io-mixed-with-logic` | 1.00 / 0.83 | 20 functions from this repo |
| `docstring-quality` | 0.90 / 0.82 | 20 docstrings from this repo |
| `test-smell` | no false alarms on 11 real tests | recall unmeasured: the sample held no real smells |
| `log-exposure`, `symptom-workaround`, `test-weakening` | not measured on real code | 100% on 5–6 synthetic cases each |

This repository (615 units, 1,288 judgments) lints in about 7 seconds; 1,790 files
across 20 repositories took 227 seconds, roughly 95 judgments a second at the default
concurrency of 16.

`evals/run_eval.py` scores the labeled cases in `evals/cases.py`; pass a JSONL of
comments that cleanup commits deleted to score comment recall as well.

Two lessons from tuning, both decided by measurement rather than argument:

- A `vendor-leak` rule was removed. On clean code it flagged 8 of 16 functions, because
  a snippet cannot show whether a class is the project's own wrapper or a vendor type.
- `silent-failure` asks whether a failure "that matters" is hidden. Dropping that phrase
  to match the stricter criteria read better but measured worse (0.75 precision against
  0.86, stable across repeated runs), so the phrase stays.
