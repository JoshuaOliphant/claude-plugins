# Diagnose on real fix commits (#169)

Does `skills/diagnose` beat an unguided agent when the bug is a real one? The mutant pilot (`../mutant-diagnose`) hit a
ceiling: both arms fixed nearly everything, and the bug reports there were written by a model from a mutant.

Here the task is a past fix commit in this repo. The tree is the commit's parent (plugin source only, no history, no
skills directory). The symptom is written by hand from the commit message and the commit's test, then checked against the
real diff. The grader is the commit's own tests, laid over the agent's tree after it finishes.

## Results (10 tasks, Sonnet 5.5 subagents, one run per cell)

| | skill | no skill |
|---|---|---|
| hidden tests green | 9/10 | 10/10 |
| regressions in the rest of the suite | 0 | 0 |
| tool calls per task (mean) | 10.5 | 8.9 |
| tokens per task (mean) | 76.6k | 73.0k |

The one red cell is t10 with the skill. The fix swapped lint's cache for one that never stores anything. The real fix
gives each eval run a fresh temporary cache. With no cache at all, the same question inside one run goes to the API
twice, and the hidden test counts calls (4, expected 2). The no-skill arm used a per-run cache and passed.
Nothing about this separates the arms: it is one design choice in one task.

Both arms found the same root cause in all ten tasks, usually the same one-file fix. Two agents (t1, t4) said the old
tests pin the old behaviour, which is right: the fix commits changed them.

## What this says

On small, well-specified bugs with a regression test to run, diagnose does not improve the outcome and costs about one
more tool call and 3.6k tokens per task. This is the same answer as the mutant pilot, now on real bugs with human-written
symptoms. A pilot of one run per cell cannot detect a small effect; it rules out a large one.

Where the skill's discipline could matter is untested here: bugs with no failing test to run, or symptoms that point away
from the cause. The agents mostly did not build a red repro first even with the skill (several said so), so the skill's
central step was often skipped. A follow-up could grade whether the repro was built, not only whether the tests go green.

## Run it

```
REPO=. PLUGIN=plugins/compost PY=plugins/compost/.venv/bin/python python3 select_fixes.py origin/main
python3 build_tasks.py                  # uses symptoms.json beside it
python3 grade.py t8 /path/to/agent/tree # JSON: green flag, failures, files changed
```

`select_fixes.py` keeps fix commits whose tests fail on the parent and pass on the commit (27 here, in
`results/candidates.json`). `symptoms.json` holds the ten hand-written bug reports. In `results/grades.json` the rows are
`[task, arm, green, regressions, files changed]`. Failures that fail in every tree (git and link checks that need a
checkout) are environmental and not counted.

## No-tests variant (#171)

Same ten tasks, with `tests/` removed from the agent's tree so there is nothing to run and the agent must build its own
check (`build_notests.py`; `grade.py` puts the suite back before grading). `repro_before_edit.py` reads each run's
transcript and counts commands that exercised the code before the first edit to `scripts/`.

| | skill | no skill |
|---|---|---|
| hidden tests green | 9/10 | 9/10 |
| ran something that exercised the bug before editing | 1/10 | 0/10 |
| tool calls per task (mean) | 9.4 | 6.9 |
| tokens per task (mean) | 75.2k | 69.6k |

The red cell is t10 in both arms: each replaced lint's cache with one that stores nothing, and the hidden test counts
API calls (see above). Outcome is at the ceiling again, with no tests to run.

All ten skill-arm agents read `SKILL.md`, whose step 2 says to build a red-capable check before forming a theory. Nine
edited the code first and checked afterwards (most said so in their report). The one exception, t9, ran `jev.py status`
with a bad proxy, saw "jev ready", and then patched. The skill costs about 2.5 more tool calls and 5.6k tokens per task
here, and for these bugs it did not change the order of work.

Caveats: the symptoms name the failing behavior closely, so reading the code finds the cause without a repro; this is
why the skipped step did no harm. The process measure is a heuristic over transcripts (a command that mutates and
exercises in one call counts as an edit). Per-run grades are in `results/skill-nt-t*.json` and `results/base-nt-t*.json`.

## No-tests variant with the current skill text (#171, rerun 2026-10-20)

The table above ran against the skill before step 2 gained "Show the red before the first edit" (`7848916`,
validated on seeded bugs in `../diagnose-enforce-red-check`). Rerun: the same ten no-tests tasks, a fresh Sonnet 5.5
subagent per task, briefs unchanged (`ARMS=enforced build_notests.py`), the skill as it is on main. Old-text and
no-skill rows are from the table above.

| | skill (old text) | no skill | skill (current text) |
|---|---|---|---|
| hidden tests green | 9/10 | 9/10 | 9/10 |
| failing check run on the reported symptom before the first edit | 1/10 | 0/10 | 9/10 |
| tool calls per task (mean) | 9.4 | 6.9 | 10.1 |
| tokens per task (mean) | 75.2k | 69.6k | 66.7k |

- Red-before-edit is read by hand from the transcripts. `repro_before_edit.py` reports 5/10 because it misses checks
  written as a heredoc script; the by-hand reading finds red output on the symptom before the first edit in t1, t2, t3,
  t4, t5, t7, t8, t9, t10. The exception is t6: it edited `stop_guard.py` at its fourth call and wrote its check
  afterwards, and its report says the "show the red first" step was skipped. It was green anyway.
- t9's red is the status command itself printing "jev ready" with a key and a bad proxy, which is the report's symptom.
  In the other eight the red is the agent's own throwaway script.
- The one red cell is t10 again, in all three arms: the fix swaps the shared cache for one that stores nothing, and the
  hidden test wants a fresh per-run cache. That agent did build a red check first (a second run answered from cache);
  the check was right about the bug and silent about the design. The same two `test_jev_meta` ids fail in t3 in every
  arm; they need a git checkout and are environmental.
- Cost: about 3 more tool calls per task than no skill. Token counts are the harness's per-subagent totals and are not
  comparable to within a few thousand; the skill arm was not more expensive in tokens this time.

Caveats: n=10 and one run per cell. The briefs name the skill file, so this measures compliance when the skill is read,
not whether it fires. The symptoms are specific enough that reading finds the cause, so outcome stays at the ceiling in
every arm and cannot separate them. t1, t7 and t8 picked the same scratch directory and ran in parallel, so one removed
another's files; their trees were unaffected, but their intermediate outputs are not independent. Per-run grades are in
`results/enforced-nt-t*.json`.
