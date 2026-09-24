# Design red flags

Screen every candidate interface against these before choosing one. A red flag is a reason to revise
the shape or reject it.

## Shallow module

The interface is large and hides little. Judge depth by the capability and policy behind the
interface relative to its size.

- Callers coordinate several methods to complete one operation.
- Options on the interface expose internal stages or implementation choices.
- Learning the interface doesn't save the caller from learning the implementation.

## Information leakage

Several modules depend on the same internal decision: a representation, a policy, a protocol detail.
Changing it means coordinated edits in several places.

- Transport, storage, framework, or wire types re-exported through the interface. Parse external data
  into domain types behind the interface instead.
- The same format string, key layout, or status code set written out in more than one module.

## Temporal decomposition

Modules organised by the order things happen (load, validate, transform, save) instead of by the
knowledge they own. Each stage then repeats the same representation and its invariants. Group code
around the decision it protects; methods that run at different times can belong to one module.

## Pass-through method

A method that forwards its arguments to another method of the same shape. It adds a layer and hides
nothing. Remove it, or move the responsibility to the module that can complete the operation. Keep a
forwarding seam only when it adds policy, adaptation, or a distinct abstraction.

## Loose types

- A bag of optional fields where contradictory combinations compile: `{done: bool, done_at?: date}`
  admits `done=True` with no date. Model the variants: open, or done at a date.
- Two parameters of the same primitive type that mean different things (a user id and an order id
  as plain strings). Give each its own type.
- An invariant enforced by a check the type could have made impossible. Build the type from valid
  values: a non-empty list as a first element plus the rest, a range as a start plus a length.
- Strengthen a type only where partiality shows up (an assertion, a null check, a "can't happen"
  branch). Precision for its own sake is not the goal; total functions are.

## Signs the shape was wrong, seen during implementation

One of these is noise; a pattern means redesign rather than patch.

- The same shape of workaround appears in unrelated code.
- Unrelated edge cases each need their own special-case branch.
- Types need escape hatches to compile: casts, `Any`, optional fields that are always set in practice.
- A lock appears in a design that said the state wasn't shared.
- Callers have to know the module's internal rules to use it.

When you redesign, treat the new constraints as if they had been there from the start, and make the
design smaller before it grows ([subtract before you add](../../../canon/subtract-before-you-add.md)).
Complexity in the data is not complexity in the design; some problems are genuinely intricate.
