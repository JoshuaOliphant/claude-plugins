# Subtle-mutant diagnose (#173, follow-up to ../cross-module-diagnose)

Question: when the seeded bug is a changed constant, boundary, operator or argument instead of a stub or inverted condition, does the diagnose skill change outcomes or process? The earlier cross-module set was at the ceiling and its mutants were blatant (`../cross-module-diagnose/README.md`).

## Design

Same harness as `../cross-module-diagnose`, three changes:

- `gen.py` keeps only subtle operators: `NumberReplacer`, ordering-comparison swaps (`Lt`/`LtE`/`Gt`/`GtE`), arithmetic swaps (`Add`/`Sub`/`Mul`/`Div`/`FloorDiv`/`Mod`), `and`/`or` swaps and `DropTerm`. Stubs, constant returns and string edits are out. Mutants must be killed by a different module's tests than the helper's own. 62 candidates came out of 5 helper and caller pairs; I picked 10 by hand, none on a line the earlier set used (`tasks.json`).
- Symptoms in `symptoms.json` are written at the caller and never name the helper.
- The skill arm reads the current `skills/diagnose/SKILL.md`, which includes the "show the red before the first edit" step from #174. The earlier skill arm used the old text.

Arms: `skill` and `base`, Sonnet 5.5 subagents, one run per task, tests removed from the tree. Grade 1 puts the original tests back and counts failures beyond the 8 that every run shares (environment: no `.git`, `skills/` removed from the tree). Grade 2 reads each transcript for a python run before the first edit to `scripts/`, and I read the pre-edit commands by hand (`results/process.txt` is the regex count).

## Results

| | skill | base |
|---|---|---|
| hidden tests green | 10/10 | 10/10 |
| cause found in the helper, not the named caller | 10/10 | 10/10 |
| ran a check on the bug before the first edit | 10/10 | 0/10 |
| mean tool calls | 10.6 | 8.9 |
| mean call index of first edit | 6.8 | 5.2 |

Per-run grades are in `results/grade-<arm>-cN.json`; `new_failures` there still includes the 8 shared environment failures.

## Reading

- Outcome: a ceiling again, 20/20. Single-line subtle mutants are still found by reading: every agent opened the helper within a few calls, and no base agent ran anything before editing.
- Process: with the #174 wording the skill arm ran a probe script before its first edit in all 10 runs (0/10 for the old wording in the earlier set, 0/10 here for no skill). Cost is about 1.7 tool calls per task.
- Two symptoms were written wrong by me. c4 said positions 250 and 500 go missing (only position 0 and the last batch's size are wrong), and c5 said a suite of exactly 250 is split (the inverted test splits 249 and below and returns 250 whole). The skill agents noticed the mismatch in their probe and fixed the real line anyway; one base agent did the same. It did not change a grade.

## Caveats

- n=10 per arm, one sample per task, seeded in compost's own scripts, which agents may know from training.
- Every mutant is one line. Subtlety here means a mutated operator or constant, not a cause that needs a hypothesis to find. State, data and environment bugs are the untested region.
- The briefs name the skill file, so the skill arm measures compliance when read, not whether the skill fires.
- Token counts are not reported.
