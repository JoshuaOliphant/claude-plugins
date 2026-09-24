# Prove it works

Check the real thing. A task is finished when its output has been observed working: the feature
run, the actual value read, the diff inspected. An inference from a proxy is not a check.

Forked from the pstack principle of the same name.

## What counts as a proxy

A proxy is anything that stands between you and the behavior you claim: "it compiles", a file's
modification time, a log line saying a step started, a cached screenshot, a subagent's report that
it is done, a test that mocks the thing under test. Proxies feel cheaper than direct observation,
and they usually agree with it. The cases where they do not are exactly the bugs you ship.

## Why it matters for an agent

An agent's natural report is a self-report. It wrote the code, it believes the code is right, and
"done" costs nothing to say. Unverified work has unknown correctness, and a user acting on a wrong
"done" pays far more than the check would have. The same holds one level up: a subagent's summary
is a claim, not evidence, until the claims that matter are checked against the artifact.

Measurements follow the same rule. When two approaches are both defensible, run both and let the
result decide, rather than choosing from documentation claims or plausible reasoning.

## In practice

- Before saying done, run the thing the user will run: the command, the endpoint, the page. Use
  `/run` or `/verify` to drive the app when a test cannot show the behavior.
- Report what you checked and what you saw, including checks that failed. "Tests pass" without the
  output is a claim, not a result.
- Prefer a check you can script and rerun (a test, a comparison script, a query) over a one-time
  look, and leave it where a reviewer can run it again.
- When a check fails unexpectedly, suspect the observation first: the wrong process, a stale
  build, a cached value, the wrong environment. Then suspect the system.
- Test output is part of the evidence. Warnings and error logs in a passing run are either
  asserted on as expected, or they are a finding.
