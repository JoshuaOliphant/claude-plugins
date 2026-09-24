# Good-enough software

Quality is a requirement, decided with the user, not a private standard the implementer keeps
raising. Software is good enough when it meets the quality bar the people using it agreed to, and
further polish is a trade against shipping and learning from real use.

The idea comes from Andy Hunt and Dave Thomas, *The Pragmatic Programmer*. Their point is not that
sloppiness is fine. It is that "perfect" has no stopping rule, and the users who pay for the
software are entitled to weigh in on how good it has to be before they get it. Often they would
rather have something useful today than something flawless next quarter, and what they learn from
using it changes what "flawless" would have meant.

## Good enough is not careless

The bar is set once, explicitly, and then met in full. Correctness, tests that prove behavior, and
readable code are part of the bar, not extras above it. What good enough rules out is work past the
agreed bar: speculative options, edge cases nobody has hit, abstractions for callers that do not
exist, a second pass of polish on code that already reads plainly.

## Why it matters for an agent

An agent does not get tired, so it has no natural brake on gold-plating. It will happily add
configuration flags, handle hypothetical inputs, and refactor adjacent code, and each addition
looks responsible in isolation. The cost lands on the reviewer, who has more to read, and on the
codebase, which has more to maintain. Without a stated bar the agent also cannot tell the user when
it is done, so "done" drifts.

The opposite failure is real too: stopping at "it compiles" or at tests that prove nothing, and
calling that good enough. The bar exists to rule out both.

## In practice

- Write the quality bar into the acceptance criteria before building. When a criterion is met and
  verified, that part is finished.
- Build for observed usage. A case the spec does not name and nobody has hit waits until it is
  hit; note it on the issue instead of coding it.
- When a gate and the bar disagree, bring the trade to the user rather than padding. The coverage
  gate is the common case: if reaching 100% means tests that assert nothing useful, show the lines
  and propose an exclusion or a lower threshold.
- Stop at the bar and ship. Feedback from real use is worth more than another hour of polish that
  nobody asked for.
