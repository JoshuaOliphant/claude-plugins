# Stick Shift

Manually-driven ("disassembled") SDLC. Same `.sdlc/` **session** format as
`autonomous-sdlc`, but you swap the autonomous Stop-hook **harness** for one you drive
by hand: five slash commands, one phase each, every one ending by handing control back
to you.

```
/spec "<task>"  →  /plan  →  /build [task]  →  /verify  →  /journal
```

| Command | Phase | Does |
|---|---|---|
| `/spec "<task>"` or `/spec <file>` | SPEC (+init) | Starts from a task or an existing spec/plan file; adopts any in-progress `.sdlc/` session; writes 3–5 Given/When/Then criteria |
| `/plan` | PLAN | Decomposes into a task list; logs key decisions |
| `/build [task]` | BUILD | TDD one task (red→green→refactor), then stops |
| `/verify` | VERIFY | Runs the suite + walks each criterion |
| `/journal` | — | Renders the durable session record |

The `.sdlc/` directory (state.json, progress.md, decisions.jsonl) is the durable
session — it survives context loss, and it is what a shared corpus (e.g.
`compound-knowledge`) would ingest. The harness is disposable; the session survives.

REVIEW is the built-in `/code-review` skill, run ad hoc. There is no SHIP — `/journal`
is the close.

## Executable spec compliance

The Given/When/Then criteria are proven **in code**, not by reading. `/spec` picks the
project's test convention once (adopt an existing pattern → default by stack, Python →
pytest-bdd → ask only if greenfield), records it in the session, and `/verify` then maps
every criterion to a passing test in that convention. See
[`references/test-conventions.md`](references/test-conventions.md).

## Adopting an existing session

`/spec` is idempotent and resumes any `.sdlc/` already on disk — including one created by
`autonomous-sdlc`, since both share the session format. If that session was being driven
by the autonomous loop (its `driver` is `auto`/`stop-hook`), `/spec` runs
`session_state.py takeover` to stand the autonomous driver down, so the two harnesses
don't fight over one session. That's the "swap the harness over a durable session" move.
To hand back the other way, re-arm the autonomous driver (`sdlc_state.py set-driver auto`)
and run `/sdlc`.

You can also seed `/spec` from an upstream plan — `/spec docs/.../my-plan.md` ingests it,
normalizes its criteria into the testable contract, and records a `Source:` pointer.

## State CLI

`python3 scripts/session_state.py --help` documents the manual operations: `init`,
`state`, `status`, `transition`, `decide`, `note-progress`, `task`, `journal`, `takeover`.
