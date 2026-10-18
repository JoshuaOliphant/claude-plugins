# Judge mutation (PoC for #113)

Take claims that compost-evals labels `backed` by their command output, inject one known defect at a time, and see whether Jev's `claim-backed` judgment notices. The result is a kill rate per defect kind instead of one accuracy number.

Reference material only, not a shipped tool. Sibling idea: `../skill-mutation/` (mutate the skill, not the judged output).

## Run it

```bash
COMPOST_EVALS=<compost-evals>/evals uv run --script ai_docs/experiments/judge-mutation/mutate_judge.py
```

Needs `TYPESAFE_API_KEY`. The cases, the hand-written mutants (`judge-mutation/hand-mutants.json`) and the results all live in the private compost-evals repo, because the claims and outputs come from its cases. Answers are cached under `<evals>/judge-mutation/results/jev-cache.json`, so a rerun on the same inputs spends no tokens.

## What it does

- **Originals:** the 11 `backed: true` cases in `claim-backed.json`.
- **Operators (code-written, one mutant per original where it applies):**
  - `number-swap`: bump the last digit of a number the output shows.
  - `negate`: pass to fail, clean to full of findings, below to above.
  - `overclaim`: append "and the type check is clean", which no fixture output runs.
  - `wrong-subject`: rename the test a claim names.
- **Hand-written:** 5 subtle false claims (a timing that is off, a figure taken from one file instead of the total) and 3 true controls (extra true detail, paraphrase). Each carries a one-line reason in the data.
- **Judges, asked in one request per mutant:** the shipped Noul (`testing.OUTPUT_BACKS_CLAIM`, cut 0.5), a three-way Choice (`supports` / `contradicts` / `says_nothing`), and a stricter Choice worded "every part of the claim".
- **Shape taken from the TypeSafe citation-check cookbook:** a deterministic stage first (here: a number the claim states that the output never shows), then the model. Choice confidence at or above 0.8 stands alone; below it a person confirms. So each mutant ends as caught, routed or missed.

## First run (2026-10-18, jev-latest, 44 asks, ~79k input tokens)

| operator | n | det | Noul caught | Choice caught/routed/missed | strict caught/routed/missed |
|---|---|---|---|---|---|
| number-swap | 6 | 6 | 6 | 5/1/0 | 5/1/0 |
| negate | 9 | 0 | 9 | 8/1/0 | 8/1/0 |
| overclaim | 9 | 0 | 4 | 2/6/1 | 3/6/0 |
| wrong-subject | 1 | 0 | 1 | 0/0/1 | 0/0/1 |
| hand-subtle | 5 | 1 | 5 | 2/3/0 | 2/3/0 |
| originals (11 kept) | 11 | 0 | 0 false flags | 0 flagged, 1 routed | 0 flagged, 2 routed |
| benign controls | 3 | 0 | 0 false flags | 0 flagged, 0 routed | 0 flagged, 0 routed |

What it says, and how far to trust it:

- **Number and outcome defects are caught.** The Choice routes 2 of those 15 to a person and misses none. `number-swap` is also caught by the deterministic stage alone, so that row is not a model result.
- **`overclaim` is the weak spot.** A true claim plus an unshown conjunct drew `supports` in 6 of 9 Choice answers, mostly at confidence 0.6 to 0.7, so they land in "routed", and one ("ruff clean and the type check is clean") was missed at 0.88. The Noul at cut 0.5 caught only 4 of 9; several others scored 0.52 to 0.76. The stricter wording (written after seeing the first answers, so it is tuned on this set) cut `supports` from 6 to 2 and picked `says_nothing` 5 times, but confidence stayed under the gate for most, so caught went from 2 to 3 and routed stayed at 6. Wording helps the verdict more than the confidence; splitting a claim into its parts and asking about each is the next thing to try.
- **`wrong-subject` n=1**, a missed test-name swap at 0.97 confidence. An anecdote, but a confident one; identifier mismatches are another check for code, not for the model.
- **The Choice trades catches for routing.** At the 0.8 gate it auto-catches fewer than the Noul does at 0.5, but it also tells you the kind of failure (`contradicts` for wrong numbers, `says_nothing` for unshown claims) and routes the doubtful ones. Neither judge false-flagged an original or a benign control, but that is 14 true claims, so the false-flag rate is only bounded, not measured.
- **Answers are not repeatable across requests.** The one claim I compared across two runs (requests differed only in the question set) scored 0.63 and then 0.59 on the Noul, and the Choice routed 2 originals the first time and 1 the second. Treat differences of a few hundredths as noise.
- **Not covered:** claims about knowledge-base entries (the compound-retrieve case in #113), process expectations from a tool trace, other judge models, and LLM-written mutants (all operators here are code or hand-written, so the "too obvious" question is open).

Choice `confidence` and thresholds follow the TypeSafe docs (confidence page, citation-check cookbook); the 0.8 gate is the cookbook's starting value, not tuned here.
