---
name: slice
description: Breaks an agreed spec into tracer-bullet issues in the repo's tracker, each with its acceptance criteria, files, interfaces, and blocking edges. Use when the user says "slice this", "break this into issues", "make tickets", "create the issues", "make a plan", "write the implementation plan", "plan the implementation", "save the rest as issues", "what order should we build this in", or a parent spec issue is ready to build.
---

# Slice

Slicing turns the parent issue's acceptance criteria into issues that can be built, verified, and
merged one at a time, several of them in parallel. The unit is the tracer bullet (Hunt and Thomas,
The Pragmatic Programmer): a thin path through every layer that works end to end on its own, so
each issue proves something real the day it lands ([tracer bullets](../../canon/tracer-bullets.md)).
Issues worked in parallel drift apart unless each one says exactly what it consumes from its
neighbors and what it produces for them, so every issue carries that contract.

The tracker is the only plan. No markdown plan files, no second task list.

## Steps

1. **Read the spec and the ground.** Fetch the parent issue with its comments, using the commands
   in `docs/agents/issue-tracker.md` (if it is missing, run `compost:setup` now, then continue).
   Read `CONTEXT.md`, the ADRs in the area, and the code the spec touches. Use the glossary's
   terms in every title and body. If there is no spec, or it still has open questions, go back to
   `compost:spec` first.

2. **Lock the file structure.** Before cutting issues, list the files to create or change and the
   one responsibility each will hold. Split by what changes together, not by technical layer.
   Follow the patterns the codebase already has; when a file you must change has grown unwieldy,
   a split belongs in the plan. Look for a prefactor that makes the rest simple ("make the change
   easy, then make the easy change", Kent Beck) and put it first. This is where decomposition
   gets decided, and issues inherit it.

3. **Cut tracer bullets.** Each issue cuts a narrow but complete path through every layer it
   needs (schema, logic, interface, tests) and is demoable or verifiable alone. Give every AC-N
   from the spec to exactly one issue; a criterion split across two issues is verified by neither.
   Order issues so each lands green on its own
   ([sequence verifiable units](../../canon/sequence-verifiable-units.md)).

   A wide refactor is the exception: one mechanical change whose blast radius spans the codebase
   (renaming a column, retyping a shared symbol) can't land as a vertical slice. Sequence it as
   expand-contract ([expand-contract](../../canon/expand-contract.md)): one issue adds the new form
   beside the old; migrate issues move callers over in batches sized by blast radius, each blocked
   by the expand; a contract issue, blocked by every batch, deletes the old form. If even the
   batches can't stay green alone, give them a shared integration branch and a final
   integrate-and-verify issue that all of them block.

   If you can't cut slices because the way there is still foggy (decisions the spec couldn't
   settle, work that will outlast several sessions), chart a map instead: step 7.

4. **Write each issue** with the template in [issue template](references/issue-template.md):
   - **Acceptance criteria:** the issue's AC-N copied verbatim from the spec, as a checklist.
   - **Files:** create, modify, and test paths, with line ranges when a change is local. Paths
     belong here and not in the spec: an issue lives for days, a spec for the life of the feature.
   - **Interfaces:** what it consumes from earlier issues and what it produces for later ones,
     with exact names, parameters, and return types. Someone working one issue sees only that
     issue; this block is how they learn what the neighbors call things.
   - **Blocked by:** only the issues that genuinely gate this one. Two issues that touch the same
     file are ordered by a blocking edge, so they never run in parallel.

   No placeholders: "add error handling", "similar to #12", "tests for the above", or a name that
   no issue produces are all failures. Write out what the reader needs.

5. **Self-review the set once** against the spec, and fix what you find inline:
   - Coverage: point to the issue for every AC-N and every user story. Add an issue for any gap.
   - Placeholders: none of the patterns above.
   - Interfaces: every name an issue consumes is produced, with the same spelling and types, by an
     issue it is blocked by.
   - Edges: no cycles; issues that share a file are ordered; nothing is blocked without cause.

6. **Publish in dependency order,** blockers first, so each "Blocked by" names a real number.
   Use the tracker's native sub-issue and dependency links where it has them, and always write the
   `Blocked by #n` line in the body as well. Label each issue per `docs/agents/issue-tracker.md`
   (`ready-for-agent` by default, `ready-for-human` for work only a person can do). Add a checklist
   of the slices to the parent issue; it is the progress record. Leave the parent open.

7. **For long, foggy work, keep a map issue** instead of guessing at slices. The map names the
   destination, indexes the decisions made so far, and lists the fog, the questions you can see
   coming but can't yet phrase sharply. Each sharp question becomes a decision sub-issue, resolved
   one at a time; unclear parts stay unticketed until the fog lifts. Format and procedure are in
   [map issue](references/map-issue.md). When the way is clear, come back to step 2 and slice.

Report the breakdown when done: each issue's number, title, what it delivers, and its blockers,
plus which issues can start in parallel.

## Next moves

- `compost:implement` when the issues are filed and at least one is unblocked.
- `compost:spec` when slicing exposes a decision the spec left open; resume here after.
- `compost:deepen` when locking the file structure raises a real question about a module's shape
  or interface.
- `compost:pause` when a map will outlive this session.
