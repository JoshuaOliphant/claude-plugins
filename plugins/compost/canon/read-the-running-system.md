# Read the running system

When the code runs, ask it what it did. Traces, logs, and metrics are a record of real behavior,
already captured; reading them is cheaper and more honest than reasoning from the source about
what probably happened.

## Why it matters for an agent

An agent reads code well, so it reaches for code first: open the file, follow the call, decide
what must have happened. That is a theory. The running system's telemetry is an observation of
the same path, with the real inputs, the real timing, and the branch that was actually taken. A
span that never appeared settles "is this code even running" in one query. A log line carrying
the bad value shows where it entered. A latency histogram answers "did it get slower" without a
benchmark harness.

The failure is not ignorance of the telemetry but forgetting it exists. A stack nobody queries
costs its upkeep and returns nothing, so the workflow asks for it at fixed points instead of
waiting to be reminded: `docs/agents/observability.md` records how to read it, diagnosis reads it
before adding print statements, and verification cites it as evidence that the changed path ran.

## In practice

- Before adding a debug line, query what the app already emitted for the failing run. Add
  logging only where the existing record goes quiet, and keep the line if it would have helped.
- After a change, exercise the path once and find its span, log, or metric. "The new endpoint
  returned 200" is a proxy; the span showing it called the store with the right arguments is the
  behavior ([prove it works](prove-it-works.md)).
- An empty result is a finding to explain, not a pass. Either the path did not run, or the
  pipeline is down: check which before concluding anything.
- Instrument new boundaries as you build them: a request handler, an external call, a job, an
  agent tool. Telemetry added after the incident arrives too late for that incident.
- Telemetry is evidence about this run, not about every run. A clean trace does not replace the
  test that guards the behavior; it shows the test is exercising the real thing.
