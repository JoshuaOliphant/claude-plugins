---
name: spec
description: Turns a fuzzy idea, request, or rough doc into an agreed spec of user stories with Given/When/Then acceptance criteria, posted as the parent issue. Use when the user says "spec this out", "let's design this", "brainstorm", "grill me", "what should happen when", "acceptance criteria", "edge cases", "define the requirements", "BDD", or asks for a feature whose behavior is not pinned down yet.
---

# Spec

A spec turns what someone asked for into what "done" means, before any code exists. It is the
record every later stage argues from: slice cuts issues from its acceptance criteria, build
fits a test to each one, verify maps each one to a passing test. A spec that leaves a decision
open pushes it into the code, where it gets made by accident. So the job is to find every open
decision, get it settled, and write the result down in behavior terms that won't go stale.

Facts are yours to find; decisions are the user's to make. Never ask what the code, the docs, or
a quick lookup can answer.

## Steps

1. **Read before asking.** Read `docs/agents/issue-tracker.md` (if it is missing, run
   `compost:setup` now, then continue), `CONTEXT.md` or `CONTEXT-MAP.md`, the ADRs in `docs/adr/` that touch
   the area, the relevant code, and recent commits. Use the glossary's terms from here on
   ([ubiquitous language](../../canon/ubiquitous-language.md)). Send subagents after facts you
   still need and keep going while they run; only the questions that depend on a fact wait for it.
   If the request already lives in an issue, thread, or doc that settles the decisions, synthesize
   the spec from it without an interview: classify it (step 2), then skip to step 6.

2. **Classify in one line, out loud,** so the user can override it. Ask Jev first: run `spec-class`
   with the request and what the survey found ([jev](references/jev.md)), state its `class` and its
   probability, and act on it. Exit 3 means Jev is unavailable: classify by the definitions below.
   - **Spike**: a feasibility question ("can we...", "is it possible..."). Its output is an
     answer, not code you keep.
   - **Bounded**: a well-scoped change to a flow that already exists in this repo (a flag, a small
     endpoint, a one-module fix). If there is no existing flow to read, it is not bounded.
   - **Architectural**: a project, a subsystem, or a change to how components fit together or to
     interfaces others depend on.

   When torn between two classes, take the heavier one. The ratchet turns one way: complexity
   found mid-spec upgrades the class, and nothing downgrades. If the request holds several
   independent subsystems, say so now and spec the first one; the rest become their own specs.

3. **Spike: state the question and the probe, then run it.** Two or three sentences on what you
   will try, then find out as cheaply as correctness allows, usually with a throwaway prototype
   ([prototype](references/prototype.md)). Report the answer as a recommendation. Anything you
   built stays labelled throwaway; building on it for real is a fresh request, so classify it.

4. **Ask in rounds until no open decisions remain.** Map the open decisions as a tree: each
   decision branches into the ones that hang off it. A round asks the frontier, the 3 to 5
   decisions whose prerequisites are all settled, as lettered multiple-choice questions, each with
   your recommended answer, in the format in [questions](references/questions.md). A question that
   depends on one still open waits for a later round. Ask fewer when the frontier is smaller;
   never pad a round. Draft the candidates, then ask Jev which make the round: `question-value`
   ranks them by how much the answer changes what gets built and returns the `round` to ask and the
   ones to `assume` ([jev](references/jev.md)). Exit 3: cut by the rules in
   [questions](references/questions.md).

   Gaps too small to be worth a question become assumptions: pick the conservative reading, list
   it, and keep going. The user corrects assumptions by reading the spec.

   After every round, show the refined prompt: the original request word for word plus one bullet
   per settled answer, following [refine-prompt](references/refine-prompt.md). It becomes the
   Clarifications section of the parent issue, so the record of what was asked for never drifts.

   The interview ends when the frontier is empty: every branch visited, nothing silently
   assumed. That is the stopping rule, not the user saying "enough" and not a series of approval
   gates. If nobody is there to answer (an unattended run), take your recommended answers, mark
   each bullet in the refined prompt as an assumption, and continue. If the user says "enough",
   do the same for the frontier still open: each recommendation becomes a bullet marked
   (assumed).

5. **Sharpen the domain as it settles.** While the rounds run, do the domain modeling inline, as
   described in [domain docs](references/domain-docs.md):
   - Call out a term that conflicts with `CONTEXT.md` the moment it appears, and propose one
     canonical word for a fuzzy or overloaded one.
   - Stress-test relationships with invented scenarios that probe the boundaries between
     concepts; when the user's account of the system disagrees with the code, surface it.
   - Write each resolved term into `CONTEXT.md` right away, creating the file with the first term.
     It is a glossary and nothing else.
   - Write an ADR in `docs/adr/` only when a decision is hard to reverse, surprising without
     context, and the result of a real trade-off. Missing any one of the three, skip it. Ask Jev
     first with `adr-worthy` and offer the ADR only on `offer_adr` ([jev](references/jev.md));
     exit 3, apply the three tests yourself.

   When prose cannot settle a decision (a state model that looks fine on paper, a layout nobody
   can picture), build a throwaway prototype, keep it on a `prototype/<slug>` branch as evidence,
   and link the branch from the spec ([prototype](references/prototype.md)).

6. **Architectural only: propose two or three approaches.** Give each its trade-offs, lead with
   the one you recommend and why, and cut every feature nobody asked for from all of them
   ([subtract before you add](../../canon/subtract-before-you-add.md)). Break the recommended
   design into units that each have one purpose and a well-defined interface, so each can be
   understood and tested without reading its internals. In existing code, follow the patterns
   already there, and include targeted improvements only where they serve this change.

7. **Write the spec** with the template in [parent issue](references/parent-issue.md): the
   concise sections for bounded work, the full ones for architectural work.
   - User stories: "As an <actor>, I want <feature>, so that <benefit>". The story says why.
   - Under each story, its acceptance criteria AC-N in Given/When/Then: the happy path first,
     then the cases the [edge-case checklist](references/edge-case-checklist.md) turns up, with
     three or more cases of the same shape merged into one scenario outline. The scenarios say
     what done means. Format and anti-patterns are in
     [acceptance criteria](references/acceptance-criteria.md).
   - Describe behavior and decisions, never file paths or code: both go stale within days. The
     exception is a prototype snippet that pins a decision more precisely than prose can (a state
     machine, a schema, a type shape), trimmed to the decision and marked as from the prototype.
   - Name the seams the tests will use: prefer existing ones, the highest one that works, and as
     few as possible ([seams](../../canon/seams.md)).

8. **Add Gherkin feature files when the project wants a BDD suite:** `docs/agents/testing.md`
   names a BDD runner, or one is already in the project's dependencies. Each AC-N becomes a
   scenario tagged `@ac-N`, so the spec is also a suite. The mapping and runner layout are in
   [gherkin](references/gherkin.md). Step definitions are test code and belong to `compost:build`.

9. **Self-review, then ask what is left.** Read the spec fresh and fix inline:
   - placeholders: "TBD", "TODO", "handle errors appropriately", sections left thin
   - contradictions between sections, or between a story and its criteria
   - scope: one spec's worth, or several independent pieces
   - ambiguity: any requirement two readers could build differently; pick one reading and state it
   - verifiability: every Then observable by a test

   For the criteria, ask Jev first: `ac-quality` grades each AC-N on an observable Then, a
   specific Given, and one behavior, and flags the ones to `rewrite` with their `weakest`
   dimension ([jev](references/jev.md)). Rewrite those. Exit 3: check every criterion against
   [acceptance criteria](references/acceptance-criteria.md) yourself.

   Then list any open questions, each quoting the spec line it concerns, in the format in
   [questions](references/questions.md). Answers go back into the spec and the refined prompt. No
   open questions is a fine result; say so.

10. **Post the parent issue** with the tracker from `docs/agents/issue-tracker.md` (by default
    `gh issue create` with the `spec` label; a local tracker writes `.scratch/<slug>/spec.md`).
    Commit `CONTEXT.md` and ADR changes, with any Gherkin feature files from step 8, as their own
    `docs:` commit. Bounded work proceeds from here. Architectural work stops: link the issue, ask
    for approval, and record the approval as an issue comment. An explicit instruction in the
    request to build it counts as that approval, unless the approach you chose changes what the
    user asked for. Requested changes go into the issue, then repeat step 9.

## Next moves

- `compost:slice` when the parent issue is posted (and approved, for architectural work) and the
  work spans more than one tracer bullet.
- `compost:build` when bounded work fits in one issue: the parent issue carries its own criteria.
- `compost:deepen` when the open decision is really about a module's shape or interface.
- `compost:fan-out` when two approaches are close enough that building both is cheaper than
  arguing.
- `compost:diagnose` when the "feature" turns out to be a defect in existing behavior.
