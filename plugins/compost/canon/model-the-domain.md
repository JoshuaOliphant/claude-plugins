# Model the domain

Put the domain's rules in a data structure that matches the domain, instead of spreading them
across conditionals. When the structure is right, invalid states cannot be built and whole
families of branches disappear.

Forked from the pstack principle of the same name. It is the code-level partner of
[ubiquitous language](ubiquitous-language.md): the glossary names the concepts, and the model gives
each one a single home.

## The signs you skipped it

- A second boolean that must stay in sync with the first (`is_active` and `is_archived`).
- A feature that adds one more branch to an existing if/else chain, in several files.
- The same assumption about a dict's keys or a tuple's order repeated at every use site.
- Modules named for phases (load, validate, transform, save), each re-applying the same domain
  rules. Execution order is not ownership.

## Why it matters for an agent

An agent extends whatever shape it finds. Given scattered flags, it adds another flag; given an
if/else chain, it adds another branch. Each change is locally reasonable, and the accidental
complexity compounds. Choosing the structure when the code is written is cheap. Recovering it
later reads as a refactor, and refactors get deferred.

## Structures to reach for

- A state machine instead of lifecycle booleans and phase checks.
- A typed model instead of loose parameters or dicts passed around by convention.
- A lookup table, registry, or tagged union instead of branching spread across files. When the
  table's rules change more often than the code, move them into a data file: a
  [domain language](domain-languages.md).
- A reducer or command/event model instead of ad hoc mutation.
- A module that owns one body of domain knowledge and its invariants.
- When none of these fits: write down what the code must never allow and how the data is read,
  then pick the structure that encodes exactly that.
- Tell a law from a policy. A semantic invariant is part of what the domain means ("a charge is
  never applied twice"), lives in `CONTEXT.md`, and is enforced by a type or an assertion. A
  policy is a rule the business may change ("refunds over $500 need approval"), and belongs in
  code that is cheap to change or a domain language's data file. Hard-coding a policy as a law
  makes it costly to change; a law kept as a config value lets someone switch it off.

## In practice

- Before adding a flag or a branch, ask whether the domain concept it represents has a home. If
  not, create the home first, then add the behavior there.
- Do not force it. If the current shape is clear, local, and unlikely to grow, boring code wins.
  An abstraction that adds indirection without deleting branches, duplicated rules, or invalid
  states is not a model; it is a layer.
- Heavier architecture (aggregates, repositories, event stores, ports and adapters everywhere) is
  not the default. It waits for a project whose complexity has been observed to need it.
