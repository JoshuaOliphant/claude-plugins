"""Declarative description of every setting relaydesk understands.

Each setting has a dotted key (``section.name``), a kind used for coercion,
a default, and optionally the name of an environment variable that can set
it.  The loader walks this table; nothing else in the code base should need
to know where a value came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Setting:
    key: str
    kind: str
    default: object
    env: str | None = None
    help: str = ""
    minimum: float | None = None
    choices: tuple[str, ...] = field(default_factory=tuple)

    @property
    def section(self) -> str:
        return self.key.split(".", 1)[0]

    @property
    def name(self) -> str:
        return self.key.split(".", 1)[1]


SETTINGS: tuple[Setting, ...] = (
    Setting("service.name", "str", "relaydesk", "RELAYDESK_NAME",
            "Name stamped on outgoing envelopes."),
    Setting("service.log_level", "str", "warning", "RELAYDESK_LOG_LEVEL",
            "Python logging level name.",
            choices=("debug", "info", "warning", "error")),
    Setting("service.environment", "str", "development", "RELAYDESK_ENV",
            "Deployment environment label.",
            choices=("development", "staging", "production")),

    Setting("sources.tickets", "path", "data/tickets.jsonl", "RELAYDESK_TICKETS",
            "JSON-lines export of help-desk tickets."),

    Setting("delivery.endpoint", "str", "https://hooks.example.invalid/relay",
            "RELAYDESK_ENDPOINT", "Base URL of the notification webhook."),
    Setting("delivery.transport", "str", "outbox", "RELAYDESK_TRANSPORT",
            "How batches leave the process.",
            choices=("outbox", "webhook")),
    Setting("delivery.batch_size", "int", 25, "RELAYDESK_BATCH",
            "Maximum notifications per delivered batch.", minimum=1),
    Setting("delivery.timeout", "duration", "10s", "RELAYDESK_TIMEOUT",
            "Per-request timeout for the webhook transport.", minimum=0.1),
    Setting("delivery.verify_tls", "bool", True, "RELAYDESK_VERIFY_TLS",
            "Verify webhook TLS certificates."),
    Setting("delivery.outbox_dir", "path", "var/outbox", "RELAYDESK_OUTBOX",
            "Directory the outbox transport writes batches into."),

    Setting("rate.per_minute", "int", 120, "RELAYDESK_RATE",
            "Sustained batches per minute.", minimum=1),
    Setting("rate.burst", "int", 20, None,
            "Batches allowed back-to-back before throttling.", minimum=1),

    Setting("retry.attempts", "int", 3, "RELAYDESK_RETRIES",
            "Delivery attempts per batch.", minimum=1),
    Setting("retry.backoff", "duration", "2s", None,
            "Initial backoff between attempts."),
    Setting("retry.max_backoff", "duration", "30s", None,
            "Upper bound on backoff between attempts."),

    Setting("routing.rules_file", "path", "data/routing.toml", None,
            "Routing rules (category/priority -> channel)."),
    Setting("routing.include_closed", "bool", False, "RELAYDESK_INCLUDE_CLOSED",
            "Also notify about tickets that are already closed."),

    Setting("templates.dir", "path", "templates", None,
            "Directory with message templates."),
    Setting("templates.max_summary", "int", 140, None,
            "Truncate ticket subjects to this many characters.", minimum=10),

    Setting("state.db", "path", "var/state.sqlite3", "RELAYDESK_STATE_DB",
            "SQLite file remembering delivered tickets."),
)

BY_KEY: dict[str, Setting] = {s.key: s for s in SETTINGS}
SECTIONS: tuple[str, ...] = tuple(dict.fromkeys(s.section for s in SETTINGS))


def lookup(key: str) -> Setting:
    try:
        return BY_KEY[key]
    except KeyError:
        raise KeyError(f"unknown setting {key!r}") from None
