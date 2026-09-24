# Design it twice

Your first interface is rarely the best one (Ousterhout, *A Philosophy of Software Design*). When an
interface is costly to get wrong, get several radically different designs from parallel subagents and
compare them before committing.

## 1. Frame the problem

Write a short explanation of the problem space for the chosen candidate and show it in the
conversation:

- The constraints any interface must satisfy.
- The dependencies it relies on, and their categories ([dependency-categories.md](dependency-categories.md)).
- A rough code sketch that makes the constraints concrete. It illustrates, it doesn't propose.

Then spawn the designers straight away; the user reads while they work.

## 2. Spawn the designers

Spawn three subagents in one message so they run in parallel, or teammates when agent teams are
enabled. Each gets the same technical brief with a different constraint:

| Designer | Constraint |
|---|---|
| Minimal | Minimise the interface: one to three entry points. Maximise leverage per entry point. |
| Flexible | Maximise flexibility: support many use cases and extension. |
| Common case | Optimise for the most common caller: make the default call trivial. |
| Ports (only for category 3 or 4 dependencies) | Design around a port and adapters for the cross-seam dependency. |

### The brief

Give every designer the following, filled in:

```
You are designing one interface for a deepened module. Other designers are working on
the same problem under different constraints; produce the best design your constraint
allows and don't hedge toward a safe middle. Differences between designs are the point.

Your constraint: <minimal | flexible | common case | ports>

Problem: <the friction, in one paragraph>
Files and modules involved: <paths>
Coupling today: <what calls what, what leaks across which seam>
Dependencies and categories: <each dependency, in-process | local-substitutable |
  remote but owned | truly external>
What should sit behind the seam: <the behaviour to hide>

Vocabulary: use module, interface, implementation, depth, seam, adapter, leverage,
locality exactly. Domain terms from CONTEXT.md: <the relevant entries>.

Discipline:
- Write the caller's usage first (two or three real call sites), then derive the types.
- Build types from valid values; make illegal states unrepresentable.
- Parse external data into domain types behind the interface; no wire or vendor types
  on it.
- Validate at the seam and trust types inside; keep logic in pure functions.
- One source of truth per invariant; derive rather than sync.
- If two actors can write the same state, say what happens.
- Only remote-but-owned or truly external dependencies get a port.

Return:
1. The interface: types, entry points, parameters, invariants, ordering, error modes.
2. A usage example from a real caller.
3. What the implementation hides behind the seam.
4. Dependency strategy and adapters, per category.
5. Trade-offs: where leverage is high, where it is thin.
6. How it scores on the red flags in design-red-flags.md.
```

Attach [vocabulary.md](vocabulary.md), [dependency-categories.md](dependency-categories.md), and
[design-red-flags.md](design-red-flags.md) by path so each designer reads them.

## 3. Compare and recommend

Present the designs one at a time so each can be absorbed, then compare them in prose on:

- **Depth**: leverage at the interface.
- **Locality**: where change will concentrate.
- **Seam placement**: where the interface sits and what varies across it.

Screen each against the red flags. Then give your recommendation: which design is strongest and why.
If parts of two designs combine well, propose the hybrid. Be opinionated; a menu with no pick hands
the work back.
