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
