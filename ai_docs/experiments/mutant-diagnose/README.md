# Mutants as diagnose tasks (PoC for #114)

Inject known defects into a green module, hand an agent only the symptom, and grade by whether the module's own tests go green again. The ground truth is the mutation, so no judge is needed. Compared `compost:diagnose` against no skill on the same trees.

Reference material only, not a shipped tool. Sibling experiments: `../judge-mutation/`, `../skill-mutation/`.

## Result

| round | tasks | what the agent got | hidden suite green, skill | hidden suite green, no skill |
|---|---|---|---|---|
| 1 | 10 mutants of `stop_guard.py`, one each | the failing test output, tests visible | 10/10 | 10/10 |
| 2 | 10 trees, two mutants each, in `claude_config.py` and `skill_drift.py` | a user-level bug report, tests removed | 7/10 | 8/10 |

Mean cost in round 2: skill 9.4 tool calls and about 91k tokens, no skill 7.4 and about 85k. Round 1: 7.0 against 4.8 calls.

- Round 1 is a ceiling: a one-token mutant with the failing test in hand is a one-hop trace.
- Round 2 failures (t6, t7 in both arms; t1 in the skill arm) trace to the bug reports, which were written from the failing tests and described one of the two defects. Neither arm could find a defect nobody reported. They say nothing about the skill.
- Check each report against the ground-truth mutants before running agents; this round did not.
- Operator mutants are mostly an inverted condition or a deleted statement. They do not produce causes far from the symptom, which is where a method like diagnose should help.
- Jev as a mutant-realism filter (a Noul for plausibility, a Choice for crash or wrong logic) was weak: scores sat at 0.5 to 0.68, `is` swaps on string literals ranked highest, and the failure-mode Choice mislabeled 8 of the 19 mutants that really crashed. Operator class plus the observed failure type worked better.

## Run it

From a checkout, with the compost venv (`uv sync` in `plugins/compost`) and `MUTANT_WORK` pointing at a scratch directory:

```bash
export MUTANT_WORK=/tmp/mutant-diagnose COMPOST=plugins/compost; mkdir -p $MUTANT_WORK
cd plugins/compost
uv run --with cosmic-ray python ../../ai_docs/experiments/mutant-diagnose/scripts/gen2.py scripts/skill_drift.py tests/test_skill_drift.py  # every mutant the tests kill
uv run --with cosmic-ray python ../../ai_docs/experiments/mutant-diagnose/scripts/mk2.py     # pairs them into trees with the tests removed
```

`gen.py`, `mk.py` and `grade.py` are the round 1 versions (one mutant, tests visible); `gen2.py`, `mk2.py` and `grade2.py` are round 2. `realism.py` is the Jev filter. `mk2.py` names its two modules in a loop and leaves the bug reports to you (round 2 had a Haiku agent write them from the failing output; its output is `results/symptoms-round2.json`).

Then give each tree to two agents, one told to read `skills/diagnose/SKILL.md` and one not, and run `grade2.py`, which copies the real tests over each tree and reports whether the suite is green and the mutated lines are fixed. Green is the primary check; many correct fixes differ from the original text.

## Next

Build the tasks from real past fix commits in claude-plugins' history instead, where the symptom is the actual issue text and the cause is rarely a one-token flip.
