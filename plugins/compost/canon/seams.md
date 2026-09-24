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

## Seeing a test fail through the seam

A test is trusted only once you have seen it fail for the reason you expect. A test that has
never failed may be checking nothing: the wrong code path, a mock of the thing it meant to
exercise, an assertion that cannot be false. The seam is where the test gets in, so it is also
where you make it fail: change the behavior behind the seam, or run the test against the code
before the change, and watch the assertion go red with the message you expected. Whether the test
or the code comes first is a separate choice. When no seam exists, cut one with the smallest
mechanical edit before any behavior change, so the test can reach the code at all.

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
