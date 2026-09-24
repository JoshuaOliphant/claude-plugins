# Tracer bullets

Build one thin path through every layer of the system first, with real code, and grow the system
by widening that path. The first slice of a feature should run end to end: input, the domain
logic, storage, and whatever the user sees, each in its simplest real form.

The idea comes from Andy Hunt and Dave Thomas, *The Pragmatic Programmer*. Gunners firing at night
load tracer rounds so they can see where the stream lands and correct the aim while firing, instead
of calculating everything up front and hoping. Software built layer by layer is the calculated
shot: nothing works until everything works, and the first honest feedback arrives at the end.

## Tracer code is not a prototype

A prototype answers one question and is thrown away. Tracer code is kept. It is the skeleton the
finished system hangs on, so it is written to production standard: tested, named in the domain's
language, and merged. What makes it thin is scope, not quality. It handles one case of one story,
not every case badly.

## Why it matters for an agent

An agent left alone tends to build horizontally: all the models, then all the services, then the
interface. Each layer looks complete and passes its own tests, and the integration problems wait
until the last step, where they are most expensive to fix and hardest to trace. A vertical slice
turns every integration question into something observable on day one, and gives the user a
running thing to react to while the direction is still cheap to change.

It also makes progress legible. "Story 1 works end to end" is a claim anyone can check by running
it. "The data layer is 80% done" is not.

## In practice

- Make the first slice of any feature cross every layer it will eventually touch, with the
  simplest behavior that is real. A hard-coded list behind a real endpoint and a real screen beats
  a complete schema with nothing calling it.
- Each slice ends demoable: one user story, or one acceptance criterion of it, that can be run and
  observed, not just unit-tested.
- When the slice misses (the interface feels wrong, a layer resists), adjust the aim now. Missing
  early is the point; it is cheaper than discovering the same thing after every layer is built.
- Widen by adding the next story as another slice through the same path. Do not go back and
  "finish" a layer ahead of the stories that need it.
