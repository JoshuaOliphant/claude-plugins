<!-- ABOUTME: Roadmap mapping this marketplace's plugins onto Every's compound-engineering loop. -->
<!-- ABOUTME: Gap analysis + prioritized action items; design-only, no code changes yet. -->

# Compound Engineering Roadmap

A design note that maps this plugin marketplace against Every's
[Compound Engineering guide](https://every.to/guides/compound-engineering) and the
[official EveryInc plugin](https://github.com/EveryInc/compound-engineering-plugin),
then proposes prioritized improvements.

**Status:** design only — no code changes. Each action item is a candidate, to be
scoped and sequenced separately.

---

## 1. The framework in one screen

**Core claim:** every unit of work should make the next unit *easier*, not harder.
The codebase should get more trustworthy over time, not more fragile.

**The loop (7 steps + debug shortcut):**

```
ideate → brainstorm → plan → work → review → polish → compound
                              (debug = shortcut when the bug is obvious)
```

Three phases: a **human decides what's worth building** (ideate/brainstorm), the
**agent plans/codes/tests/reviews/preps the PR** (plan/work/review/polish), and a
**human judges** whether it's good enough and whether the system *learned* anything
reusable (compound).

**The 50/50 rule** (supersedes the older per-feature 80/20): spend ~50% of total
engineering time shipping features and ~50% improving the system — review agents,
pattern docs, test generators. "An hour spent creating a review agent saves 10 hours
of review over the next year." *This entire marketplace is the 50%.*

**The five-stage maturity ladder:**

| Stage | Mode |
|-------|------|
| 0 | Manual development |
| 1 | Chat-based assistance (copy-paste) |
| 2 | Agentic tools, line-by-line review |
| 3 | Plan-first, PR-only review ← *compound engineering begins here* |
| 4 | Idea → PR on a single machine |
| 5 | Parallel cloud execution, proactive agents |

**Core principles worth pinning:** taste belongs in systems not in review · teach the
system, don't do the work yourself · build safety nets, not gatekeeping · make
environments agent-native · plans are the new code · assign outcomes, not tasks.

---

## 2. Current state: plugins mapped to the loop

| Loop step | Plugin / mechanism | Maturity |
|-----------|--------------------|----------|
| Ideate | — | **missing** |
| Brainstorm | — | **missing** |
| Plan | `autonomous-sdlc` → `architect` agent | strong |
| Work | `autonomous-sdlc` → `builder` + worktree isolation | strong |
| Review | `autonomous-sdlc` → single `validator` (format/lint/type/test) | **thin** |
| Polish | `verify` / `run` skills, `hexagonal-agents` (adjacent, not owned) | partial |
| Compound | `compound-knowledge` (capture + retrieve), cross-project registry | strong |
| Meta-compound | `feedback` skill in every plugin (corrects the *plugins themselves*) | unique |
| Optimization loop | `autoloop` (Karpathy-style scalar-metric experiment loop) | strong |

**The headline finding:** the pieces of the loop exist, but they live in **separate
plugins that don't call each other**. `compound-knowledge` *is* the Compound step, yet
`autonomous-sdlc`'s architect never retrieves past lessons before planning, and its
integrator/documenter never captures learnings after. Two siblings that ignore each
other, instead of one closed loop.

The `feedback` skill is a genuinely distinctive asset — it's compound thinking applied
one level up (improving the plugins, not just the user's code). The guide has no direct
equivalent. Worth keeping and leaning into.

---

## 3. Gap analysis

### G1 — The loop is open (highest leverage)
The guide's `/ce-code-review` wires a **learnings-researcher** in as a reviewer, and its
compound step **feeds the planner next time**. Here, retrieve/capture and plan/review
are disconnected. Closing this turns the two strongest plugins into one engine.

### G2 — Review is a single gate, not a panel
`autonomous-sdlc` has one `validator`. The guide runs a **diff-aware panel**:
- *Always-on:* correctness, testing, maintainability, project-standards (reads `CLAUDE.md`), agent-native, **learnings-researcher**.
- *Conditional (by diff):* security (auth/secrets), performance (queries/loops), API-contract (routes/types), data-migrations, reliability (retries/jobs), adversarial (large diffs).
- Findings prioritized **P1/P2/P3**, fixes **re-validated**, patterns **captured** → review feeds compound.

### G3 — The corpus has no gardening
`compound-knowledge` has capture + retrieve but no equivalent of **`/ce-compound-refresh`**
(prune/merge/replace/archive stale, duplicate, or obsolete learnings). Without it the
solutions corpus rots and retrieval precision degrades.

### G4 — Compound writes files but doesn't update the living context
The guide's compound step ends by editing **`CLAUDE.md`/`AGENTS.md`** — the file read
every session. Here, capture writes solution docs and a `critical-patterns.md`, but
rarely *promotes* a hard-won lesson into the always-loaded context.

### G5 — No owner for Ideate / Brainstorm / Polish
Three loop steps have no home. Ideate/Brainstorm (ambiguity → scoped requirements,
saved to `docs/brainstorms/`) and Polish (drive the running app, judge UX) are absent.
`verify`/`run` and `hexagonal-agents` are adjacent but don't own the steps.

### G6 — The collection isn't positioned against the ladder
Each plugin moves a user up a specific rung, but nothing says so. The marketplace reads
as five tools rather than one staged system.

---

## 4. Prioritized action items

Ordered by leverage. Each is independently shippable.

### P1 — Close the loop (`autonomous-sdlc` ↔ `compound-knowledge`)
- Architect's first action: invoke `compound-retrieve` (or its `knowledge-researcher`
  agent) and fold prior lessons into the plan.
- Integrator/documenter's last action: invoke `compound-capture` on what was learned.
- Add `compound-retrieve` as a **reviewer** ("learnings-researcher") in the review step.
- *Why first:* delivers most of the compounding value using only what already exists.
- *Touches:* `autonomous-sdlc/agents/architect.md`, `integrator.md`, `documenter.md`;
  version bumps in both `plugin.json`s + `marketplace.json`.

### P2 — Reviewer panel (`autonomous-sdlc`)
- Promote `validator` into an orchestrator that selects reviewers by diff content
  (start with: correctness, testing/maintainability, security, performance, learnings).
- Emit P1/P2/P3 findings; re-validate fixes; pipe captured patterns into `compound-capture`.
- Cheap interim step with **zero new agents:** bake the guide's three questions into the
  validator/PR handoff — "hardest decision?", "alternatives rejected?", "least confident?".
- Consider delegating to the existing `/code-review` and `/security-review` skills rather
  than re-implementing.

### P3 — Corpus gardening (`compound-knowledge`)
- Add a `/compound-refresh` skill: scan solutions for stale/duplicate/overlapping entries,
  decide keep/update/merge/replace/archive (mirror the existing feedback `consolidate` action).
- Let `compound-capture` **promote** recurring lessons into `critical-patterns.md` and,
  when project-wide, suggest a `CLAUDE.md` edit (addresses G4).

### P4 — Positioning pass (docs, no code)
- In each plugin README and the marketplace README, state which **ladder rung** the plugin
  enables (e.g. `autonomous-sdlc` = Stage 3→4; `autoloop` + cloud = Stage 5).
- Add a one-paragraph "how these compose into the loop" section to the top-level README.

### P5 — Fill the missing steps (larger, optional)
- A brainstorm/ideate skill that turns ambiguity into a requirements doc in
  `docs/brainstorms/`, handed off to the architect.
- A polish skill that drives the running app (extends `verify`/`run`) and judges UX
  readiness before PR.

---

## 5. Beliefs this collection already embodies (and one to lean into)

The guide's "beliefs to adopt" largely describe what's already here:
- **Plans are the new code** → `autonomous-sdlc` is plan-first.
- **Build safety nets, not review processes** → `verification-stack`, `autoloop` quality gates.
- **Make environments agent-native** → `hexagonal-agents`, worktree isolation.
- **Apply compound thinking everywhere** → `compound-knowledge`.

The one to lean into: **"taste belongs in systems, not in review."** The `feedback`
skill is exactly this — encoding corrections so they're never repeated. It's the most
differentiated thing in the marketplace and under-advertised. Consider making it a
first-class, cross-plugin capability rather than a per-plugin appendage.

---

## 6. Suggested sequence

1. **P1** — close the loop (focused, highest leverage).
2. **P2** — reviewer panel, starting with the free three-questions safety net.
3. **P3** — corpus gardening, so the growing knowledge base stays sharp.
4. **P4** — positioning docs (cheap, makes the system legible).
5. **P5** — ideate/brainstorm/polish, only if the loop above is paying off.
