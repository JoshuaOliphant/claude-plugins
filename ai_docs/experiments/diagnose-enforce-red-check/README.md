# Does the stricter diagnose step 2 get a red check built first?

Context: #173 found that agents following `compost:diagnose` read step 2 ("build a feedback loop") and then went straight to reading code (0/20 red checks before the first edit, with and without the skill). Step 2 now ends with "Show the red before the first edit": the failing output goes where the user will see it before any edit, and a check that was only read or run against something else does not count. Step 9 asks for the same red output and the same command passing.

Rerun: the 10 seeded cross-module tasks of `../cross-module-diagnose`, same briefs, same grading, with the edited skill (`enforced` arm). One fresh Sonnet-class subagent per task.

| | skill (old) | no skill | skill (enforced) |
|---|---|---|---|
| hidden tests green (see Grading) | 10/10 | 9/10 | 9/10 |
| failing check run before the first edit | 0/10 | 0/10 | 10/10 |
| mean tool calls | 8.4 | 7.4 | 10.7 |
| mean call index of first edit | 5.5 | 4.8 | 7.0 |

- Red check: read from the transcripts. `results/process.txt` counts python or pytest runs before the first edit to `scripts/`; that regex missed two runs (c3 and c8 wrote the check as a heredoc script, so the file shows "exercised before edit 0" for c3 and an undercount for c8), which I read by hand. All 10 transcripts show the check failing on the reported symptom before the first edit. That the same command passes after the fix rests on each agent's own report for 9 of the 10; c8's after-fix re-run never ran (see below).
- The one miss, c3, rebuilt `personal_skills` from folders that contain a `SKILL.md`; the tests count any folder. Its 19 failing test ids are identical to `grade-base-c3.json` (the no-skill arm), so the miss is the same wrong fix and not caused by the change.
- Cost: about two more tool calls per task.
- c8 hit an auto-mode denial on its after-fix re-run, so its green after the fix rests on the hidden tests, not on its own check.

## Grading

Same rule as `../cross-module-diagnose`: restore the original tests over the agent's tree and run the suite. The task trees have no `.git`, so 7 tests fail in every run for environment reasons. The raw field `"green"` in each `results/grade-enforced-c*.json` is therefore `false` for all ten. Green here means no failure beyond those 7, i.e. subtract the set common to all runs: `new_failures` minus that set is empty for 9 runs, and 12 ids remain for c3 (the miss above).

Caveats: n=10, one sample per task, seeded mutants are blatant, tests were removed from the trees, and the briefs name the skill file, so this measures compliance when the skill is read, not whether it fires.
