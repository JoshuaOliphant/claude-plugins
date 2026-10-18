# Seeded cross-module diagnose (#173, part of #114)

Question: does the diagnose skill change outcomes when the symptom is reported at a caller but the cause sits in a shared helper module? The earlier pilots (`../mutant-diagnose`, `../real-fix-diagnose`) were at the ceiling, and history holds too few non-obvious fixes to build a harder set, so the tasks here are seeded.

## Design

- `gen.py` mutates a helper module of compost's scripts (cosmic-ray operators plus thin's own) and keeps only mutants that a *different* module's tests kill. `tasks.json` holds the 10 chosen (c1 to c10); `build.py` builds the trees with the tests removed.
- `symptoms.json`: one hand-written symptom per task, phrased at the caller (for example "every Score reads 0.0", "the stop guard crashes with KeyError 'message'"). The helper is never named.
- Two arms, 10 tasks each, one fresh Sonnet-class subagent per run: `skill` (told to follow `plugins/compost/skills/diagnose/SKILL.md`) and `base` (same brief, no skill). `prepare_runs.py` writes the briefs.
- Grade 1, `grade.py`: put the original tests back over the agent's tree and run the whole suite. Green means no failure beyond the environment's (there is no `.git`, so 7 gather and plugin-layout tests fail in every run, including untouched ones).
- Grade 2, `repro_before_edit.py`: from each transcript, count python or pytest runs before the first mutating call to `scripts/`. I then read the commands for the two non-zero cases by hand.

## Results

| | skill | base |
|---|---|---|
| hidden tests green | 10/10 | 9/10 |
| cause found in the helper, not the named caller | 10/10 | 10/10 |
| red check built before first edit (read by hand) | 0/10 | 0/10 |
| mean tool calls | 8.4 | 7.4 |
| mean call index of first edit | 5.5 | 4.8 |

Per-run grades are in `results/grade-<arm>-cN.json` (`new_failures` there still includes the 7 environment failures; subtract the set common to all 20 runs) and `results/process.txt`.

The one miss: base c3 (`Config.personal` returned `set()`). It rebuilt the set from `*/SKILL.md` globs; the skill arm listed directories. The tests treat a skill directory without a `SKILL.md` as a personal skill, so the base fix broke 12 `test_a_malformed_marketplace_catalog...` cases.

The two runs with a non-zero count before the first edit (base c7, skill c7) were inspecting the SDK's `ScoreAnswer` fields. Neither exercised the reported symptom, so neither counts as a red check.

## What this says

- Both arms locate the cause in the helper. The symptom-to-helper hop is easy for these mutants because each is a stub or inverted condition, and a grep for the symptom's key term lands on it. 19/20 green is a ceiling again.
- The skill's step 2 (build a red-capable check first) is not followed: 0/10, against 1/10 in the no-tests variant of #171. The skill arm reads it and still goes straight to reading code.
- The skill costs about one tool call more per task and delivers no measurable gain in these tasks. One miss in 20 is not a difference.
- Several agents noted the suite was removed, so the missing red check may be partly the task setup: the only red check available was one they had to write from nothing. #171 had the same property.

## Caveats

- Seeded mutants are blatant (stubs, inverted filters). Real cross-module bugs are subtler.
- n=10 per arm, one sample per task, no repeat runs.
- Mean call counts come from transcripts; token counts are not reported here.
- Tasks come from compost's own scripts, which agents may know from training.
- Jev as a root-cause grader is still untested.
