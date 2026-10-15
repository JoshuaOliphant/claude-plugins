---
name: setup
description: >-
  Sets up a superfan: a headless Claude that watches one component's telemetry on a local
  schedule through read-only MCP tools (Splunk, Prometheus, Kubernetes, Datadog, ...) and
  raises a desktop notification when it sees something a threshold alert would miss. Use
  when the user says "set up a superfan", "make a superfan for <component>", "watch
  <component> for me", "add a superfan", or wants to change an existing superfan's charter,
  signals, tools, or schedule.
---

# Set up a superfan

A superfan is only as good as its charter. Your job here is to build one with the user from
real query results, not from guesses, then put it on a schedule.

The runner is `${CLAUDE_PLUGIN_ROOT}/scripts/superfan.py` (call it `SF` below; run it with
`python3`). Every file lives in `${SUPERFAN_HOME:-~/.superfans}/<component>/`; the script's
docstring lists them.

## 1. Data policy first

Ask once: is sending this component's metrics and logs to Claude within their employer's
data and AI policy? Logs carry customer data that metrics do not. If they are unsure, stop
and say what they need to check. Do not continue on a guess.

## 2. Interview

One component, named in lowercase with hyphens. Ask, one at a time, only what you cannot
find out from the tools:

- What does it do, who calls it, what does it call?
- What does a normal day look like? When is it busiest?
- What do you look at first when it is on fire? (These dashboards and searches become
  signals.)
- What looks scary but is fine? (Batch jobs, deploy windows, a noisy health check. These
  become Known patterns.)
- Which neighbors' trouble shows up here first?

## 3. Choose the tools, read-only only

List the MCP tools you can see for the user's telemetry servers. Sort them into read and
write. Anything that mutates, scales, restarts, deletes, executes, or acknowledges is write,
and when a name is ambiguous it is write. Show the user the read list and get a yes. Those
exact names go in `allowed_tools`; the script rejects wildcards and bare server prefixes.

## 4. Probe the signals for real

For each candidate signal, run the query now with those tools and show the user what came
back. Cover the four golden signals where they apply (traffic, errors, latency, saturation),
plus restarts and pending pods from Kubernetes and the top error signatures from logs.

- Keep a query only if it returns data and the user agrees it means something.
- Pull history (7 days where the backend allows) to see the daily and weekly shape. That
  shape is the baseline; one point-in-time value is not.
- Prefer queries that answer in one call. Every query runs every pass, and the run has a
  budget.

## 5. Write it down

```bash
python3 SF init <component>
```

Then fill in, in that directory:

- `charter.md`: every section, with each signal's tool, exact query, and normal range.
- `baselines.md`: the shapes you saw in history, per signal, by hour and weekday.
- `superfan.toml`: `allowed_tools`, `cadence_minutes` (60 is a good start), `model`,
  `max_budget_usd`, `active_hours`, and `neighbors` if other superfans exist. If the user's
  MCP servers are configured somewhere a headless run will not find them, write an
  `mcp.json` with just those servers and set `mcp_config`.

## 6. Prove it runs

```bash
python3 SF notify-test <component>   # needs `brew install terminal-notifier`
python3 SF run <component>
```

`run` prints one line: status, cost, and counts. If it reports denied tool calls, a query in
the charter uses a tool that is not in `allowed_tools`; fix whichever is wrong. If it fails,
read the newest file in `runs/`. Do not schedule a superfan that has not completed one clean
run. Outside `active_hours` a run is skipped, so test inside them.

## 7. Schedule it

```bash
python3 SF install <component> --load
```

This writes `~/Library/LaunchAgents/com.superfan.<component>.plist`, copies the runner to
`~/.superfans/bin/` so plugin updates do not break it, and loads it. Re-run it after changing
`cadence_minutes` or updating the plugin. `SF uninstall <component>` stops it.

## 8. Hand over the experiment

Tell the user how the loop works and what to measure:

- Page-worthy findings raise a notification. Clicking it opens `/superfan:triage` on that
  finding. Everything else lands in `digest/<date>.md`, with one heartbeat line per run.
- Give every finding a verdict (real, noise, or known). The ledger is how the superfan stops
  repeating itself.
- After a week, `python3 SF stats <component>` gives runs, cost, verdicts, and page
  precision. That number decides whether the superfan earns a second component.

## Next moves

- `/superfan:triage <component> <finding-id>` for an open finding.
- `/superfan:setup` again for the next component, listing this one as a neighbor.
