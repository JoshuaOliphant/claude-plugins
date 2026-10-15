# {component}

## What it is

What the component does, who depends on it, and what it depends on.

## What healthy looks like

The shape of a normal day in a few sentences: traffic pattern, typical latency, the error
rate you shrug at, how many pods, how often it restarts.

## Signals

One entry per query the superfan runs every pass. Each names the tool, the exact query, and
what normal returns.

### <signal name>

- Tool: `mcp__<server>__<tool>`
- Query: `<PromQL / SPL / Kubernetes call>`
- Normal: <value or range, and how it moves through the day>

## Known patterns

Things that look odd but are expected, with when they happen. The superfan never raises
these.

## Neighbors

Upstream and downstream components, and what their trouble looks like from here.
