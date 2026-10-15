# superfan

A superfan is a Claude that cares about exactly one component and has nothing better to do
than refresh its charts. The idea comes from Anthropic's
[source control post](https://www.anthropic.com/engineering/redesigning-source-control): they
catch subtle and novel issues that threshold alerts miss.

This plugin runs superfans locally on macOS, against whatever read-only telemetry MCP servers
you already have (Splunk, Prometheus, Kubernetes, ...), and gets your attention with a desktop
notification instead of a chat channel.

## How it works

```
launchd (every N min, active hours only)
  └─ superfan.py run <component>
       ├─ prompt = watch prompt + charter + baselines + long-term memory + 24h journal
       │           + open findings + verdicts + neighbors
       ├─ claude -p --tools "" --allowedTools <exact read-only MCP tools> --permission-mode dontAsk
       │            --json-schema <report> --max-budget-usd <cap>
       └─ report → inbox/ findings, digest/ heartbeat, journal.md, long_term.md, baselines.md,
                   notification
click notification → Terminal → /superfan:triage → verdict → ledger.jsonl → next prompt
```

- **Least privilege by construction.** The headless run has no built-in tools (no Bash, no
  file writes) and only the exact MCP tool names you approved. Anything else is denied, not
  prompted. The script does all the writing.
- **Fresh sessions, curated memory.** Each pass starts clean and rereads what is worth
  keeping: its own journal notes from the last 24h (what it noticed, what to recheck),
  a long-term memory it rewrites itself, baselines, and your verdicts. Values over time stay in
  the telemetry backend; the memory holds judgments. Every file is plain markdown you can edit,
  so a wrong belief is one line to delete, not a poisoned session.
- **Verdicts are enforced.** Every verdict (real, noise, known) goes into the next prompt, and
  the runner drops `known` fingerprints for good and `noise` ones for a week, whatever the
  model says.
- **A blind superfan is loud.** A crash, a timeout, or a pass that can't reach its tools all
  count as failures; after three in a row you get one notification.
- **Neighbors.** A superfan can read other superfans' last 24 hours of findings, so the
  consumer superfan knows the broker superfan saw ISR shrink twenty minutes ago.

## Use

```
/superfan:setup              # interview, pick read-only tools, probe signals, schedule
/superfan:triage <component> # go through findings and record verdicts
```

`brew install terminal-notifier` for clickable notifications. `notify = "command"` in
`superfan.toml` sends anywhere a shell command can reach (a Teams Workflows webhook, for one).

After a week: `python3 scripts/superfan.py stats <component>` gives runs, cost, verdicts, and
page precision.
