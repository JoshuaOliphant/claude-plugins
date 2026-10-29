# Diagnose on bugs where reading may not find the cause (#187)

Question: every earlier diagnose experiment (#114, #169, #171, #173) sat at an outcome ceiling because the bug report named the failing behaviour closely enough that reading the code found the cause. Does `compost:diagnose` beat an unguided agent when the cause is state, data, or environment rather than a line you can spot?

Answer in one line: no. 80 runs, 80 green. The skill's measurable effect is still only process: it puts a reproduction on record before the first edit (39/40 runs against 6/40), for about 2.4 more tool calls, 95k more tokens (mostly cache reads) and $0.08 more per run.

## Design

Two task sets, 10 tasks each, same arms and grading.

- **Round 1 (`h1` to `h10`, small).** Seeded Python projects of 50 to 220 lines, causes that live in state, data or environment: shared mutable catalog item (h1), `lru_cache` key that ignores a field (h2), one bad event in a 600-event JSON file (h3, h1 to h3 reused from the debugger PoC), a Cyrillic letter in a CSV SKU (h4), `int(price * 100)` truncation (h5), `PYTHONHASHSEED`-dependent tie order (h6), DST day arithmetic (h7), shallow-copied nested defaults (h8), generator consumed by a preview (h9), unsorted `glob` order (h10).
- **Round 2 (`L1` to `L10`, large).** Added after round 1 showed base agents solving the small trees in about three tool calls with one `cat` of the whole project. Ten apps of 28 to 34 modules and 1,675 to 2,199 lines each, authored by Opus 5.5 from `author/L*.prompt` (one bug class per task), each with at least four decoys that use the same idiom harmlessly. Causes: stale on-disk cache (L1), import-time `decimal` context change (L2), unlocked get-or-create under threads (L3), naive `mktime` under a non-UTC `TZ` (L4), a trigger inside the shipped SQLite file (L5), a stray `.env.local` that outranks the config file (L6), duplicate `.csv` registration decided by directory listing order (L7), a global revision counter that defeats per-namespace indexes so imports go quadratic (L8), `deep_merge` aliasing the shared template (L9), a cursor cache that resumes an abandoned stream (L10). `notes/L*.md` say where each cause is and what the decoys are.

Per task: the agent gets the tree with no `tests/`, plus a user-style symptom (`symptoms.json`, effect only, no function named as the cause). Grading lays the hidden tests (`hidden/<task>/tests`, fix-agnostic: they assert behaviour, and where order or timing matters they vary it, for example `PYTHONHASHSEED` 0 to 7, reversed `os.scandir`, `TZ` set, a barrier with `sys.setswitchinterval(1e-6)`, store-read counts instead of wall clock) over the agent's tree and runs them. Every task was checked by me: hidden tests red on the buggy tree, green after the reference fix in `reference/`.

Arms: `skill` (brief says to use the compost:diagnose skill through the Skill tool; the installed text is byte-identical to main, compost 0.24.2) and `base` (same brief, `--disable-slash-commands`, "Method: your choice"). Sonnet 5.5, headless `claude -p`, 2 runs per cell, 40 runs per round, `build.py`, `run_one.sh`, `grade.py`. The plugin-eval runner in compost-evals is for trigger cases, so it was not used.

## Results

Green means every hidden test passes. There were no environmental failures to name: the trees are standalone and every run graded cleanly.

| | round 1 skill | round 1 base | round 2 skill | round 2 base |
|---|---|---|---|---|
| hidden tests green | 20/20 | 20/20 | 20/20 | 20/20 |
| symptom reproduced by running code before the first edit (by hand) | 19/20 | 1/20 | 20/20 | 5/20 |
| ... with an assertion or expected value in the check | 17/20 | 0/20 | 5/20 | 0/20 |
| tool calls (mean) | 5.8 | 3.3 | 9.1 | 6.8 |
| tokens incl. cache reads (mean, k) | 286 | 211 | 520 | 425 |
| cost (mean, $) | 0.14 | 0.07 | 0.23 | 0.15 |
| wall seconds (mean) | 28 | 21 | 48 | 41 |

Pooled: green 40/40 vs 40/40; reproduced before editing 39/40 vs 6/40; 7.4 vs 5.0 calls; 403k vs 318k tokens; $0.18 vs $0.11. Zero failures in 40 runs bounds either arm's true failure rate below about 7% (one-sided 95%), so any outcome effect on tasks like these is smaller than that.

Per-run numbers: `results/runs.csv`. Hand labels for the red-before-edit rows: `results/redcheck-hand.csv` (N = no code run on the symptom before the first edit; R = ran code on the real path that showed the reported wrong behaviour; RA = R with an assertion or expected value that fails). I read every pre-edit command and its output with `preedit.py`; `redcheck.py` only flags candidates. Transcripts: `results/transcripts.tar.gz`. There are no red cells to read.

Every skill run invoked the skill (`skill_invoked` in `runs.csv`) and none of the 40 base runs had it.

## What the data says

1. **Outcome: still no gain, now including bugs the agent cannot spot at a glance.** Base agents on the large apps used 6.8 calls on average. They grepped the idiom (`getcontext`, `scandir`, `mktime`, `.env`), read the two or three modules the symptom pointed at, and found the cause. Two reasons I can see, neither tested separately: the symptoms keep one discriminating clue each (L4 "the same command on our UTC box gives the right numbers", L6 "other settings in the same file are picked up fine", L7 "on our CI runner"), and a 2,000-line app is still small enough to navigate by grep. So "reading does not find the cause" did not hold for Sonnet 5.5 at this size even with decoys.
2. **Process: the enforced red check is followed.** 39/40 skill runs ran the reported scenario before editing, against 6/40 base runs (all six ran the reported scenario as one of their first steps). This repeats #174's 10/10.
3. **The skill's check is usually an eyeball, not an assertion, when a CLI is available.** In round 2 only 5/20 skill runs wrote a check that asserts the expected value (the concurrency, ordering and quadratic tasks, where a CLI run cannot show the bug); the other 15 ran the CLI and compared output to the report by eye. Step 2 asks for a red-capable check; this is close to the line and did not change any outcome.
4. **Cost: about 2.4 more calls and $0.08 per run.** Round 2 skill runs also took 7 s longer on average. Same size as #171 (+2.5 calls).
5. **Skill-specific failure modes: none seen.** No run patched a symptom instead of the cause (hidden tests are behavioural and all pass), and no skill run got stuck building a check.

## Recommendation: keep, trim the claim, stop measuring outcomes with seeded tasks

- **Keep `skills/diagnose` as it is (the #174 wording).** It reliably changes behaviour, the price is small, and across five data sets (about 190 runs) its green rate has stayed within one run of no skill.
- **Do not rewrite.** Nothing here suggests a wording change would raise green rate; both arms are at 100% on this set.
- **Narrow the claim, not the skill.** The supportable statement is "diagnose puts a reproduction on record before the first edit." If the description or README says it finds root causes better, trim that.
- **Optional, for Joshua:** step 2 could say the check should state the expected value, since 15 of 20 round 2 skill checks were an unasserted CLI run. I did not change the skill; that is a behaviour change and waits for review.
- **What would change this:** only bugs where the agent has no symptom clue and no cheap reproduction, which cannot be graded by hidden tests: a flaky failure seen once in CI, a production-only behaviour, a bug in a codebase far larger than 2k lines. The right data for that is real sessions (the skill-drift log) rather than another seeded set. Another seeded round would almost certainly land at the ceiling again.

## Caveats

- n=2 per cell, one model (Sonnet 5.5), one skill text. A very small effect is not ruled out; a large one is.
- Round 2 trees and symptoms were written by an LLM (Opus 5.5) and validated by me for red/green behaviour, not for how hard they are to read; the clues in the symptoms are part of why base agents succeed.
- The brief says "a small Python project" in both rounds (template wording); round 2 trees are not small.
- Agents were told not to look outside their tree. I searched all 80 transcripts for the repo path, the author directory, `hidden`, `NOTES.md`, `reference_fix` and other runs' trees: no hits.
- "Reproduced before the first edit" is a hand judgement; the hardest calls were runs that inspect a database or data file without replaying the reported scenario (base-L5-2, base-h3-1, skill-h3-1), which I labelled N.

## Run it

```
HW=/tmp/hard-diagnose python3 build.py                       # round 1 trees and briefs (TASKS="L1 ... L10" for round 2)
ls /tmp/hard-diagnose/runs | xargs -P 8 -I{} ./run_one.sh {}   # claude -p, Sonnet 5.5
HW=/tmp/hard-diagnose python3 grade.py skill-L3-1             # one run's JSON
HW=/tmp/hard-diagnose python3 analyze.py                      # calls, tokens, cost per run
HW=/tmp/hard-diagnose python3 preedit.py skill-L3-1           # pre-edit commands and output, for hand labelling
```

The tests run with `/home/user/pt-venv/bin/python` (a venv with pytest; override with `PY`).
