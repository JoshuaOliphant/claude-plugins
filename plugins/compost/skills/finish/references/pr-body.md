# PR body

The pull request is the record a reviewer audits. Every decision made without the user appears
here, with enough of the reason to judge it. Keep it factual: do not hide skipped validation,
unproven facts, or judgment calls.

```md
## Goal

<One or two sentences: what this change does for whom, in the domain's words. Link the issue.>

## Decisions

- <Ruling>: <why>. Cost if wrong: <what breaks or has to be redone>. (<link to the issue comment>)
- <Assumption taken instead of asking>: <why it was the careful reading>.

## Changes

- <Behavior that changed, not a file list. Name files only where a reviewer needs to look.>
- <What was removed or replaced, with no shim left behind.>

## Validation

- Suite: `<command>`: <N passed, 0 failed> on the branch, and <N passed> on the merge result
  with `<target>`.
- Gates: <each gate and its result>. Coverage <N>%<, with proposed exclusions listed under Risk>.
- Acceptance criteria:

  | AC | Test | Result |
  |---|---|---|
  | AC-1 | `tests/test_x.py::test_name[case-id]` | pass |

- Safety fact: <the one fact the change is safe because of>. Reached <rung>: <proof summary,
  or the script to re-run>.

## Risk

- <Anything unproven, with the rung it reached.>
- <Anything deferred, with the issue that tracks it.>
- <Coverage exclusions proposed and why the lines earn no test.>

Closes #<parent>, closes #<sub-issue>, closes #<sub-issue>
```

The `Closes` line names the parent issue and every sub-issue, so the merge closes all of them;
work with no parent closes its one issue.
Keep it when editing a body `compost:implement` already wrote.

Leave a section empty with "None." rather than deleting it, so a reviewer knows it was
considered.
