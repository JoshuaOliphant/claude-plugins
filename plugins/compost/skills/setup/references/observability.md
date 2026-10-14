# Observability

How setup finds the telemetry a repo's running code emits, and the template for
`docs/agents/observability.md`. The skills read that file to query the running system instead of
guessing at it ([read the running system](../../../canon/read-the-running-system.md)).

## Detection ladder

Run top to bottom and stop at the first rung that matches. Only the last one asks.

1. **The observability harness.** `.claude/harness/observability/status.sh` exists: run it with
   `--json` and record the `mode` and `service` it reports. The query recipes are the
   `observability-query` skill's, for that mode.
2. **Another stack already wired.** Look in the dependencies, config, and app startup code:
   - Logfire: `logfire` in the dependencies, `logfire.configure()` at startup. Read it through the
     Logfire MCP server or `logfire` CLI.
   - Sentry: `sentry-sdk` or `@sentry/*`, `sentry_sdk.init` or `Sentry.init`.
   - OpenTelemetry with an exporter: `opentelemetry-*` exporter packages and an
     `OTEL_EXPORTER_OTLP_ENDPOINT` pointing at Jaeger, Tempo, Honeycomb, or similar.
   - Structured logs to a file: structlog, pino, or a JSON log handler writing somewhere readable.

   Record what is wired and the exact command or tool that reads it. Run one query now. When the
   read path needs a credential or an MCP server that isn't connected, record it as broken with
   its first error, as a broken gate is recorded, and tell the user what would fix it.
3. **Nothing found: ask once.** When the repo runs code (a server, CLI, worker, or agent),
   recommend the harness: the `claude-code-observability-harness` skill installs it, from the
   `observability-harness` plugin (`/plugin install observability-harness@oliphant-plugins` when
   it is missing). Otherwise offer recording the stack the user names, or none. For a library with
   no runtime or a docs-only repo, recommend none. When running unattended, record none and post
   the choice as a ruling, so the user can install the harness later.

## Template for docs/agents/observability.md

````markdown
# Observability

Stack: <observability harness, lite mode, service `<name>` | Logfire project `<name>` | Sentry |
none, because <reason>>.

## Is it up

`<check command>` reports <what up looks like>. When it is down, run `<start command>`.

## Query

| Signal | How |
|---|---|
| Traces | `<command>` |
| Logs | `<command>` |
| Metrics | `<command>` |

## Instrumentation

New spans, metrics, and log fields go in `<module path>`, following the instruments already there.

## How the skills use it

- `compost:diagnose` reads the failing run's telemetry before adding any debug logging.
- `compost:verify` cites the span, log, or metric that shows the changed path ran.
- `compost:build` instruments each new boundary in the module above.
````

For the harness in lite mode the rows are, for example:

| Signal | How |
|---|---|
| Traces | `jq -r '.name // empty' .claude/harness/observability/data/jsonl/traces/$(date +%F).jsonl \| sort \| uniq -c` |
| Logs | `jq -c '{sev: .severity_text, msg: (.message // .body), trace_id}' .claude/harness/observability/data/jsonl/logs/$(date +%F).jsonl` |
| Metrics | `jq -c 'select(.name)' .claude/harness/observability/data/jsonl/metrics/$(date +%F).jsonl` |

With none, keep only the `Stack:` line and its reason. The skills then skip their telemetry steps
without asking again; rerunning `compost:setup` revisits the choice.
