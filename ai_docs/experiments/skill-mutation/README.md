# Skill mutation testing (PoC)

Treat a SKILL.md as the program and its `evals.json` as the test suite:

1. Delete one chunk of the skill at a time (a paragraph, a single list item, or a code block).
2. Rerun the evals on each version.
3. Report which deletions the evals noticed.

A deletion the evals miss means one of two things: the evals have a gap, or the line changes nothing and can be cut.

This is reference material only, not a shipped skill. Related ideas: #113 (mutate outputs to measure the judge) and #114 (mutation score for agent-written tests, and mutants as eval tasks).

## Run it

```bash
uv run --group dev python ai_docs/experiments/skill-mutation/mutate_skill.py \
  --skill plugins/compound-knowledge/skills/compound-retrieve/SKILL.md \
  --evals plugins/compound-knowledge/skills/compound-retrieve/evals/evals.json \
  --plugin-root plugins/compound-knowledge --out <dir> --trials 5 --workers 12
uv run --group dev python ai_docs/experiments/skill-mutation/mutate_skill.py ... --out <dir> --judge-check
uv run --group dev python ai_docs/experiments/skill-mutation/analyze.py <dir> [--exclude-escaped]
```

`analyze.py` also reads the committed runs directly: `analyze.py ai_docs/experiments/skill-mutation/results`.

`--controls-only` runs the baseline and the controls without mutants, which is enough to check that the evals measure the skill at all. `--kb` and `--home-seed` default to the `fixtures` block in `evals.json` (paths relative to it). A case with `"kb": null` runs with no knowledge directory. `--plugin-root` copies the plugin's `scripts/` into the sandbox and points `CLAUDE_PLUGIN_ROOT` at the copy, so the skill's resolver and feedback calls run as they would installed. `--agents-dir` offers the plugin's agents; leave it off when an agent carries the skill's own procedure (compound-knowledge's `knowledge-researcher` does), or the no-skill control delegates to it and stops being skill-free.

**Subject.** Each run is headless `claude -p` on haiku:
- The skill is injected with `--append-system-prompt`.
- `--setting-sources ""` keeps installed plugins out.
- With `--agents-dir`, the plugin's own agents are offered through `--agents`, so the subject can delegate as it would when installed.

**Sandbox.**
- Each trial gets a fresh project directory holding a copy of the KB (none for a `"kb": null` case).
- Its `HOME` is empty, or a copy of `--home-seed` when one is given, for example a registry fixture.

**Judge.** Sonnet grades each expectation from the tool trace and the final response. Only real JSON booleans count; anything else is retried.

**Controls.**
- Two byte-identical copies of the skill (negative controls).
- One variant with the whole skill deleted (positive control).

**Kill rule.**
- The reference is the baseline pooled with the identical copies. Each identical copy is compared against the pool of the others.
- An expectation is *live* when its reference pass rate is at least the drop a kill needs.
- A mutant is killed when some live expectation drops by at least 0.5 (absolute).
- The rule is absolute rather than relative because identical copies already differ by 0.4 on one expectation.
- `analyze.py` also gives the number of kills expected by chance (binomial) if no deletion mattered.

**Bookkeeping.**
- Mutant labels are SKILL.md line numbers.
- Timeouts, errors, unparseable verdicts and a wrong served model go to `errors.jsonl`, never into scores.
- Reads outside the sandbox are flagged per row.
- `manifest.json` refuses to resume into an `--out` whose inputs changed.

## Results: compound-retrieve, shipped evals (2026-10-17)

The run had 3 cases × 54 variants × 5 trials = 810 runs, with 0 infra errors. Subject cost was $4.33; judge cost was not recorded.

Reproduce it from commit 332e3bf (the evals and KB it ran against were rewritten for #116): `mutate_skill.py --skill plugins/compound-knowledge/skills/compound-retrieve/SKILL.md --evals plugins/compound-knowledge/skills/compound-retrieve/evals/evals.json --kb knowledge/solutions --agents-dir plugins/compound-knowledge/agents --out <dir> --trials 5 --workers 12`, with that commit's `mutate_skill.py`.

Outputs in `results/`:
- `analysis.txt` and `analysis-excluding-escaped.txt`: the analysis, with and without runs that read outside the sandbox.
- `results.jsonl.gz`: per-run transcripts.
- `judge_check.json`: the judge check.

**Mutation score: 2/50.**

| View | Kills | Kills expected by chance | Positive control killed? |
|---|---|---|---|
| All runs | 2 | about 0.8 | yes, by c1e5 and c3e5 |
| Excluding the 249 runs that read outside the sandbox | 2 | about 3.1 | yes, by c1e5 |

Neither view shows a deletion the evals reliably detect:
- **Excluding leaked runs**, two kills against about three expected is noise.
- **Across all runs**, both kills come through c3e5. That expectation passes in 0.67 of reference runs, but in only 0.20 once leaked runs are dropped: the subject meets it by finding `feedback_manager.py` outside the sandbox. One of those two "kills" deletes a line about tdd-workflow ordering, which can't plausibly matter to these cases.

### Findings

1. **One expectation measures the skill.** c1e5 ("checked or referenced critical-patterns.md") goes from 0.6 in the reference to 0.0 with the whole skill deleted, and nothing else moves:

   | Variant | c1e5 |
   |---|---|
   | baseline, identical copy 1, identical copy 2 | 0.4, 0.8, 0.6 |
   | delete L93, "MUST always read critical-patterns.md" | 0.4 |
   | delete L95, "Checked critical-patterns.md — no patterns apply" | 0.4 |
   | delete L113, "Search summary first … critical-patterns.md" | 0.6 |
   | **whole skill deleted** | **0.0** |

   The other expectations that pass (c1e1–3, c2e1, c2e3, c2e5) pass without the skill. The KB has three files, and the prompt says "check the knowledge base", so plain haiku greps and finds the answer.

2. **Instructions stated more than once survive single deletions.** The critical-patterns instruction appears three times (L93, L95, L113):
   - Deleting any one of them leaves c1e5 inside the spread of the identical copies (0.4 to 0.8).
   - Deleting the whole skill takes it to 0.

   Single-chunk mutants systematically miss behaviour that a prompt states more than once. The fix is concept-level mutants: delete every chunk that names a concept together.

3. **The evals have rotted.** 7 of the 15 expectations can't be met as written, and each scores 0.20 or less once leaked runs are excluded:
   - **Missing KB entries.** Case 3 and c2e2 expect KB entries that are no longer in `knowledge/solutions/` (the feedback-persistence pattern and the skill-value principle).
   - **c1e4 expects a delegation the skill never asks for.** It wants the `knowledge-researcher` subagent spawned. The agent was offered to every run, and when asked directly haiku does spawn it, yet 0 of 810 runs delegated. The skill only mentions "the researcher" inside conditions (L79, L85) and never tells the model to delegate.
   - **c2e4 cannot pass in this harness.** It expects a cross-project search, but nothing in the repo provides a registry, and the sandbox HOME is empty. A registry fixture passed with `--home-seed` would make it testable.

   Filed as #116.

4. **The noise floor is about the size of the effects.**
   - The three identical arms gave c1e5 pass rates of 0.4, 0.8 and 0.6.
   - Which arm got called "baseline" used to decide which expectations counted. In the first run on the earlier harness, c1e5 was live; in this run's baseline alone it wasn't.
   - Pooling the reference and estimating chance kills are the analysis's answer to that. More trials, or pooling expectations per mutant, would be the run's answer.

5. **The judge is good enough for this.**
   - Re-grading 75 baseline verdicts agreed on 72.
   - Null answers failed every expectation except c2e5 ("does not fabricate"). The judge passes it for "I don't know." and for an off-topic answer about Paris; the empty answer fails it. A non-answer that fabricates nothing passes c2e5 by construction, so c2e5 can only catch fabrication, not the absence of an answer.

6. **The sandbox leaks, and the leak matters.** 249 of 810 runs read outside the sandbox, mostly through `find /` into `/root/.claude/plugins/marketplaces/...`, which holds a second copy of this repo and its KB. That leak is what keeps c3e5 alive (finding above). Fully blocking reads needs a container. Until then, read the `--exclude-escaped` view.

### What the method says to do next

Until several expectations depend on the skill, survivors carry little information about its lines. In order:

- **Fix the evals (#116)** so that deleting the whole skill drops several expectations, not one:
  - a fixture KB with every named entry and a `critical-patterns.md`;
  - a "nothing relevant" case and a "no knowledge dir" case;
  - a registry fixture for the cross-project expectation;
  - drop the delegation expectation, or add delegation to the skill.
- **Add concept-level mutants** next to the single-chunk ones.
- **Run in a container,** or keep reading the `--exclude-escaped` view.
- **Then rerun.** Survivors are the actionable list: each one is either a missing eval case or a line to delete.

## Results: compound-retrieve, evals rebuilt for #116 (2026-10-17)

`results-116/`: `--controls-only`, 5 trials, no agents offered, `--plugin-root plugins/compound-knowledge`. 4 variants × 5 cases × 5 trials = 100 runs, 0 infra errors, subject cost $0.45.

The evals now ship their own fixtures (`evals/fixtures/`): a KB holding every entry an expectation names plus a `critical-patterns.md`, and a HOME whose registry lists a second KB (`skill-lab`). Cases 4 and 5 cover "nothing relevant" and "no knowledge dir". The delegation expectation is gone.

- **24 of 24 expectations are live** in the reference (the old evals had 8 of 15 meetable).
- **The whole-skill deletion is killed by 5 expectations**, against 1 before. The identical copies are killed by none.

  | Expectation | Reference (3 arms) | No skill |
  |---|---|---|
  | c2e1 read the cross-project registry | 0.8, 1.0, 1.0 | 0.0 |
  | c2e2 names the registered skill-lab KB | 0.6, 0.8, 1.0 | 0.0 |
  | c4e4 searched the registry on a miss | 1.0, 1.0, 1.0 | 0.0 |
  | c4e3 reports critical-patterns.md checked, none apply | 1.0, 1.0, 1.0 | 0.2 |
  | c3e5 checked critical-patterns.md | 1.0, 1.0, 1.0 | 0.4 |

- **Case 5 is masked by the leak.** Without the skill, haiku still reports the missing directory (0.8) and suggests setup (0.6). In 3 of those 5 runs it left the sandbox, found the installed compound-knowledge plugin (`/root/.claude/plugins/synced/...`, or this checkout under `/home/user`) and ran its resolver, whose stderr names `/compound-knowledge:setup`. In a container it should separate.
- **Case 1 doesn't separate either.** `critical-patterns.md` sits beside the solutions, so a plain glob of the KB reads it.
- **66 of 100 runs escaped**, all four arms alike. In this cloud container most are harmless: `~` guessed as `/home/user` (the path doesn't exist) and reads of the session's own memory dir under `/tmp/claude/memory`. The rest reach this repo or its installed plugin, which only helps the no-skill arm. The checkout does hold a copy of the registry fixture under `evals/fixtures/home`, but no run read it: the one no-skill run that grepped the checkout searched its `knowledge/` dir. So the kills above stand; the `--exclude-escaped` view keeps too few no-skill rows to say anything. A future run can pass c2e2 and c4e4 through that leak, so check traces for `evals/fixtures` before trusting a no-skill pass there.
