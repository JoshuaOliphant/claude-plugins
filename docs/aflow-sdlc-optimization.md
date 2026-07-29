<!-- ABOUTME: Design note for learning from every autonomous-sdlc run: capture traces, score them, -->
<!-- ABOUTME: and periodically feed them back into the SDLC skill via retrospectives. AFlow-inspired. -->

# Learning From Every Run: Feeding SDLC Traces Back Into the Skill

**Status**: Proof of concept implemented in autonomous-sdlc v2.4.0 — capture + score
(`sdlc_state.py score` / archive-on-terminal-transition), retro tooling
(`sdlc_retro.py digest|mark`), and the `/sdlc-retro` skill. The measure loop (§6)
activates once real ledger data accumulates.
**Target**: autonomous-sdlc (post-v2.1)
**Companion**: `docs/sdlc-loop-redesign.md` (the loop being improved),
`docs/compound-engineering-roadmap.md` (this is the "compound" step applied to the loop itself)

> **Revision note.** The first draft of this note proposed benchmark-driven MCTS over
> workflow variants as the primary mechanism (per AFlow, Zhang et al., ICLR 2025).
> Discussion inverted that: the primary mechanism is now **capturing every real run and
> periodically feeding the accumulated results back into the skill**. Deliberate search
> survives as future work (§8). AFlow still supplies the conceptual skeleton — score,
> ledger, LLM-proposed modification conditioned on failure logs, keep-only-if-improved —
> but evaluation is amortized over normal usage instead of purchased with benchmark runs.

## 1. The Problem: The Loop Learns Nothing From Itself

Every `/sdlc` run produces a complete execution trace and then throws it away:

- `state.json` `history` — every transition, timestamped, with a reason. The rework
  story (VERIFY→BUILD bounces, REVIEW round-trips, REPAIR entries) is right there.
- `attempts`, `wait_ticks`, `iteration` — where effort actually went.
- `decisions.jsonl` — every autonomous judgment call (kept in the PR body, but never
  aggregated across runs).
- `progress.md`, `signs.md`, `escalation.md` — the narrative, the guardrails in force,
  and why the loop gave up when it did.

The DONE state "cleans `.sdlc/` markers"; BLOCKED runs — the most informative ones —
leave their trace stranded on an abandoned branch. Meanwhile the only improvement
mechanism, `signs.md` + the feedback skill, is **append-only expansion with no
evaluation**: a sign added after one bad iteration is replayed forever, whether or not
it ever helped, and nothing ever removes one.

In AFlow's terms: the plugin already has *execution* and *expansion*, but no *score*,
no *ledger*, no *selection*, and no way to check whether a modification improved
anything.

## 2. The Flow

```
                     every real /sdlc run                    periodically (human-invoked)
                ┌──────────────────────────┐            ┌────────────────────────────────┐
   /sdlc ──────►│ run loop ──► DONE/BLOCKED│            │ /sdlc-retro                    │
                │        │                 │            │   mine ledger since last retro │
                │        ▼                 │            │   ──► ≤5 grounded proposals    │
                │  archive trace + score ──┼──────────► │   ──► PR against the plugin    │
                │  (runs ledger, durable)  │   ledger   │        (human reviews, merges) │
                └──────────────────────────┘            └───────────────┬────────────────┘
                         ▲                                              │
                         │            next period's runs evaluate       │
                         └──────────── the merged changes ◄─────────────┘
                                       (next retro checks: did it help?)
```

Four stages, each independently shippable: **capture** (§3), **score** (§4),
**retro** (§5), **measure** (§6).

## 3. Capture: Archive Every Run, Automatically

Hook the archive into the terminal transition — `sdlc_state.py` archives whenever the
state becomes `DONE` **or** `BLOCKED` (including budget/no-progress force-blocks, which
go through the same `block()` path). Not a dispatch-table instruction the model can
forget; a side effect of the state machine it already must call.

**Where**: user-level, cross-project — learning should compound across repos, exactly
like the feedback skill's storage:

```
~/.claude/autonomous-sdlc/
├── runs.jsonl                          # one summary line per run (the ledger)
└── runs/2026-07-08T05-41_claude-plugins_user-auth/
    ├── state.json                      # full history, attempts, budgets, review config
    ├── decisions.jsonl
    ├── progress.md
    ├── signs.md                        # the guardrails that were in force
    └── escalation.md                   # when BLOCKED
```

**Ledger line** (the retro's primary input; the directory is the drill-down):

```json
{"at": "...", "repo": "claude-plugins", "feature": "user-auth",
 "plugin_version": "2.1.0", "outcome": "DONE", "score": 0.74,
 "iterations": 21, "tasks_closed": 6, "attempts_exceeded": 0,
 "rework": {"verify_bounces": 1, "review_roundtrips": 1, "repairs": 0},
 "wait_ticks": 40, "decisions": 9, "signs_active": 3,
 "blocked_reason": null, "pr": "https://…"}
```

`plugin_version` (read from the installed plugin's `plugin.json`) is the load-bearing
field: it is what lets a later retro attribute score changes to a skill change (§6).

Everything stays local to the user's machine; traces contain project narrative
(`progress.md` may quote code), so nothing is transmitted anywhere — the retro reads
the archive in place.

## 4. Score: One Number Per Run

Computed at archive time from the trace (`sdlc_state.py score`, also runnable ad hoc):

```
score = 0.5 * outcome            # DONE-with-PR = 1.0, BLOCKED = 0.0
      + 0.2 * efficiency         # 1 / (1 + iterations_per_closed_task - baseline)
      + 0.2 * (1 - rework_rate)  # backward transitions / total transitions
      + 0.1 * autonomy           # 1 - (attempts_exceeded + escalations) / tasks
```

Weights are a starting point, to be sanity-checked against the human's own sense of
"that run went well" once a dozen records exist — before any retro acts on them.

**Secondary metrics — tracked, never optimized** (the Goodhart guard, borrowed from
autoloop): wall-clock, `wait_ticks`, decision count, and (future) post-merge signal —
human review comments on the loop's PRs, reverts of loop commits. A skill change that
raises scores while secondary metrics degrade is a red flag, not a win.

## 5. Retro: Periodically Feed the Results Back

A new `/sdlc-retro` command + `sdlc-retro` skill. Human-invoked ("periodically" is a
human judgment); the SHIP step may *nudge* — "14 runs since the last retro, consider
`/sdlc-retro`" — but never self-invokes.

One retro session:

1. **Load** all ledger lines since the last retro marker; drill into the archive
   directories of the worst-scoring runs (the failure log, in AFlow's sense).
2. **Mine for patterns** across runs — the checklist, roughly in order of value:
   - Recurring **BLOCKED reasons** (budget? no-progress? same escalation shape twice?)
   - **Rework clusters** — which state pairs bounce most; what the transition `reason`
     strings have in common (e.g. "REVIEW keeps finding missing error handling" →
     candidate Builder-prompt or sign change).
   - **Attempts-exceeded** task shapes — what kinds of tasks burn 3 strikes.
   - **Iteration sinks** — states consuming disproportionate ticks vs. work produced
     (e.g. chronic `wait_ticks` → the waiting guidance isn't landing).
   - **Sign audit** — for each active sign, compare scores of runs with vs. without
     it. Signs are finally *removable*: an unhelpful one becomes a removal proposal.
   - **Decision audit** — decisions that later correlate with REPAIR/rework.
3. **Propose ≤5 concrete changes**, each citing the runs that motivate it
   (`runs.jsonl` line refs). Eligible targets — the plugin source in this repo:
   - `sdlc-loop/SKILL.md` dispatch-table prose (the workflow itself),
   - default budgets and review-gate defaults in `sdlc_state.py`,
   - Architect/Builder agent prompts,
   - sign graduation into skill text, or sign removal,
   - the score weights themselves (flagged as such — changing the ruler is allowed
     but must be its own proposal, never bundled with changes measured by it).
4. **Deliver as a PR** against `claude-plugins` on a branch, one commit per proposal,
   with the evidence in the PR body. The human reviews and merges — the retro **never
   self-merges** (§7). A `retro.json` marker (date, ledger position, plugin version,
   proposals) is written so the next retro knows its window and what to measure.

**Consumer mode.** Marketplace users who can't edit the plugin get the same retro with
a different output channel: proposals land as feedback-skill entries and `signs.md`
candidates (the existing `feedback save`/`consolidate` path) instead of a source PR.
Author mode is the primary target — it is how the skill itself compounds.

## 6. Measure: Did the Last Change Help?

This is AFlow's "keep only if improved," amortized over real usage. Each retro's first
act is to grade the previous one:

- Partition ledger lines by `plugin_version` (before vs. after the last merged retro
  PR); compare score windows — pessimistically (`mean − stderr`), with a minimum n
  (default 5 runs) before any conclusion is drawn.
- Improved or neutral → note it in the new retro PR and move on.
- Regressed → the first proposal of the new retro is a **revert** of the offending
  change, with the two windows as evidence.

Honest caveats, and why this is still enough: real features are not i.i.d. — a bad
fortnight of gnarly tasks can sink a window. The pessimistic comparison, the minimum
n, and the fact that a human reviews every conclusion (this is a PR gate, not an
autonomous actuator) keep noise from compounding. What this design gives up relative
to benchmark-driven search is *statistical crispness*; what it gains is zero marginal
evaluation cost and scores grounded in the work the user actually cares about.

## 7. Guardrails

- **The retro proposes; the human merges.** The optimizer path never edits skill
  text, agents, or hooks directly — a system that auto-approves its own actions must
  not also choose its own rules. The PR is the boundary.
- **One proposal, one commit, one measurable claim** — so a regression found later is
  revertible at proposal granularity.
- **Secondary metrics veto, never climb** (§4).
- **No mid-run mutation**: whatever skill version a run starts with, it keeps; scores
  attribute cleanly via `plugin_version`.
- **Patterns need ≥2 supporting runs.** A single pathological run makes a `signs.md`
  candidate at most, never a skill-text proposal — that is the existing signs channel
  doing its job at the right altitude.

## 8. Future Work: Deliberate Search (the original AFlow shape)

If passive accumulation plateaus — retros keep coming back empty while scores sit
below where they should be — the ledger and score function built here are exactly the
substrate real search needs. The earlier draft of this note specified it: reify the
tunable surface as a hashable *workflow genome* (`.sdlc/workflow.json`: budgets,
review config, signs, bounded per-state prompt overlays); build a small
`evals/sdlc-bench/` fixture suite whose **held-out acceptance tests** restore ground
truth; drive MCTS-lite over genomes (AFlow's soft-mixture selection over pessimistic
top-k, schema-constrained expansion, keep-if-improved, top-k-plateau stopping) with
**autoloop** as the evaluator harness — the genome is the mutable artifact, the bench
runner emits `METRIC score=…`. Roughly 10 rounds × 3 tasks ≈ 30 headless loop runs,
an overnight-shaped session. None of it is needed until the cheap loop stops paying.

## 9. Migration

1. **Capture + score** — `sdlc_state.py`: archive-on-terminal-transition, `score`
   command, ledger append. Pure telemetry; no behavior change; test alongside the
   existing `test_sdlc_state.py` suite.
2. **Ledger bake-in** — run real features for a while; sanity-check scores against
   human judgment; tune weights once.
3. **`/sdlc-retro`** — command + skill (author mode first), including the
   measure-previous-retro step and the `retro.json` marker.
4. **Consumer mode** — feedback-skill output channel.
5. **(Optional, later)** genome + bench suite + MCTS per §8.

## Sources

- [AFlow: Automating Agentic Workflow Generation (Zhang et al., ICLR 2025)](https://arxiv.org/abs/2410.10762)
- `docs/sdlc-loop-redesign.md` — the loop, its signs/feedback mechanism, and the state CLI this extends
- `docs/compound-engineering-roadmap.md` — "every unit of work should make the next unit easier"; this note is that principle applied to the loop itself
- `plugins/autoloop/skills/autoloop/SKILL.md` — secondary-metric guardrails; the evaluator harness for §8
- [Anthropic Engineering — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
