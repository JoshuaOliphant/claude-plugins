# Skill mutation testing (PoC)

Treat a SKILL.md as the program and its `evals.json` as the test suite:

1. Delete one chunk of the skill at a time (a paragraph, a list item, or a code block).
2. Rerun the evals on each version.
3. Report which deletions the evals noticed.

A deletion the evals miss means one of two things: the evals have a gap, or the line changes nothing and can be cut.

This is reference material only, not a shipped skill. Related ideas: #113 (mutate outputs to measure the judge) and #114 (mutation score for agent-written tests, and mutants as eval tasks).

## Run it

```bash
python ai_docs/experiments/skill-mutation/mutate_skill.py \
  --skill plugins/compound-knowledge/skills/compound-retrieve/SKILL.md \
  --evals plugins/compound-knowledge/skills/compound-retrieve/evals/evals.json \
  --kb knowledge/solutions --out <dir> --trials 5 --workers 12
python ai_docs/experiments/skill-mutation/mutate_skill.py ... --out <dir> --judge-check
python ai_docs/experiments/skill-mutation/analyze.py <dir> [--exclude-escaped]
```

**Subject.** Each run is headless `claude -p` on haiku:
- The skill is injected with `--append-system-prompt`.
- `--setting-sources ""` keeps installed plugins out.
- Each trial gets a fresh project directory holding a copy of the KB, plus an empty `HOME`.

**Judge.** Sonnet grades each expectation from the tool trace and the final response.

**Controls.**
- Two byte-identical copies of the skill (negative controls). Any kill on these is noise.
- One variant with the whole skill deleted (positive control). If it survives, the evals don't measure the skill.

**Bookkeeping.**
- Timeouts, errored runs, unparseable verdicts and a wrong served model go to `errors.jsonl`, never into scores.
- Reads outside the sandbox are flagged per row.

## Results: compound-retrieve, shipped evals (2026-10-17)

The run had 3 cases × 54 variants × 5 trials = 810 runs, with 0 infra errors. Subject cost was $4.23; judge cost was not recorded. Full output is in `results/analysis.txt`, and per-run transcripts are in `results/results.jsonl.gz`.

**Mutation score: 0/50.** Neither negative control was killed, so this isn't the kill rule being trigger-happy. The evals can't see the skill:

| Variant | c1e5 "checked critical-patterns.md" | The other 6 live expectations |
|---|---|---|
| baseline | 0.8 | 1.0 |
| identical copies | 0.8, 0.8 | about 1.0 |
| delete L82, "MUST always read critical-patterns.md" | 0.4 | 1.0 |
| delete L102, "Search summary first … critical-patterns.md" | 0.4 | 1.0 |
| **whole skill deleted** | **0.0** | **1.0** |

### Findings

1. **The evals have rotted.**
   - Only 7 of 15 expectations ever pass at baseline (at least 3 of 5 runs).
   - Case 3 and two expectations in case 2 refer to KB entries that are no longer in `knowledge/solutions/` (the feedback-persistence pattern and the skill-value principle).
   - Case 1 e4 expects a `knowledge-researcher` subagent that the current SKILL.md never mentions.
   - "Searched cross-project KBs" assumes a registry that doesn't exist.
   - Because no reference answer can pass these expectations, a mutant can never make them fail.

2. **The live expectations pass without the skill.** The KB has three files, and the prompt says "check the knowledge base", so plain haiku greps and finds the answer. Six of the seven live expectations only test that the right fact gets found. Finding it is easy, and the skill isn't what makes it happen. Only c1e5, a process check, depends on the skill.

3. **Instructions stated more than once survive single deletions.** The critical-patterns instruction appears three times (L82, L84, L102):
   - Deleting any one of them halves c1e5's pass rate (0.8 to 0.4), which is under the 0.5 kill threshold.
   - Deleting all three takes it to 0.

   Single-chunk mutants systematically miss behaviour the prompt states more than once. The fix is higher-order mutants: delete every chunk that names a concept together.

4. **The noise floor is about the size of the effects.** At 5 trials, a per-expectation pass rate moves in steps of 0.2, and two copies of the same skill can differ by 0.4 on a single expectation (c3e5: 0.8 vs 0.4). Telling a 0.4 drop from noise needs more trials, or pooling expectations per mutant.

5. **The judge is trustworthy for this.** Re-grading gave 45 of 45 identical verdicts. Null answers ("", "I don't know.", an off-topic answer) failed every expectation except c2e5 ("does not fabricate"), which an empty answer passes trivially.

6. **The sandbox leaks.** 253 of 810 runs read outside it, mostly `find /` into `/root/.claude/plugins/marketplaces/...`, which holds a second copy of this repo's KB. Excluding those runs gives the same conclusions (`--exclude-escaped`). Fully blocking reads needs a container.

### What the method says to do next

Until the evals can tell a run with the skill from a run without it, survivors carry no information about the skill's lines. In order:

- **Make the positive control fail.** Fix the evals so that deleting the whole skill drops several expectations:
  - Restore or rewrite the KB fixture so every expected entry exists.
  - Add a `critical-patterns.md` that holds a relevant warning.
  - Add a case where the directory is missing (the skill should suggest setup).
  - Add a case where nothing relevant exists (the skill should honestly say nothing was found). This also covers both directions.
- **Add concept-level mutants** (delete every mention of critical-patterns, of the registry, or of the output order) next to the single-chunk ones.
- **Then rerun.** Survivors on a suite where the positive control fails are the actionable list: each one is either a missing eval case or a line to delete.
