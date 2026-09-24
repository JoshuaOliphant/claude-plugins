# Expand, migrate, contract

Change an interface that other code depends on in three steps instead of one. Expand: add the
target form alongside the current one. Migrate: move every caller to the target form. Contract:
delete the old form. At every point between steps the system builds and its tests pass.

The pattern is called parallel change; Danilo Sato described it on Martin Fowler's site, and it is
also known as expand-contract. It applies to function signatures, module interfaces, database
schemas (add the column, backfill and dual-write, switch reads, drop the old column), message
formats, and public APIs.

## Why it matters for an agent

A breaking change made in one edit breaks every caller at once, and the agent then fixes dozens of
sites against a red build with no working state to compare to. Splitting the change keeps each
step verifiable on its own, which is the point of
[sequencing verifiable units](sequence-verifiable-units.md). The contract step matters as much as
the expand step: an agent that expands and migrates but never contracts leaves two ways to do
everything, which is the accumulation this pattern exists to avoid.

## When the old form may outlive the change

Compost's rule is replace, don't deprecate: no compatibility shims, and the old code goes in the
same change. Expand-contract fits inside that rule. Which case applies depends on who controls the
callers.

- **You control every caller** (one repo, one deploy). Expand, migrate, and contract all happen in
  the same branch, usually as separate commits, and the old form is gone before merge. The
  sequence exists to keep each commit green, not to ship a transition period.
- **You do not control every caller, or the change crosses a deploy** (a database with a running
  service, a published API, clients on older versions). The contract step is a later release. It
  gets its own issue, filed when the expand lands, naming what must be true before the old form
  can be removed.

## In practice

- Expand without changing behavior: the target form delegates to, or is delegated to by, the old
  one, and existing tests stay green.
- Migrate callers in batches small enough that each can be verified; run the checks after each.
- Contract completely: delete the old form, its tests, and any code that only existed to bridge
  the two. Search for remaining references before calling it done.
- Never leave an expand without a contract. Either it happens in the same branch, or an issue
  exists for it before the expand merges.
