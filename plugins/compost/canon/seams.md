# Seams

A seam is a place where you can change what a program does without editing the code at that
place. Every seam has an enabling point, the place where you choose which behavior runs: a
constructor argument, a function parameter, an import, a configuration value.

The idea comes from Michael Feathers, *Working Effectively with Legacy Code*. His definition of
legacy code is code without tests, and his problem is how to get tests around code that was never
designed for them. The answer is seams. Find a place where a dependency can be swapped (an object
passed in instead of constructed inside, a function looked up instead of hard-wired), or create
one with the smallest possible edit, then put the code under test through it and change it safely.

Matt Pocock uses the word the same way in his codebase-design vocabulary, and adds a design rule:
the seam is where a module's interface lives, and choosing where it goes is a design decision of
its own. One adapter behind a seam makes it hypothetical; it is real once two things plug into
it, typically the production adapter and a test adapter. "Seam" is preferred over "boundary",
which already means a bounded context.

## Seams and red, green, refactor

Kent Beck's test-driven cycle (*Test-Driven Development: By Example*) needs a seam to work. Red:
write a test through the seam and watch it fail for the reason you expect. Green: make it pass
with the simplest change. Refactor: clean up behind the seam while the test holds the behavior
still. When no seam exists, the first move is to make one, with the smallest mechanical edit,
before any behavior change.

## Why it matters for an agent

An agent that cannot get a test around the code will either skip the test or test something
adjacent, like a mock of the thing it meant to exercise. Knowing where the seams are tells it
where a test can reach, and knowing how to cut one tells it how to make untestable code testable
without a risky rewrite.

## In practice

- Before changing untested code, find the seam where a test can reach the behavior. If there is
  none, create one with a minimal edit (pass a dependency in, extract a function) and commit that
  separately from the behavior change.
- Put seams where something actually varies. Do not add an interface with one implementation and
  no test double "for flexibility".
- Test through the seam at the module's interface, not through internal seams exposed only for
  tests.
- Mock only at seams over things you do not control, such as third-party services. Behind your
  own seams, prefer the real implementation or a local stand-in.
