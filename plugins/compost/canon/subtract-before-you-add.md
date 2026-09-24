# Subtract before you add

When changing a system, remove what is no longer needed first, then build on what remains. The
default move is subtraction.

Forked from the pstack principle of the same name.

## Why it works

Adding to a complicated system compounds its complexity. Removing first leaves less code to read,
reveals the structure that actually carries the behavior, and often makes the next design
obvious. A change that starts by deleting a dead path, a redundant check, or an unused option is
usually smaller in total than the same change made on top of them.

Treat simplification as continual. Leave each area slightly simpler, and no less capable, than
you found it, behind the same or a smaller interface.

## Why it matters for an agent

Agents add by reflex. Asked to change behavior, an agent writes the new path and leaves the old
one "in case", adds a flag to choose between them, and keeps the helper nothing calls any more.
Every one of those survives into the next session, where another agent reads it, assumes it
matters, and builds around it. Dead code is not neutral for an agent; it is misleading context.

## In practice

- Sequence removal before construction: delete dead code, stale references, and redundant
  validation in their own commit, then make the change on the smaller base.
- Replace, do not deprecate. When the change supersedes old code, the old code goes in the same
  change. No compatibility shims, no commented-out blocks, no flags that keep both paths alive.
  Where callers you do not control need a transition, use
  [expand, migrate, contract](expand-contract.md) with the contract step filed as an issue.
- Design for observed usage. No validators, options, or handlers beyond what the spec asks for.
- Cut before you polish. Reach the minimum that meets the bar, then decide whether polish is
  worth it.
- Apply it to prose too: instructions, prompts, and docs. A section that adds nothing gets
  deleted, not left as a stub.
