# Invariant Ledger — Design

**Date:** 2026-07-16
**Status:** Design approved; pending implementation plan
**Author:** Joshua Oliphant (with Claude)
**Affects:** `autonomous-sdlc` (currently v2.3.1)

## Context

`autonomous-sdlc` is opinionated about **process** — TDD red/green/refactor, BDD
Given/When/Then, beads, the state machine — and silent about **shape**. The architect's
plan template has a free-form `Solution Approach: architecture choices` bullet and
nothing downstream binds to it.

This design started as "should the plugin be opinionated about domain-driven design?"
and arrived somewhere narrower and better-evidenced. The path matters, because it
explains the Non-Goals:

1. **DDD as a plugin-wide default was rejected.** The loop is pointed at a mix of
   greenfield and existing codebases. Prescribing aggregates/repositories/layering
   into a marketplace plugin ships a value to strangers' repos, contradicts the
   repo's own detect-and-adapt lesson
   (`memory/feedback_detect_adapt_conventions.md`), and fights CLAUDE.md's
   "match surrounding style over external standards."
2. **A real DDD analysis of the Brooklet project supplied the actual finding.** Full
   DDD was cargo-cult there — Brooklet's domain *is* storage, so there is no domain to
   protect from infrastructure. But the analysis surfaced a reproducible bug and a
   clean filter:

   > Every DDD idea that pays off here is about **invariant placement** — where a rule
   > lives and what makes it impossible to bypass. Every idea that doesn't pay off is
   > about **layering**. Adopt the invariant discipline; only pay for the layering when
   > you actually have a domain to protect from infrastructure.

   Invariant placement survived in the case where DDD's central premise failed. That is
   what makes it a candidate for something universal. Layering did not survive, and is
   therefore out of scope here.

### The evidence

Brooklet's `Stream.produce()` validates topic names with an ad-hoc traversal check.
`storage/offsets.py` validates via `validate_safe_name()`, which also enforces a
character allowlist. The two rules disagree, and nothing forces them to agree. Result:
a topic can be produced, registered, listed, and read — and never consumed. The data is
stranded. The bug shipped through a merge and sat in `main`.

### Why this belongs in *this* plugin

Invariant drift is not a generic code-quality nicety — it is the loop's **native
failure mode**, manufactured by its own central mechanic:

- The architect's job is decomposing a feature into independent tasks; the plan template
  has a `Parallelization Waves` section.
- Independent tasks that each touch the same concept will each validate it locally and
  *correctly*. No individual Builder is wrong.
- The inconsistency is **emergent**. It is invisible to every iteration, because no
  single iteration ever sees two of the three checks.

And every quality gate the plugin owns is structurally blind to it, because every gate
is **local**:

| Gate | Why it misses invariant drift |
|---|---|
| Builder Stop hook | Checks tests passing, commit, hook errors, task closed |
| Tests / coverage | Each check is individually tested and individually passing |
| Ruff / type validators | Both checks are well-typed and lint-clean |
| Built-in `code-review` (REVIEW state) | Reads a **diff**; task 7's added check is correct in isolation |

Drift is never visible in a diff. It is only visible in the *relationship between two
diffs that were never reviewed together*. That is why a smarter reviewer cannot fix
this, and why the check must key off a whole-feature, cross-feature artifact.

## Goals

1. Prevent a rule for a named concept from acquiring a second, disagreeing home —
   across tasks within a feature, and across features over time.
2. Do it without naming, requiring, or implying any architecture.
3. Leave the map behind as durable, human-readable product documentation.

## Non-Goals

- **No DDD.** No aggregates, repositories, domain services, domain events, or
  `domain/application/infrastructure` restructuring. The ledger records *where a rule
  lives*; it never mandates a value object or any other pattern.
- **No layering opinion.** The half of the DDD analysis that didn't generalize stays out.
- **No new agent.** v2 deliberately replaced the agent-team pipeline with the state
  machine, and CLAUDE.md is explicit that VERIFY/REVIEW call built-in skills rather than
  custom equivalents. Agent definitions here earn their keep by carrying machinery
  (Builder has PostToolUse validators and a Stop-hook gate). This check needs grep and a
  list.
- **No full-repo invariant survey.** See "Ledger, not survey."
- **No mandatory architecture declaration.** The plan *accepts* a named approach if the
  human declared one in the task description; it never demands one, which would
  manufacture "Architecture: layered" on two-file bugfixes.

## Architecture: a durable ledger, read before written

The map lives at **`specs/invariants.md`** — tracked in git, beside the per-feature
`{slug}-spec.md` and `{slug}-plan.md` that reference it, and surviving uninstallation of
the plugin. A map describing the product's code should not live in the loop's state
directory.

`.sdlc/signs.md` is the precedent for durability (read at step 2 of every orient ritual,
survives across runs) but not the right home: signs are guardrails about **loop
behavior**; the ledger is about the **product's code**, and its audience includes humans
reviewing the PR and Claude sessions that never invoke `/sdlc`.

### The central inversion

**The architect's first PLAN move is to *read* the ledger, not write it.** The map is an
input before it is an output. Feature 2's architect opens the ledger, sees
`TopicName → storage/names.py`, and plans `GroupName` beside it rather than inventing a
second home for a rule that already has one. Appending new rows is what it does *after*
honoring existing ones.

Without this inversion the ledger is per-plan, and a per-plan map reproduces the exact
bug it exists to prevent: feature 2 has no idea what feature 1 declared.

### Ledger, not survey

On an existing codebase with no map, the architect does **not** inventory every invariant
in the repo. It records what this feature touches; the map accretes. An incomplete map
honest about being incomplete is useful on day one. A complete map is an unbounded
prerequisite that would sink the idea on feature one.

### Threshold: any named concept with a rule earns a row

Point-in-time thresholds ("used in 2+ places", "crosses a public boundary or gets
persisted") are wrong *because* the ledger is durable. A concept used in exactly one
place today cannot drift from itself today — but the row is precisely what stops feature
five from giving it a second home next month.

The cost of a row is one line in a table, not a wrapper class. That asymmetry is what
lets the threshold be loose without ceremony creeping back in.

### Ledger format

A table in `specs/invariants.md`. Rules are written as **rules, not adjectives** —
`billing/domain/ imports nothing from billing/adapters/` beats "clean architecture".

| Concept | Rule | Home (the one place it is enforced) | Added by |
|---|---|---|---|
| `TopicName` | Non-empty; no `..` path segments; chars in `[A-Za-z0-9._/-]`; no trailing `/` | `src/brooklet/storage/names.py` | `topic-registry` |

## Touch points

Four edits, zero new agents.

1. **Architect (`agents/architect.md`)** — read `specs/invariants.md` before planning;
   honor existing rows; append rows for concepts this feature introduces. The optional
   `Architectural Constraints` subsection of `Solution Approach` accepts a named
   approach when the human declared one in the task description, and is omitted
   entirely otherwise.

2. **Builder (`agents/builder.md`)** — the weak link today is one line:
   `- **Plan documents**: Check specs/*-plan.md for acceptance criteria and context.`
   Architectural constraints reach the Builder as *context*, i.e. optional. Split the
   two things the plan carries: acceptance criteria (what to build) vs. invariants
   (binding). Add one concrete action, not a virtue: **before writing a validation or
   check, consult the ledger; if the concept has a home, use it and never add a second
   check.** Also fix a precedence bug in `Decide, Log, Proceed` — it currently says pick
   what "best matches project conventions", which lets a Builder violate a stated rule
   because the surrounding legacy code violates it too. A ledger row beats ambient
   convention; a genuine conflict is a `decide` log entry.

3. **VERIFY (`skills/sdlc-loop/SKILL.md`)** — a fourth required check, structurally
   identical to existing check #2 (`walk the spec AC by AC`): walk the ledger row by row
   and confirm the rule is **defined** in its declared home and nowhere else. The
   prohibition is on a *second, independent definition* of the rule — not on redundant
   enforcement. Code that defers to the home (calling its parser) is fine; so is a
   belt-and-braces DB constraint. What fails is a second place that decides for itself
   what a valid `TopicName` is, because that is the thing that can silently disagree.
   This runs at the only time the check is meaningful — after all tasks have merged. Per-task
   checking is checking for drift before there is anything to drift from. If fresh eyes
   are wanted later, VERIFY can dispatch a throwaway subagent with just the ledger; no
   agent definition required.

4. **CLAUDE.md pointer** — a one-line pointer to `specs/invariants.md` in the project's
   CLAUDE.md, so non-loop sessions honor the ledger. A map only the loop respects will
   get drifted around by hand within a week. This is the most invasive touch point (the
   plugin proposes an edit to a file the user owns) and should be proposed, not silently
   written.

## Rot, and why the check must be bidirectional

A durable map introduces a failure mode the per-plan version did not have. The ledger
says `TopicName → storage/names.py`; someone moves it; VERIFY now checks code against a
lie and reports false confidence. **A stale ledger is worse than no ledger.**

The mitigation falls out of making VERIFY's check bidirectional: if a declared home does
not exist, or no longer enforces its rule, that is a VERIFY failure that forces the
ledger to be corrected. The map cannot silently rot, because the thing that reads it
also audits it. A durable artifact not continuously checked against reality always
degrades into documentation-shaped decoration.

## Success criteria

- [ ] Two features built by separate `/sdlc` invocations, both touching one concept,
      produce exactly one home for its rule.
- [ ] The Brooklet stranded-topic bug class is caught by VERIFY: a second, disagreeing
      check for a ledgered concept fails the run.
- [ ] A two-file bugfix with no named concepts produces no ledger rows and no
      `Architectural Constraints` section — no ceremony.
- [ ] A moved/renamed home fails VERIFY rather than silently rotting.
- [ ] The word "aggregate" appears nowhere in the plugin.
- [ ] `specs/invariants.md` is readable by a human with no context on the plugin.

## Open questions / risks

- **Architect over-application.** Told to map invariants, an architect may row-ify every
  string in the feature. The loose threshold is defensible only while rows stay one line;
  if rows grow prose, ceremony returns through the door DDD was shown out of.
- **VERIFY cost.** A whole-feature, cross-feature check runs every feature and grows with
  the ledger. Unbounded growth may need a scoping rule (only rows this feature touched?)
  — but that reintroduces the cross-feature blind spot. Deliberately unresolved; needs
  real runs.
- **Enforcement strength.** VERIFY failure bounces the loop into BUILD with an attempt
  budget. A false positive on an architectural judgment burns budget on a phantom. This
  is why the check is keyed to a *declared list* rather than open-ended judgment — but
  the risk is real and argues for starting advisory.
- **The Builder Stop hook stays untouched.** Adding a fifth criterion was considered and
  rejected: it is Haiku, 30s, judging from a transcript. Architectural conformance is a
  large step up from "did they run git commit", and a false `{"ok": false}` stalls the
  loop.
- **Untested premise.** Invariant drift has not been observed in La Boeuf's own `/sdlc`
  runs — the evidence is Brooklet's hand-written bug. The claim that the loop produces
  this failure mode is reasoned from its mechanics, not measured. Mitigating: the bug is
  near-invisible by construction (passes tests, coverage, lint, diff review), so absence
  of observation is weak evidence of absence.
