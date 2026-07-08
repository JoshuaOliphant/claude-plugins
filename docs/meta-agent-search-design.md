# Meta-Agent Search over Plugin Workflows (ADAS applied to oliphant-plugins)

**Status**: Proposed design (not yet implemented)
**Prompted by**: Automated Design of Agentic Systems (ADAS; Hu et al. 2025) — "meta-agent
search", where a meta-agent proposes new agentic workflow designs, evaluates them, and
archives the winners. Workflow design is a search problem; we should be able to find good
designs by algorithm, not only by hand.

## 1. Thesis

Every plugin in this marketplace is a hand-crafted point in an enormous design space:
skill descriptions, skill procedures, agent prompts, state graphs, gate orderings, hook
configurations. We iterate on them by intuition and dogfooding. ADAS says: treat each of
those artifacts as a **genome**, define a **fitness function**, and let a **meta-agent**
run the search.

This repo is unusually well positioned to try this, because two of the three ADAS
ingredients already exist here:

| ADAS ingredient | ADAS paper | This repo — already have |
|---|---|---|
| Seed archive of simple agents | CoT, self-refine, debate | Nine hand-crafted plugins; each is a working, non-trivial seed |
| Search loop harness | Bespoke Python driver | `autoloop`: program.md + immutable `auto/run.sh` + `METRIC` contract + git checkpoint/rollback |
| Fitness function | Held-out benchmark accuracy | **Missing** — but `evals/*.json` is 90% of a cheap one |

The missing piece is small: an eval runner that turns `evals/*.json` into a scalar, and a
meta-agent protocol that proposes candidates instead of hill-climbing a single file.

## 2. What the genome is here

ADAS searches over Python programs. Our "programming language" is the Claude Code plugin
format — SKILL.md files, agent frontmatter + prompts, hooks.json, and (for
autonomous-sdlc) the state machine in `sdlc_state.py`. This is a *better* genome than
free-form code in one important way: it is declarative and mechanically gate-checkable
(`check_marketplace_versions.py`, `sync_shared.py`, hooks JSON parsing, `pytest` on the
Python helpers) before any expensive evaluation runs.

The search spaces, ordered by evaluation cost:

| Tier | Genome (what the meta-agent may mutate) | Fitness signal | Cost per candidate |
|---|---|---|---|
| **1 — Trigger surface** | The `description` field of one SKILL.md | Trigger accuracy against `evals/<skill>-eval.json`, judged by haiku | Seconds, ~cents |
| **2 — Skill procedure** | SKILL.md body + `references/*.md` | Rubric-judged output quality on fixture tasks (e.g. mochi-creator already ships prompt-quality validation criteria) | Minutes |
| **3 — Whole workflow** | autonomous-sdlc: state graph transitions, Architect/Builder prompts, gate order, loop Stop-hook prompt | Task success rate, iterations-to-green, token cost on a benchmark suite of small repos | Hours |

Structural validity (plugin.json parses, hooks load, Python compiles, versions sync) is
**not** fitness — it is the quality-gate layer, exactly as in autoloop: gates fail fast
so no benchmark time is wasted on a malformed candidate.

## 3. Architecture

### 3.1 The archive

```
meta/
├── archive/
│   ├── index.jsonl                  # one line per candidate: id, parents, tier, scores
│   └── {candidate-id}/
│       ├── genome/                  # the mutated files (mirror of plugin-relative paths)
│       └── meta.json                # idea description, lineage, fitness per eval,
│                                    # dev vs holdout scores, tokens spent
└── benchmarks/                      # tier-3 only: task suite definitions
```

Seeded with:
- **Candidate 0**: the current committed workflow, verbatim (the hand-crafted incumbent).
- **2–3 deliberately simple baselines**, analogous to ADAS seeding with CoT/self-refine.
  For tier 3: "single pass, no gates", "build once + self-refine once". These anchor the
  low end so fitness deltas are interpretable and give the meta-agent structurally
  diverse inspiration.

Following ADAS, every candidate that passes the gates is archived *with its scores* —
selection pressure is applied at proposal time (inspiration is sampled weighted by
fitness), not by discarding losers. Failed ideas are cheap negative examples.

### 3.2 The meta-agent loop

One iteration, mapping ADAS steps onto Claude Code mechanics:

1. **Read** `meta/archive/index.jsonl` + the top-k candidates' `meta.json` ideas.
2. **Propose**: write a high-level prose description of a new workflow first. Forced
   novelty framing: the description must name which archive entries inspired it and
   state, in one sentence, how it differs from *each* of its parents.
3. **Implement**: materialize the idea as files under `meta/archive/{new-id}/genome/`.
4. **Self-refine ×2** (Madaan et al. 2023, as in ADAS):
   - Pass A — *novelty check*: compare against the archive; if it is a re-skin of an
     existing candidate, revise or abandon.
   - Pass B — *feasibility check*: do referenced files exist, do hooks parse, does the
     procedure contradict itself, does it violate repo invariants (e.g. VERIFY/REVIEW
     must call built-in skills, `/goal` stays user-only)?
5. **Evaluate**: run the immutable runner (gates → fitness eval → `METRIC` lines).
6. **Archive**: append to `index.jsonl` with scores; `git commit` the candidate dir.
7. Repeat until `--max-iterations` or token budget.

This is autoloop's seven components with two deliberate deviations, which is why it is a
sibling protocol rather than a stock autoloop `program.md`:

- **Mutable artifact** is not one file edited in place — it is a *new directory per
  iteration* (population, not trajectory). Checkpoint/rollback becomes append/skip.
- **Keep/revert** is not metric-gated — gates decide archival, the metric only steers
  future sampling. Hill-climbing would converge on one lineage; ADAS's results come from
  breadth.

Everything else carries over verbatim: immutable runner, `METRIC key=value` contract,
`results.tsv` ledger, embedded progress log, tiered fastest-first gates, launch via
`claude --dangerously-skip-permissions -p "Read program.md and execute the loop protocol."`.

### 3.3 The fitness function (tier 1 — build this first)

`evals/run_trigger_eval.py`:

- Input: a SKILL.md path (or raw description) + an `evals/*-eval.json` file.
- For each case, ask a judge model (haiku — cheap, and trigger decisions are made by a
  small router-shaped judgment anyway) whether the description would fire for the query,
  given a realistic "available skills" context so the judge sees competing descriptions.
- Output: `METRIC trigger_score=<balanced accuracy>` plus secondary metrics.

Scoring detail that matters: report **false-positive rate separately** and weight it
into the primary metric. An over-triggering skill pollutes every unrelated session; a
under-triggering one costs only its own invocations. Balanced accuracy with an FP
penalty, not raw accuracy.

This script is worth building even if the meta-agent never ships: it is a regression
test for every description edit we already make by hand, runnable in CI.

### 3.4 Tier 3: searching the SDLC loop itself

The genome is a variant overlay on `plugins/autonomous-sdlc/`: state-graph edits
(e.g. "merge REVIEW into VERIFY", "add a CRITIQUE state between PLAN and BUILD",
"REPAIR retries twice before BLOCKED"), Architect/Builder prompt rewrites, gate
reordering, loop-prompt wording. The state machine living in `sdlc_state.py` +
`.sdlc/state.json` is what makes this searchable at all — transitions are data, not
vibes.

Evaluation: 3–5 benchmark micro-repos under `meta/benchmarks/` (a repo with failing
tests + a spec; a small feature request; a bug with a reproduction). Each candidate runs
the full loop in a disposable git worktree (reuse `hooks/scripts/worktree-create.sh` /
`worktree-remove.sh`), headless, with a hard iteration ceiling and token budget.

```
fitness = w1·success_rate − w2·norm(tokens) − w3·norm(wallclock)
secondary (tracked, not optimized): diff size, test count delta, BLOCKED rate
```

This is the true ADAS regime and the expensive one — hours per candidate. It is phase 3
for a reason: the tier-1 pilot debugs the archive/meta-agent/runner machinery for cents
before any candidate costs hours.

## 4. Goodhart defenses

The eval sets are small (~10–40 cases each), so overfitting is the default outcome, not
a tail risk.

1. **Dev/holdout split**: each `evals/*.json` is split once (e.g. 70/30, committed, never
   reshuffled). The meta-agent sees and optimizes dev scores only; `run.sh` emits both;
   the holdout number is what a human reads when deciding whether a winner is real.
2. **Secondary guardrail metrics**: description token count (tier 1 — blocks the
   degenerate "enumerate every trigger phrase" solution), diff size and test-delta
   (tier 3 — blocks "delete the hard parts").
3. **Winners land as PRs, never auto-merge.** The search loop only ever writes under
   `meta/`. Promoting a winning genome back into `plugins/` is a human-reviewed PR with
   the usual version bump + marketplace sync. The meta-agent proposes; the human ships.
4. **Immutable runner** (autoloop's rule, unchanged): the meta-agent can never touch
   `auto/run.sh`, the eval JSONs, or the judge prompt. The optimizer must not hold the
   measuring stick.

## 5. Where it lives

Recommendation: **repo-level `meta/` + `evals/run_trigger_eval.py`, not a new plugin.**
Like `evals/`, this is tooling *about* this repo's artifacts, not a capability to
distribute — it references our eval fixtures and our plugins in place. Graduate it to a
plugin only if the protocol proves general enough to point at someone else's skills
directory. This also keeps the marketplace catalog untouched (no `metadata.version`
bump, no new sync surface) while the idea is unproven.

`autoloop` stays as-is. The meta-search `program.md` is written fresh following
autoloop's conventions (same runner contract, same ledger) rather than generated by the
autoloop skill, because of the population-vs-trajectory deviation in §3.2.

## 6. Phased plan

| Phase | Deliverable | Exit criterion |
|---|---|---|
| **1 — Fitness function** | `evals/run_trigger_eval.py` + dev/holdout split + baseline scores for all nine current skill descriptions, committed to `meta/archive/` as candidate 0 | Baseline table exists; runner is deterministic enough that re-runs agree within noise |
| **2 — Pilot search** | Meta-search `program.md` + `auto/run.sh`; overnight run on the *single worst-scoring* description from phase 1 | ≥1 candidate beats the incumbent on **holdout**, or we learn the eval is saturated |
| **3 — Procedure search** | Tier-2 rubric evals for one skill (mochi-creator, which already has quality criteria) | Rubric-judged wins that survive human review |
| **4 — SDLC workflow search** | `meta/benchmarks/` suite + worktree-isolated tier-3 runs over autonomous-sdlc variants | A state-graph or prompt variant beats the incumbent on success rate at ≤ token parity |

Phase 1 is a good afternoon of work and is independently useful. Phase 4 is the headline
but should not be attempted until phases 1–2 have shaken out the archive mechanics.

## 7. Risks and open questions

- **Judge ≠ router.** Tier-1 fitness uses haiku to *simulate* Claude Code's skill
  triggering. If the simulation diverges from the real router, we optimize the wrong
  thing. Mitigation: spot-check winners in a live session before promotion; keep the
  judge prompt frozen per search run so scores are comparable.
- **Eval saturation.** Several descriptions may already score near-perfect on their
  small eval sets. Phase 1's baseline table tells us where search has headroom; where
  there is none, the move is *growing the eval set* (also a candidate meta-agent task,
  but adversarially — one agent proposes hard cases, the fitness judge stays frozen).
- **Tier-3 nondeterminism.** Agentic runs are noisy; one benchmark run per candidate
  will mis-rank. Budget ≥2 runs per candidate and rank on mean; accept that tier 3 is
  a coarse signal.
- **Cost ceiling.** The loop must carry a hard token budget per run (autoloop's time
  budget generalizes); tier 3 especially, where a pathological candidate can loop in
  REPAIR. The benchmark harness kills a candidate at N iterations and scores it failed.
- **Scope of mutation.** Letting the meta-agent touch `hooks/scripts/*.sh` (tier 3)
  means candidate code executes with real permissions during evaluation. Start with
  prompts + state graph only; hook-script mutation needs a sandbox story first.
