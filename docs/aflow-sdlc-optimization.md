<!-- ABOUTME: Design note applying AFlow-style MCTS workflow optimization to the autonomous-sdlc loop. -->
<!-- ABOUTME: Maps AFlow's assumptions onto the plugin, proposes a scored/searched workflow-genome design. -->

# AFlow for the SDLC Loop: Scored, Searched Workflow Evolution

**Status**: Proposed design (not yet implemented)
**Target**: autonomous-sdlc (post-v2.1), composing with autoloop
**Companion**: `docs/sdlc-loop-redesign.md` (the v2 loop this optimizes)

## 1. What AFlow Does (and What It Quietly Assumes)

AFlow (Zhang et al., ICLR 2025) treats an agentic workflow as a **code-represented
graph** — nodes are LLM-invoking actions, edges are plain code — and searches the space
of workflows with MCTS:

1. Initialize the tree with a template workflow.
2. **Select** a node using a soft mixture of score and uniform exploration.
3. **Expand**: an LLM proposes a modified workflow *conditioned on the parent's
   evaluation performance* (its failure log).
4. **Execute and evaluate** the new workflow against a benchmark.
5. Keep the child only if it improves within a budget of rounds.
6. Stop when the top-k average score plateaus or the budget is exhausted.

The loop is simple; the preconditions are not. AFlow works because it has:

- **Cheap, repeatable evaluation** — hundreds of executions against fixed benchmark
  problems (HumanEval, GSM8K) with **ground truth**, so a score is a pass rate, not a
  judgment call.
- **A machine-manipulable workflow representation** — the LLM edits a small Python
  graph drawn from a *constrained operator set* (Ensemble, Review, Revise…), not
  arbitrary prose.
- **Low-noise scalar scores** — averaging over many problems per evaluation.

Any honest port to the SDLC loop has to reconstruct or substitute each of these.

## 2. Why the Naive Port Fails

| AFlow assumes | The SDLC loop has |
|---|---|
| Evaluation = seconds, repeatable, hundreds of runs | Evaluation = one full feature build: hours of wall-clock, real tokens, non-repeatable task |
| Workflow = small code graph the LLM can rewrite | Workflow = a prose `SKILL.md` dispatch table + agents + hooks; free-editing it is unreviewable — and the loop **auto-approves its own actions**, so a self-edited workflow is a self-modifying autonomous system |
| Ground-truth score per problem | "Was this feature built well?" has no oracle; the PR review happens after the loop exits |
| Noise averaged over a benchmark | n=1 per (task, workflow) pair; tasks are not i.i.d. |

So: no MCTS over raw `SKILL.md` edits, evaluated by vibes, one real feature at a time.
That version burns money and converges on nothing.

## 3. What Already Maps: The Plugin Is Half an AFlow

The interesting discovery is how much of AFlow's machinery the v2 loop already ships —
unscored and unsearched:

| AFlow component | Existing counterpart | What's missing |
|---|---|---|
| Workflow representation | The loop's **config surface**: budgets, review-gate config (`reviewers`/`mode`), signs, dispatch-table behavior knobs | Not reified — scattered across `state.json`, `signs.md`, and prose; unversioned |
| Execute + trace | Every real `/sdlc` run writes a **complete execution trace**: `state.json` `history` (every transition, timestamped, with reason), `attempts`, `wait_ticks`, `decisions.jsonl`, `progress.md` | The trace is **discarded** at DONE; nothing computes a score from it |
| Expand (LLM proposes a modification conditioned on the failure log) | **`signs.md` + the feedback skill**: after watching the loop err, a guardrail line is added and replayed every iteration; `feedback consolidate` graduates durable ones | No score, no selection, no rollback — signs accumulate **monotonically whether or not they help**. This is expansion without evaluation |
| Evaluator harness | **autoloop**'s seven components: mutable artifact, scalar metric, immutable runner, quality gates, git checkpoint/rollback, results ledger | Never pointed at the SDLC workflow itself |
| Benchmark problems | `evals/` fixture datasets (skill-trigger evals) | No end-to-end SDLC task suite |

AFlow's contribution, seen from here, is exactly the four missing pieces: **a score, a
ledger, a selection rule, and a tree of variants instead of a monotone pile of signs.**

## 4. Design: Three Tiers

Each tier is independently useful; each later tier consumes the previous one.

### Tier 1 — Score every run (free telemetry, no search)

Extend `sdlc_state.py` with a `score` command that computes a scalar from the trace at
terminal states, and have the DONE/BLOCKED path append a **run record** to a durable
ledger before `.sdlc/` markers are cleaned:

```
~/.claude/autonomous-sdlc/runs.jsonl       # cross-project, like feedback storage
{"at": "...", "repo": "...", "feature": "user-auth", "genome": "sha256:ab12…",
 "outcome": "DONE", "score": 0.74, "iterations": 21, "tasks_closed": 6,
 "rework": {"verify_bounces": 1, "review_roundtrips": 1, "repairs": 0},
 "attempts_exceeded": 0, "wait_ticks": 40, "pr": "https://…"}
```

**Score function** (v1, weights to be tuned once data exists):

```
score = 0.5 * outcome            # DONE-with-PR = 1.0, BLOCKED = 0.0
      + 0.2 * efficiency         # 1 / (1 + iterations_per_closed_task - baseline)
      + 0.2 * (1 - rework_rate)  # backward transitions / total transitions
      + 0.1 * autonomy           # 1 - (attempts_exceeded + escalations) / tasks
```

**Secondary metrics — tracked, never optimized** (autoloop's Goodhart guard):
wall-clock, `wait_ticks`, decision count, and (future) post-merge signal — human review
comments on the PR, reverts of loop commits. If a genome improves the score while
secondary metrics degrade, that is a red flag, not a win.

Tier 1 alone already answers a question the plugin can't answer today: *did that sign
we added last month actually help?*

### Tier 2 — Reify the workflow genome

Make the config surface explicit and hashable. A **genome** is a single JSON document —
`.sdlc/workflow.json`, written at `init`, immutable for the lifetime of a run:

```json
{
  "genome_version": 1,
  "budgets": { "max_iterations": 50, "max_attempts_per_task": 3 },
  "review": { "reviewers": ["code-review"], "mode": "block", "roundtrip_budget": 2 },
  "policy": {
    "parallel_builder_threshold": 3,
    "simplify_before_ship": true,
    "plan_granularity": "default",
    "spec_depth": "default"
  },
  "signs": ["Sign: don't assume the helper exists — check first"],
  "overlays": { "BUILD": "", "VERIFY": "", "REVIEW": "" }
}
```

- The loop reads it in the iteration ritual; signs move here from `signs.md` (which
  becomes the *inbox* for candidate signs, promoted into the genome by the optimizer).
- `overlays` are bounded prompt additions per state — the constrained analogue of
  AFlow editing a node's prompt.
- Run records carry the genome's content hash, so the ledger links every score to the
  exact workflow that produced it.

This is AFlow's "workflow as code," with the same move AFlow itself makes: **mutation
is confined to a declared parameter space** (its operator set; our schema), not
arbitrary edits. The `SKILL.md`, agents, and hooks stay fixed — they are the *substrate*,
the genome is the searchable part.

### Tier 3 — The optimizer: MCTS-lite over genomes

A new `sdlc-optimize` skill (plus `/sdlc-optimize` command) owning a variant tree at
`~/.claude/autonomous-sdlc/optimize/tree.json`. Nodes are genomes with score statistics
`{n, mean, var}`; each edge records the modification that produced the child.

One optimization round, mirroring AFlow steps 2–5:

1. **Select** — soft mixture, as in the paper: with probability ε (default 0.2) pick a
   uniform-random node; otherwise softmax over the top-k nodes' **pessimistic** scores
   (`mean − stderr`, so an n=1 fluke doesn't dominate selection).
2. **Expand** — the LLM proposes **one** modification to the selected genome,
   conditioned on that genome's *failure log*: the lowest-scoring run traces, excerpted
   where points were lost (repeated REVIEW→BUILD bounces, `EXCEEDED` tasks, the
   `BLOCKED` reason). Output must validate against the genome schema — an invalid
   proposal is rejected and retried, never patched around.
3. **Evaluate** — two modes:
   - **Shadow mode** (slow, free, noisy): the child genome becomes the active genome
     for the next K real `/sdlc` runs; Tier 1 scores accrue to it.
   - **Benchmark mode** (repeatable, costs tokens): headless runs over a fixture suite
     — see below.
4. **Keep/backprop** — add the child to the tree only if its mean over its evaluation
   budget beats the parent's; otherwise record the failed edge (so expansion doesn't
   re-propose it) and discard.
5. **Stop** — top-k average plateaus for R consecutive rounds (default 3) or the round
   budget (default 10) is exhausted. The winner is offered to the user as the new
   default genome — and durable signs graduate to `feedback save`, exactly the
   existing consolidation path, now score-backed.

### Benchmark mode composes with autoloop

Benchmark mode is not new machinery — it is **an autoloop whose mutable artifact is the
genome**:

| autoloop component | Instantiation |
|---|---|
| Mutable artifact | the candidate genome JSON |
| Immutable context | `evals/sdlc-bench/` fixture repos + task specs |
| Runner (`auto/run.sh`) | for each bench task: clone fixture to scratch, `claude -p "/sdlc '<task>'"` headless with the candidate genome and small budgets (`max_iterations` ≈ 15), then run the fixture's **held-out acceptance tests** against the produced branch, then `sdlc_state.py score` |
| Primary metric | mean composite: held-out pass rate × trace score |
| Secondary metrics | wall-clock, iterations, token spend |
| Quality gates | genome schema validation (hard fail) before any run |
| Checkpoint/rollback | git commit the genome on improvement, reset on regression |
| Ledger | `results.tsv` — one row per (genome, task) |

The held-out test suite is the important recovery: fixture tasks ship acceptance tests
the loop never sees, which restores AFlow's **ground truth** property. A 3–5 task suite
(small Python repos: add a feature, fix a bug with a regression test, refactor under
tests) lives in `evals/sdlc-bench/` alongside the existing eval fixtures.

## 5. Cost and Noise, Honestly

- **Benchmark runs are expensive.** One bench task ≈ one small headless loop — minutes
  and real tokens. AFlow-scale search (hundreds of evaluations) is out. Defaults are
  sized accordingly: 10 rounds × 3 tasks × 1 seed ≈ 30 loop runs per optimization
  session, overnight-shaped — exactly autoloop's operating envelope. Baseline scores
  are computed once and reused.
- **Shadow-mode scores are noisy and non-i.i.d.** Real features differ wildly in
  difficulty. Mitigations: pessimistic scoring (above), a minimum n before a child can
  displace its parent, and preferring genome deltas that plausibly generalize (budget
  and gate changes) over task-shaped ones.
- **Sequence the tiers.** Tier 1 costs almost nothing and creates the dataset. Do not
  build Tier 3 before Tier 1 has accumulated enough real-run records to sanity-check
  the score function against human judgment of "that run went well."

## 6. What We Deliberately Do NOT Do

- **No self-editing of `SKILL.md`, agents, or hooks by the optimizer.** Mutation is
  confined to the genome schema. Graduating a proven overlay into the skill text
  remains a human-reviewed PR — the optimizer produces the *evidence*, not the commit.
  (A system that auto-approves its own actions must not also choose its own rules.)
- **No mid-run mutation.** A genome is fixed for a run's lifetime; scores attribute
  cleanly.
- **No optimizing secondary metrics**, ever. They exist to veto, not to climb.
- **Signs are not deleted as a concept** — they become genome content with scores
  attached, which finally makes bad signs *removable*. Today's append-only `signs.md`
  is expansion without evaluation; that is the one part of the current design this
  proposal retires.

## 7. New Pieces and Migration

```
plugins/autonomous-sdlc/
├── scripts/
│   └── sdlc_state.py          # + `score` command, + run-record append at DONE/BLOCKED
├── skills/
│   └── sdlc-optimize/         # NEW (Tier 3): tree ops, select/expand/evaluate/keep
│       └── SKILL.md
├── commands/
│   └── sdlc-optimize.md       # NEW: kick off / resume an optimization session
evals/
└── sdlc-bench/                # NEW (Tier 3): fixture repos + task specs + held-out tests
```

1. **Tier 1** — `score` command + run ledger + genome extraction of the knobs that
   already exist (budgets, review config, signs). No behavior change; pure telemetry.
2. **Tier 2** — loop reads `.sdlc/workflow.json`; `signs.md` becomes the inbox.
3. **Tier 3 (benchmark)** — `evals/sdlc-bench/` suite + autoloop-generated runner.
4. **Tier 3 (search)** — the `sdlc-optimize` skill; dogfood one overnight session on
   the bench suite before touching shadow mode.

## Sources

- [AFlow: Automating Agentic Workflow Generation (Zhang et al., ICLR 2025)](https://arxiv.org/abs/2410.10762)
- `docs/sdlc-loop-redesign.md` — the loop being optimized, and its signs/feedback mechanism
- `plugins/autoloop/skills/autoloop/SKILL.md` — the seven-component evaluator harness reused by benchmark mode
- [Anthropic Engineering — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
