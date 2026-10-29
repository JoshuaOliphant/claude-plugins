# relaydesk

Relays help-desk tickets to chat webhooks. Tickets from the help-desk export
(`data/tickets.jsonl`) are routed to a channel by `data/routing.toml`, rendered
with the templates in `templates/`, grouped per channel into batches and handed
to a transport (an outbox directory, or the webhook directly).

```
python -m relaydesk send --dry-run          # plan batches, deliver nothing
python -m relaydesk send --dry-run --json   # one JSON object per batch
python -m relaydesk send                    # deliver and remember delivered tickets
python -m relaydesk list --limit 10         # most pressing tickets
python -m relaydesk config                  # effective configuration
python -m relaydesk stats | templates | reset-state
```

## Configuration

Edit `config/relaydesk.toml`. Settings are layered, lowest to highest:
built-in defaults, `config/relaydesk.toml`, an optional
`config/relaydesk.local.toml`, environment variables, command-line flags.

| setting               | env var               | flag            |
|-----------------------|-----------------------|-----------------|
| delivery.endpoint     | RELAYDESK_ENDPOINT    | --endpoint      |
| delivery.transport    | RELAYDESK_TRANSPORT   | --transport     |
| delivery.batch_size   | RELAYDESK_BATCH       | --batch-size    |
| delivery.timeout      | RELAYDESK_TIMEOUT     |                 |
| delivery.verify_tls   | RELAYDESK_VERIFY_TLS  |                 |
| rate.per_minute       | RELAYDESK_RATE        |                 |
| retry.attempts        | RELAYDESK_RETRIES     |                 |
| routing.include_closed| RELAYDESK_INCLUDE_CLOSED | --include-closed |
| service.log_level     | RELAYDESK_LOG_LEVEL   | -v / -vv        |

`RELAYDESK_CONFIG` (or `--config`) points at a different config file.
Durations accept `250ms`, `15s`, `2m`; booleans accept `true/false`, `1/0`,
`yes/no`, `on/off`.

Message wording can be changed per deployment by dropping a template with
the same name into `templates/overrides/`.
