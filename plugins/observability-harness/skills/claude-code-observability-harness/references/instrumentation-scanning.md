# Instrumentation Scanning

The mechanical half of this skill (copying scripts, wiring the hook) is trivial. The half
that matters is deciding **what to instrument** — and that is genuinely project-specific.
Two harnesses this skill was extracted from instrument completely different things: an
event-bus library counts produced/consumed events and batch sizes; an agent web app times
tool calls and counts LLM tokens per agent. Copying one's instruments into the other would
be noise. So: **scan, propose, confirm, then apply.** Never silently write instruments.

## The three point-types

Most backends have telemetry value at three kinds of sites. Scan for each; not every
project has all three.

### 1. Boundary / unit-of-work call sites → a latency histogram + a span

The places where the app does one discrete, externally-meaningful thing: a tool call, an
HTTP route handler, a job step, a query, an RPC. These are where a `span` and a
`*.latency` histogram (labelled by operation name) pay off.

**Detection signals:**
- Files named `tools.py`, `*_tools.py`, `*_commands.py`, `handlers.py`, `routes.py`, `api.py`
- Decorators: `@tool`, `@mcp.tool`, `@app.get/post/...` (FastAPI/Flask), `@task`, `@command`
- Functions that are the public surface of a module (called from elsewhere, not helpers)
- Signatures like `async def name(args: dict)` / `def handle(request)` / `def run(...)`

**Instrument:** `histogram("<thing>.latency", unit="ms", by={"<name-field>"})` plus an
optional `span("<thing>")` wrapping the body. A decorator (`@_timed`) is the cleanest
application when sites share a signature.

### 2. Dispatch / routing / branching sites → a counter (+ a span)

The narrowest point where "an input arrives and a destination is chosen." Routers,
dispatchers, message handlers, event consumers, state-machine transitions. A counter
labelled by `{from, to}` or `{kind}` reveals the flow shape; a span captures the decision.

**Detection signals:**
- Names: `route`, `dispatch`, `handle_message`, `process`, `forward`, `consume`, `on_event`
- Code that inspects an input and branches to different handlers/agents/topics
- Pub/sub or event-bus produce/consume seams (`produce`, `publish`, `emit`, `consume`)

**Instrument:** `counter("<flow>.messages"|"<flow>.events", by={"from","to"}|{"topic"})`.
For producer/consumer systems, count **both** sides — the gap (produced − consumed) is
often the single most useful number (consumer lag).

### 3. Result / completion sites → a histogram of a meaningful magnitude

Where an expensive operation resolves and reports a magnitude worth tracking: LLM token
usage, batch size, bytes processed, rows returned, retry count.

**Detection signals:**
- Return values that are `ResultMessage`, `ModelResponse`, or anything with `.usage`
- Field names `input_tokens` / `output_tokens` / `total_tokens`, `batch`, `count`, `size`
- Anthropic/OpenAI SDK resolution points: `client.messages.create(...)`, `await agent.run(...)`
- Loop accumulation points: "we just processed N of something"

**Instrument:** `histogram("<op>.tokens"|"<op>.batch_size"|"<op>.<magnitude>", by={...})`.
The `sum` of the histogram gives the running total; the distribution shows the spread.

## Workflow

1. **Scan.** Grep for the signals above across the source tree. Read the few files that
   match to confirm they're real instrumentation points, not false hits.
2. **Find the configure() site.** Where does the app start? (FastAPI `lifespan`, CLI
   `main()`, `if __name__ == "__main__"`.) `otel.configure()` goes there, once.
3. **Propose.** Present a compact, concrete plan and STOP for confirmation:
   ```
   service.name: reading-tracker
   configure() at: app/main.py lifespan (line ~42)
   Proposed instruments (3):
     tool.latency   (histogram, ms, by=tool)   → @_timed on 7 tools in app/tools.py
     router.messages(counter, by=from/to)       → record in app/agents/router.py:118
     agent.tokens   (histogram, by=agent)        → record at LLM resolve in base_agent.py:64
   Spans: router.user_message wrapping the dispatch
   ```
4. **Confirm, then apply.** Add instruments to `otel.py`'s `_build_instruments()` + a
   `record_*` helper each, wire the call sites, and add `configure()` at startup. Apply
   only what's confirmed — a silent write is wrong if the project's shape differs from
   your guess.
5. **Verify** (SKILL.md step 6): exercise the real call sites once and confirm the *domain*
   instruments fired with real labels — not just a synthetic probe.

## Why propose-then-apply, not auto-apply

The detection signals are heuristics. A function named `process` might be the central
dispatcher or an irrelevant string helper. The user knows their codebase; a 20-second
confirmation prevents instrumenting the wrong layer (e.g. timing a thin wrapper instead of
the real work underneath). The cost of asking is tiny; the cost of plausible-but-wrong
instrumentation is a misleading dashboard that erodes trust in the whole harness.
