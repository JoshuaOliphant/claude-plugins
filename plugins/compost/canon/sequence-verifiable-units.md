# Sequence verifiable units

Order work as a series of small units, each ending in a state that can be checked, and do not
start the next unit until the current one is green. Then deliver the units in an order that
proves the work to whoever reviews it.

Forked from the pstack principle of the same name. It is the sequencing partner of
[prove it works](prove-it-works.md), which keeps each check real.

## Why it matters for an agent

A break caught at the unit that caused it is cheap to find: one change separates good from bad.
A break caught after a batch is buried among everything else that changed, and more work has been
stacked on the broken base. Agents are prone to batching because each edit feels obviously right,
and a run of twenty similar edits feels like one edit. It is twenty chances to be wrong.

The same ordering pays off at review. A sequence of commits that each land green and read in a
sensible order turns "trust me" into something the reviewer can replay.

## Execution

Each unit is a bracket: start from a known-good state, make one change, run the check, then move
on. Before a sweep, rebase onto a clean default branch so every check measures against the real
baseline, not against your own uncommitted drift. When a script or codemod makes the edits, the
per-unit check is nearly free; run it anyway.

## Delivery

Stack commits and pull requests so the sequence argues for the change:

- the failing test, then the fix that turns it green;
- the removal, then the reshape on the simpler base;
- the baseline measurement, then the change that moves it;
- the scaffold or seam, then the feature that uses it.

Each commit builds and passes on its own.

## In practice

- In any migration or run of similar edits, verify after each unit, not at the end.
- Commit when a unit is green. A commit is a checkpoint you can return to, not a summary you write
  later.
- If a check fails, stop and fix it before the next unit. Do not queue failures to handle later.
- Split commits by concern so each one tells one step of the story.
