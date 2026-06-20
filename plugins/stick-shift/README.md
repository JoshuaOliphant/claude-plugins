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
| `/spec "<task>"` | SPEC (+init) | Inits `.sdlc/` + a branch; writes 3–5 Given/When/Then criteria |
| `/plan` | PLAN | Decomposes into a task list; logs key decisions |
| `/build [task]` | BUILD | TDD one task (red→green→refactor), then stops |
| `/verify` | VERIFY | Runs the suite + walks each criterion |
| `/journal` | — | Renders the durable session record |

The `.sdlc/` directory (state.json, progress.md, decisions.jsonl) is the durable
session — it survives context loss, and it is what a shared corpus (e.g.
`compound-knowledge`) would ingest. The harness is disposable; the session survives.

REVIEW is the built-in `/code-review` skill, run ad hoc. There is no SHIP — `/journal`
is the close.

## State CLI

`python3 scripts/session_state.py --help` documents the manual operations: `init`,
`state`, `status`, `transition`, `decide`, `note-progress`, `task`, `journal`.
