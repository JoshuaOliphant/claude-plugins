# Dependency categories

Classify every dependency of a deepening candidate before proposing a shape. The category decides how
the deepened module is tested across its seam, and whether it gets a port at all. This is the gate
that keeps ports and adapters, repositories, and similar scaffolding out of code that hasn't earned
them: only categories 3 and 4 get a port.

## 1. In-process

Pure computation, in-memory state, no I/O. Always deepenable: merge the modules and test through the
new interface directly. No adapter, no port.

## 2. Local-substitutable

Dependencies with a local stand-in that behaves like the real thing: PGLite or a throwaway Postgres
for Postgres, a temp directory for the filesystem, SQLite in memory where the SQL dialect allows.
Deepenable if the stand-in exists. Tests run with the stand-in in the suite. The seam is internal to
the module; there is no port on its external interface.

## 3. Remote but owned

Your own services across a network: other services you run, internal APIs, queues you control.
Define a port at the seam. The deep module owns the logic; the transport is injected as an adapter.
Tests use an in-memory adapter; production uses the HTTP, gRPC, or queue adapter.

Recommendation shape: "Define a port at the seam, with an HTTP adapter for production and an
in-memory adapter for tests, so the logic sits in one deep module even though it is deployed across a
network."

## 4. Truly external

Third-party services you don't control: payment processors, messaging providers, hosted model APIs.
The deepened module takes the dependency as an injected port; tests supply a fake adapter that
records calls and returns canned responses. Parse the vendor's responses into your own types inside
the production adapter, so vendor types never cross the seam.

## Seam discipline

- A port needs at least two adapters that are justified today, typically production and test. A
  single-adapter seam is indirection with no payoff.
- Internal seams (used by the module's own tests) stay internal. Don't widen the interface to expose
  them.

## Testing: replace, don't layer

- Once tests at the deepened module's interface exist, the old unit tests on the shallow modules are
  waste. Delete them in the same change.
- Write the tests at the deepened interface, fitted into the existing suite and its fixtures.
- Assert on observable outcomes through the interface, not on internal state.
- A test that must change when the implementation changes is testing past the interface; move it to
  the interface or delete it.
