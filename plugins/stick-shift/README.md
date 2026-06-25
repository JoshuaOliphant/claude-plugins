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
| `/verify` | VERIFY | Runs the suite + the project's own checks, proves each criterion in code, applies pertinent review skills |
| `/journal` | — | Renders the durable session record |

`/spec` also creates a `stickshift/{slug}` feature branch if you aren't already on one.

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

## Next increment (after DONE)

Work arrives in waves, so `DONE` is not the end of the road. When a finished
(`state: DONE`) stick-shift session needs the *next* increment, `/spec` runs
`session_state.py increment --feature <new> --request "<task>"`. It archives the finished
increment into `increments[]`, retargets `feature`/`request` (so `status` never lies),
bumps the `cycle` counter so the durable records stay grouped per increment, and resets
to `INIT` — so the new `/spec` transitions on-graph with no nudge. This is the
first-class path; never force an off-graph `DONE → SPEC` or hand-edit `state.json`.

## State CLI

`python3 scripts/session_state.py --help` documents the manual operations: `init`,
`state`, `status`, `transition`, `decide`, `increment`, `note-progress`, `task`,
`journal`, `takeover`.

Every `transition`, `decide`, and `increment` stamps the current short commit SHA and
the increment `cycle` onto the record entry — a foreign key joining each entry to the
code it describes (`git log <entry-sha>..<next-sha>` recovers a phase's work). `status`
and `journal` surface the branch, cycle, and per-entry SHA.
