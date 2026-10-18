# Judge mutation (PoC for #113)

Inject one known defect at a time into text a judge should accept, and see whether the judge notices. The result is a kill rate per defect kind instead of one accuracy number. Two harnesses:

- `mutate_judge.py`: claims that compost-evals labels `backed` by their command output, judged by Jev's `claim-backed` (first section below).
- `mutate_kb.py`: sentences from compound-retrieve answers that passed every expectation, mutated and judged against the knowledge base (last section).

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
- **`overclaim` is the weak spot.** A true claim plus an unshown conjunct drew `supports` in 6 of 9 Choice answers, mostly at confidence 0.6 to 0.7, so they land in "routed", and one ("ruff clean and the type check is clean") was missed at 0.88. The Noul at cut 0.5 caught only 4 of 9; several others scored 0.52 to 0.76. The stricter wording (written after seeing the first answers, so it is tuned on this set) cut `supports` from 6 to 2 and picked `says_nothing` 5 times, but confidence stayed under the gate for most, so caught went from 2 to 3 and routed stayed at 6. Wording helps the verdict more than the confidence; splitting a claim into its parts and asking about each is the next thing to try (done below).
- **`wrong-subject` n=1**, a missed test-name swap at 0.97 confidence. An anecdote, but a confident one; identifier mismatches are another check for code, not for the model.
- **The Choice trades catches for routing.** At the 0.8 gate it auto-catches fewer than the Noul does at 0.5, but it also tells you the kind of failure (`contradicts` for wrong numbers, `says_nothing` for unshown claims) and routes the doubtful ones. Neither judge false-flagged an original or a benign control, but that is 14 true claims, so the false-flag rate is only bounded, not measured.
- **Answers are not repeatable across requests.** The one claim I compared across two runs (requests differed only in the question set) scored 0.63 and then 0.59 on the Noul, and the Choice routed 2 originals the first time and 1 the second. Treat differences of a few hundredths as noise.
- **Not covered:** claims about knowledge-base entries (the compound-retrieve case in #113), process expectations from a tool trace, other judge models, and LLM-written mutants (all operators here are code or hand-written, so the "too obvious" question is open).

Choice `confidence` and thresholds follow the TypeSafe docs (confidence page, citation-check cookbook); the 0.8 gate is the cookbook's starting value, not tuned here.

## Splitting a claim into parts (2026-10-18)

Code cuts each claim at "and", ";", "with" and a comma before a number or "coverage", judges each part against the output, and flags the claim if any part fails. The cues were chosen after reading the first run, on these cases, so treat the numbers as an upper bound for a splitter you did not tune on them.

| operator | n | Noul (whole claim) | Noul (lowest part) | strict Choice (whole) | strict Choice (split) c/r/m |
|---|---|---|---|---|---|
| overclaim | 9 | 4 | 7 | 3/6/0 | 4/5/0 |
| hand-subtle | 5 | 5 | 5 | 2/3/0 | 4/1/0 |
| everything else | 16 | 15 | 15 | 13/2/1 | 13/2/1 |
| originals and benign controls | 14 | 0 false flags | 0 false flags | 0 flagged | 0 flagged |

Splitting helps where the first run said it would: an unshown conjunct becomes its own part, and the part comes back `says_nothing`. The lowest-part Noul caught 7 of 9 overclaims with no false flag on 14 true claims. The test-name swap is still missed, because the failure is in a single token, not in a conjunct. n is small and the true claims number 14.

## Knowledge-base claims (2026-10-18)

`mutate_kb.py` takes 12 compound-retrieve answers from `../skill-mutation/results-116` (4 each from cases 1 to 3, all of whose expectations passed), splits them into checkable sentences (90), and mutates 3 sentences per answer, one defect each. The knowledge base is the public fixture under `plugins/compound-knowledge/skills/compound-retrieve/evals/fixtures/`, so this harness and its data are committed here.

Operators: `path-swap` and `fabricated-source` and `number-swap` are code; `wrong-fact`, `wrong-conclusion` and `unsupported-addition` are Sonnet rewrites given the knowledge base. That is 137 mutants. Four judges:

- **Jev, per sentence:** a Choice (`supports` / `contradicts` / `says_nothing`) and a Noul over `{claim, kb}`, plus a no-model check that every `.md` name in the claim exists in the knowledge base.
- **Sonnet, per sentence:** the same three-way question, asked of Sonnet.
- **Sonnet eval checklist, whole answer:** `mutate_skill.judge` with the case's own expectations; a mutant is flagged when an expectation that held on the original fails.
- **The same checklist plus one open expectation**, "every file path and factual claim is supported by the knowledge base", with the knowledge base in the prompt.

| operator | n | no-model path check | Jev Noul < 0.5 | Jev Choice not `supports` | Sonnet per sentence | checklist | checklist + open |
|---|---|---|---|---|---|---|---|
| path-swap | 14 | 14 | 14 | 13 | 14 | 4 | 5 |
| fabricated-source | 14 | 14 | 12 | 7 | 14 | 5 | 10 |
| number-swap | 2 | 0 | 2 | 2 | 2 | 0 | 2 |
| wrong-fact | 35 | 6 | 29 | 22 | 31 | 3 | 14 |
| wrong-conclusion | 36 | 0 | 34 | 31 | 36 | 2 | 18 |
| unsupported-addition | 36 | 1 | 26 | 19 | 30 | 0 | 11 |
| **all** | 137 | 35 | **117 (85%)** | **94 (69%)** | **127 (93%)** | **14 (10%)** | **60 (44%)** |
| false flags on 90 true sentences | | 0 | 16 | 11 | 15 | 0 of 12 answers | 2 of 12 answers |

What it says, and how far to trust it:

- **The unit of judgment matters more than the model.** Sonnet with the open "every claim is supported" check, given the whole answer, caught 44%. The same model asked about one sentence caught 93%. The eval checklist alone caught 10%, which is the blind spot #113 predicted: a wrong path or fact in a sentence no expectation names goes unnoticed.
- **Jev per sentence is competitive and cheap to run in parallel.** The Noul at 0.5 caught 85%; Sonnet caught more (93%) at a similar false-flag rate. The 227 Jev asks took 1.1M input tokens, because every ask carries the 16 KB knowledge base; the Sonnet cost was not recorded. Jev's edge is not accuracy here but a probability you can threshold.
- **The 0.8 confidence gate from the cookbook is too high here.** At 0.8 the Choice caught 38, routed 87 and missed 12 of 137, and routed 26 of 90 true sentences, which is a review queue nobody wants. Lowering the gate to 0.5 caught 56 with 3 false. This is a different document shape from the cookbook's RFC sections, so tune it on your own data.
- **The false-flag counts are upper bounds.** A read of the 24 originals flagged in a first pass found about half were not claims about the knowledge base at all (tool-output facts, advice, run-environment paths), and the rest were mostly true claims one judge doubted. The second run strips sandbox paths and drops run-describing sentences, which moved the counts only slightly.
- **The mutants are not all defects.** Sonnet wrote them and nothing checked every one. Reading 8 mutants that both Jev and Sonnet passed turned up at least one that is not wrong (it swaps `MOCHI_API_KEY` for `TYPESAFE_API_KEY`, and the knowledge base names both), and an `unsupported-addition` that restates a safe inference. So the recall for the three LLM operators is a lower bound.
- **A hybrid is better than either half.** The deterministic path check plus a per-sentence judge covers path and source defects completely (28 of 28) with no model. The checklist is still the only judge here that sees the tool trace, so keep it for the process expectations ("did it read the registry") and use per-sentence claim judging for content.
- **Not covered:** hand-written subtle mutants for knowledge-base claims, other judge models than Sonnet, claims drawn from knowledge bases of different shape, and repeatability of Jev (answers moved a few hundredths between requests in the first harness).

Rerun with `uv run --script ai_docs/experiments/judge-mutation/mutate_kb.py` (needs `TYPESAFE_API_KEY` and a logged-in `claude`). Mutants and judgments are cached under `kb-data/`, so a rerun on the same inputs is free.
