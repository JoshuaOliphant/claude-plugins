# Deep modules

A deep module puts a lot of behavior behind a small interface. A shallow one has an interface
nearly as complicated as what it does, so callers learn almost as much as they would by reading
the implementation. Depth is what makes a module worth having.

The idea comes from John Ousterhout, *A Philosophy of Software Design*, which builds on David
Parnas's 1972 paper "On the Criteria To Be Used in Decomposing Systems into Modules". Three ideas
travel together.

- **Depth.** The interface is everything a caller must know to use the module correctly: the
  signature, but also invariants, ordering rules, error modes, and required configuration. The
  smaller that is relative to the behavior behind it, the more leverage the module gives callers
  and the more locality it gives maintainers: a change or a bug lives in one place.
- **Information hiding.** Parnas's criterion: each module hides a design decision that is likely
  to change, so the change stays inside it. His counterexample splits a program by processing
  steps (read, transform, write), which spreads every format decision across all the steps.
  Splitting by what changes together beats splitting by what runs in sequence.
- **Design it twice.** The first interface that comes to mind is rarely the best. Sketch at least
  two substantially different ones and compare them before building.

## Why it matters for an agent

Agents produce shallow modules by default: a wrapper per concept, a pass-through service per
layer, a helper per repeated line. Each is small and each looks tidy, and together they force
every reader to hold the whole chain in their head. Deep modules also make an agent's own work
easier. A module it can use from its interface alone is one it does not have to reread every
session, and a test through that interface survives the next refactor.

## In practice

- Apply the deletion test to any module you are about to add or keep. If deleting it would make
  complexity vanish, it is a pass-through; inline it. If the complexity would reappear at every
  call site, it earns its place.
- Organize modules around a body of knowledge that changes together, not around steps in a
  pipeline. A module named for a phase (`loader`, `validator`, `saver`) is a warning sign.
- Before building a module with more than a trivial interface, write two or three rival interface
  sketches, optimized for different things (fewest entry points, the most common caller, most
  flexibility), and pick or combine deliberately. Parallel subagents do this well.
- Test through the interface. If a test needs to reach past it, the module is the wrong shape,
  not the test.
