---
name: deepen
description: Designs deep modules, meaning small interfaces with a lot of behaviour behind them, seams where something really varies, and tests at the interface. Use when the user says "design this interface", "where should the seam go", "refactor this for testability", "this module is hard to test", "find deepening opportunities", "improve the architecture", "should this be a port and adapter", or when a bug has no seam for a regression test, or implementation hits a design question.
---

# Deepen

A deep module puts a lot of behaviour behind a small interface (Ousterhout, *A Philosophy of Software
Design*; Parnas on information hiding). Callers get leverage, because they learn little and get a
lot. Maintainers get locality, because change and bugs concentrate in one place. Tests cross the same
interface callers do, so they survive refactors. This skill finds where the code is shallow, decides
where seams go, and keeps heavy architecture out unless a dependency earns it. The why is in
[deep modules](../../canon/deep-modules.md), [seams](../../canon/seams.md), and
[type-system discipline](../../canon/type-system-discipline.md).

## Steps

1. **Use the vocabulary.** Module, interface, implementation, depth, seam, adapter, leverage,
   locality: use these words exactly, and don't drift into "component", "service", "API", or
   "boundary". Definitions, the deletion test, and the rejected framings are in
   [references/vocabulary.md](references/vocabulary.md). For the domain, use the names in
   `CONTEXT.md` ([ubiquitous language](../../canon/ubiquitous-language.md)): "the Order intake
   module", not "the OrderHandler" or "the order service". Read the ADRs in `docs/adr/` for the area;
   they record decisions not to re-litigate.

2. **Scope before you scan.** Deepening pays off by making future changes easier, so look where
   change happens. If the user, the issue, or `compost:diagnose` named a module, start there. If not,
   find the hot spots in the history:

   ```bash
   git log --since="6 months ago" --name-only --format= | sort | uniq -c | sort -rn | head -30
   ```

   Let the files and directories that keep coming up pull your attention first. If changes are
   scattered with no hot spot, widen the window. This is not a full audit.

3. **Walk the code for friction.** Send a subagent (several, one per hot spot, when there are
   several) to explore and report where it hurts:
   - Understanding one concept means bouncing between many small modules.
   - An interface is nearly as complex as its implementation.
   - Pure functions were extracted for testability, but the bugs hide in how they are called.
   - Modules leak a shared decision (a representation, a policy, a wire format) across their seams.
   - Code is untested, or hard to test through its current interface.

   Apply the deletion test to anything that looks shallow: imagine deleting the module. If complexity
   vanishes, it was a pass-through. If it reappears across its callers, it was earning its keep.

4. **Classify each dependency; this decides whether a port exists.** Put every dependency of the
   candidate into one of four categories, detailed in
   [references/dependency-categories.md](references/dependency-categories.md):
   - **In-process** (pure computation, in-memory state): merge and test through the interface. No
     port.
   - **Local-substitutable** (Postgres with PGLite, a filesystem with a temp dir): test with the
     stand-in running. The seam stays internal. No port.
   - **Remote but owned** (your own service across the network): a port at the seam, a production
     adapter, an in-memory adapter for tests.
   - **Truly external** (Stripe, Twilio): the module takes it as an injected port; tests supply a
     fake adapter.

   Only the last two get a port and adapter. That rule is what keeps ports-and-adapters,
   repositories, and similar scaffolding off by default. One adapter means a hypothetical seam; two
   adapters (typically production and test) make it real. Don't add a seam nothing varies across.

5. **Present the candidates.** For each: the files, the problem (what hurts), the change (what
   becomes one module, what goes behind the seam), the gain in locality, leverage, and tests, the
   dependency categories, and a strength of *Strong*, *Worth exploring*, or *Speculative*. End with
   the one you would tackle first and why. If a candidate contradicts an ADR, include it only when the
   friction is real enough to reopen the ADR, and say which ADR and why. Don't propose interfaces yet.

   Give this in the conversation. Write an HTML report only when the user asks for one; the format is
   in [references/html-report.md](references/html-report.md). When the user is driving, let them pick
   the candidate. Inside `compost:implement`, pick the top one, post the ruling (what, why, cost if
   wrong) as an issue comment, and continue.

6. **Shape the interface.** Write the caller's usage first (two or three real call sites) and derive
   the types from it. Build types from valid values rather than carving them out of looser ones with
   checks: a non-empty list is a head and a rest, a time range is a start and a duration. Parse
   external data into those types at the seam and trust them inside
   ([boundary discipline](../../canon/boundary-discipline.md)). Screen the shape against
   [references/design-red-flags.md](references/design-red-flags.md): shallow module, information
   leakage, temporal decomposition, pass-through methods.

   When the interface is costly to get wrong (many callers, hard to change later, a public contract),
   design it twice. Spawn three subagents in parallel, each designing a radically different interface
   under one constraint: minimal (one to three entry points), flexible (many use cases), and
   common-case (the default call is trivial). Add a fourth built around ports only when step 4 found a
   remote-but-owned or external dependency. The brief and comparison are in
   [references/design-it-twice.md](references/design-it-twice.md). Compare on depth, locality, and
   seam placement, then recommend one, or a hybrid, with a clear opinion.

7. **Keep the domain docs current as decisions land.** Name a deepened module after a concept missing
   from `CONTEXT.md`: add the term, creating the file if needed. Sharpen a fuzzy term: update it there.
   When the user rejects a candidate for a reason a future reviewer would need in order not to suggest
   it again, offer an ADR; skip reasons that are temporary ("not now") or obvious. Offer ADRs only for
   decisions that meet the test in [domain docs](../spec/references/domain-docs.md). Ask Jev first:
   run `adr-worthy` on the decision (what, why, alternatives, cost if wrong) and offer only on
   `offer_adr` ([jev](../spec/references/jev.md)). Exit 3 means Jev is unavailable: apply the test yourself.

8. **Refactor by replacing, not layering.** Move every caller to the deepened interface in the same
   change and delete the old modules; no compatibility shims or deprecated paths. Write tests at the
   deepened interface, asserting on observable outcomes, and delete the old tests on the shallow
   modules they replace. A test that has to change when the implementation changes is testing past
   the interface. When callers live outside this repository or deploy separately, use expand-contract
   ([expand-contract](../../canon/expand-contract.md)) and file the contract step as an issue. If the
   refactor is bigger than one change, slice it.

   While filling in the design, watch for the shape being wrong: the same workaround in unrelated
   places, special-case branches for unrelated edge cases, types that need casts or always-set
   optional fields, callers that must know the module's internal rules. One such sign is noise; a
   pattern means go back to step 6 and redesign smaller, not bolt on fixes.

## Next moves

- `compost:slice` when the deepening spans more than one change and needs issues in the tracker.
- `compost:implement` when the design question came from an issue in flight: return to it.
- `compost:build` when the refactor is one change and ready to write.
- `compost:diagnose` when the deepening was to create a seam for a regression test: go write it.
- `compost:spec` when the new shape changes behaviour users see and needs the spec updated.
