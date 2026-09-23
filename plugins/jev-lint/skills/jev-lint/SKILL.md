---
name: jev-lint
description: Use when the user asks to "lint comments", "find narrating comments", "check for silent failures", "semantic lint", "jev lint", "check code smells", "review this diff for workarounds or weakened tests", or before handing Python changes to review. Runs plain-language lint rules through TypeSafe's Jev and reports findings with the action each one needs. Requires TYPESAFE_API_KEY.
---

# jev-lint

Semantic lint for Python. `ast` and `tokenize` find the units (comments, except
handlers, functions, log calls, diff hunks); Jev answers one question per rule about
each unit; findings at or above each rule's threshold are reported.

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev_lint.py path/to/code            # whole tree
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev_lint.py --diff origin/main      # hunks of a branch
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev_lint.py src --rules comment-kind,silent-failure
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev_lint.py src --json              # every judgment
```

Exit codes: 0 clean, 1 findings, 2 Jev failed for at least one unit, 3
`TYPESAFE_API_KEY` not set, 4 bad input (missing path, git diff failure, unreadable
files, or nothing to lint). Codes 2 and 4 mean the run was incomplete, not clean:
say so rather than reporting the findings as the whole picture.

## Acting on findings

Each finding line names its label and the action:

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

Findings tagged `[ruff: CODE]` are syntactic: the summary lists ruff rules that catch
them deterministically. Enable those in `[tool.ruff.lint] extend-select` so Jev spends
its judgments only on what needs meaning.

Probabilities are judgments, not proof. Read the flagged code before changing it,
especially near a rule's threshold.
