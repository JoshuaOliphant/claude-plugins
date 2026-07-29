---
name: sdlc-retro
description: >
  Periodic retrospective over the autonomous-sdlc run ledger: mine archived run
  traces for cross-run patterns and feed them back into the SDLC skill as
  grounded, human-reviewed improvement proposals. Trigger: the /sdlc-retro
  command, or the user asking to "review SDLC runs", "improve the SDLC loop from
  its history", or "run a loop retro". Not for use inside an active loop
  iteration.
version: 1.0.0
effort: high
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# SDLC Retro

Every `/sdlc` run archives its full trace (transition history, decisions, signs,
escalations) and a composite score to `~/.claude/autonomous-sdlc/`. This skill
periodically turns that ledger into improvement proposals for the SDLC skill
itself — AFlow's expand-and-keep-if-improved loop, amortized over real usage
(design: `docs/aflow-sdlc-optimization.md` in the marketplace repo).

**The contract: the retro proposes; the human merges.** You never edit shipped
skill text and self-approve it. Every proposal lands as a reviewable diff (author
mode) or a feedback entry (consumer mode).

`RETRO=${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_retro.py` (run with `python3`).

## Procedure

### 0. Digest

```bash
python3 $RETRO digest
```

If `runs < 5`, report that there isn't enough data for patterns yet (say how many
runs exist and that the ledger grows automatically) and stop — do **not** mark a
retro. Otherwise summarize the digest for the user in 3-5 lines before diving in.

### 1. Grade the previous retro first

If `previous_retro` is set, compare `by_plugin_version` windows before vs. after
that retro's `plugin_version`, using the `pessimistic` field and only windows with
`comparable: true`:

- **Improved or neutral** → note it in your final report.
- **Regressed** → your first proposal is a revert of that retro's change, with
  both windows as evidence.
- Either side not `comparable` → say "too early to grade" and move on.

### 2. Mine the window

Drill into the `worst_runs` archive directories (each holds the run's
`state.json`, `decisions.jsonl`, `progress.md`, `signs.md`, `escalation.md`).
Work the checklist, roughly in order of value:

1. **Recurring BLOCKED reasons** — same budget, no-progress, or escalation shape
   across runs?
2. **Rework clusters** — which state pairs bounce most (`rework_totals`), and what
   the transition `reason` strings have in common.
3. **Attempts-exceeded shapes** — what kinds of tasks burn all their strikes.
4. **Iteration sinks** — chronic `wait_ticks`, states eating iterations without
   producing commits.
5. **Sign audit** — compare scores of runs with vs. without each sign
   (`signs_active` + the archived `signs.md`). An unhelpful sign becomes a
   removal proposal — signs are finally removable.
6. **Decision audit** — decisions that later correlate with REPAIR or rework.

### 3. Propose (≤5, each grounded)

Each proposal needs **at least 2 supporting runs**, cited by their `archive`
paths. A single pathological run yields at most a `signs.md` candidate, never a
skill-text proposal. Eligible targets:

- `sdlc-loop/SKILL.md` dispatch-table prose (the workflow itself)
- default budgets / review-gate defaults in `sdlc_state.py`
- Architect / Builder agent prompts
- sign graduation into skill text, or sign removal
- the score weights in `sdlc_state.py` — allowed, but flagged as changing the
  ruler and **never bundled** with proposals measured by it

### 4. Deliver

**Author mode** (the plugin source is a git checkout you can edit — e.g. you are
in the marketplace repo, or the user points you at their clone): create a branch,
apply each proposal as **its own commit** (so a later regression is revertible at
proposal granularity), open a PR whose body lists each proposal with its
supporting runs and the previous-retro grade. Follow the repo's versioning rules.

**Consumer mode** (plugin installed read-only from the marketplace): record each
proposal via the feedback skill
(`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc save ...`)
and present the full proposal text to the user so they can file it upstream.

### 5. Mark

Only after delivering (PR opened or feedback saved):

```bash
python3 $RETRO mark --note "<one line: what this retro proposed>"
```

This windows the next retro. Never mark a retro that produced nothing — leave the
window open so the data keeps accumulating.

## Report

End with: the previous-retro grade, each proposal (one line + supporting-run
count), where they landed (PR URL / feedback entries), and the next step for the
human (review the PR; keep running `/sdlc` to grow the ledger).
