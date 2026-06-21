# Stick Shift — Design

**Date:** 2026-06-20
**Status:** Design approved; pending implementation plan
**Author:** Joshua Oliphant (with Claude)

## Context

Preparation for a **Shopify pair-programming interview** (75 minutes, live, cold
start — the task is sprung at the start) for a **developer-experience** role. The
candidate will demo "how I work with AI" using Claude Code, most likely on a
commerce-flavored task, in **Python** (stack is the candidate's choice).

Stick Shift is a **manually-driven ("disassembled") variant of the `autonomous-sdlc`
plugin**: same SDLC discipline (spec → plan → TDD build → verify), but the candidate
drives each phase by hand so every transition becomes a narratable beat, instead of an
autonomous loop running the whole thing unattended.

The framing deliberately echoes Shopify's "Under the River" essay
(<https://shopify.engineering/under-the-river>), which decomposes an agent system into
**Session / Harness / Sandbox** and asserts *"the session is the thing that must
survive"* and *"agent-friendly ≈ human-friendly."*

## Goals

Optimize the demo for, in priority order:
1. **AI-collaboration craft** — decomposition, sharp prompting, verification rigor,
   catching the agent's mistakes.
2. **DX / tooling taste** — the workflow itself is a designed developer experience.
3. **Live judgment & narration** — reasoning out loud, resolving ambiguity decisively
   under observation.

Explicitly **not** a goal: shipping a polished commerce feature. The deliverable is the
vehicle; the process is the star.

## Non-Goals

- No autonomous loop, Stop-hook driver, or iteration/attempt budgets.
- No real PR/SHIP (no remote to ship to in an interview).
- No bespoke review machinery — reuse the built-in `/code-review` skill ad hoc.
- No git worktrees / parallel builders (single-player, single-task-at-a-time demo).

## Architecture: shared Session, swappable Harness

The spine of the design is that Stick Shift **shares the Session layer with
`autonomous-sdlc` and swaps only the Harness.**

| Aquifer concept | In Stick Shift |
|---|---|
| **Session** (durable, must survive) | The `.sdlc/` on-disk state: `state.json`, `progress.md`, `decisions.jsonl`. Identical format to the autonomous plugin. |
| **Harness** (disposable, replaceable) | **Manual slash commands the candidate invokes** — instead of the autonomous Stop-hook loop. |
| **Sandbox** (ephemeral, reproducible) | The demo repo itself (git). |

This makes the two plugins a literal instance of *"the harness is replaceable over a
durable session."* On camera, pointing at `.sdlc/`:

> "Same session format. Two harnesses over it — one drives itself, this one I drive.
> The session survives either way."

The reuse is honest and subtractive: `sdlc_state.py` already supports the manual ops
(`transition`, `decide`, `note-progress`, `task`, `status`). The autonomous-only parts
are just the Stop-hook driver and `tick` budgets. Disassembling = keep the state layer
and the skill bodies, drop the loop driver, add thin per-phase commands.

## Command set

Five thin commands, each a distinct narration beat:

| Command | Phase | What it does | Narration beat |
|---|---|---|---|
| `/spec "<task>"` | SPEC (+ init) | Auto-inits `.sdlc/` + a branch; writes 3–5 Given/When/Then criteria | "Before any code — what does 'done' mean?" |
| `/plan` | PLAN | Short decomposition into a task list; logs key decisions to `decisions.jsonl` | "How I break this down — and a call I'm making, with the why." |
| `/build [task]` | BUILD | TDD **one** task (red → green → refactor), then stops | "Watch the test drive the code." (repeat per task) |
| `/verify` | VERIFY | Runs the suite + walks each criterion | "Passing ≠ satisfied — let me prove each one." |
| `/journal` | — | Prints decisions + progress + criterion status | Close: "the durable record that survived the whole session." |

**Pruned from the full SDLC machine:**
- **INIT** folds invisibly into `/spec` (no setup ceremony on a cold clock).
- **REVIEW** is the built-in `/code-review` skill, invoked ad hoc — reusing platform
  tooling is itself a DX signal. No bespoke wrapper.
- **SHIP** is dropped; `/journal` is the close.

### Signature ergonomic

Every command ends by **handing control back with a visible decision point and a
suggested-next-command that is only a suggestion.** The workflow never runs ahead. That
pause-at-every-boundary *is* the brain/hands decoupling, performed live. Example: `/plan`
ending in *"3 tasks ready; I'd start with the inventory check since it's riskiest — your
call."*

Commands reuse the state machine's transition validation, but a wrong-order call (e.g.
`/build` before `/spec`) is a **friendly nudge**, not a hard block.

## The 75-minute walkthrough

Illustrative running example (whatever they hand the candidate maps to this rhythm):
*"Build a cart pricing engine: subtotal, stackable discounts, tax, rounding."* Pure
Python, rich edge cases, no infra.

| Time | Beat | Showing |
|---|---|---|
| 0:00–0:05 | **Frame it** — one line on the approach; show `.sdlc/` empty | Let the meta emerge; don't lecture |
| 0:05–0:12 | **`/spec`** → 3–5 Given/When/Then; narrate one assumption | "What does done mean" |
| 0:12–0:22 | **`/plan`** → 3–4 tasks + a logged decision (`Decimal` not float, and why) | Judgment, made visible |
| 0:22–0:55 | **`/build × N`** → TDD each task | Craft + catching the AI; task-order choice is a beat |
| 0:55–1:03 | **`/verify`** → full suite + walk criteria | "Passing ≠ satisfied" |
| 1:03–1:08 | **`/code-review`** (built-in, optional) | Reusing platform tooling + acting on feedback |
| 1:08–1:13 | **`/journal`** → decision log + criterion status | Close; tie to "Under the River" corpus |
| 1:13–1:15 | Wrap / questions | |

**Narration assets baked in:**
- **Decide-log-proceed under ambiguity** — when something is unclear, *"I'll decide and
  log it"* (`decide`). Decisive + auditable beats rabbit-holing.
- **Resumability as a flex** — interrupted by a tangent, resume exactly where you were:
  *"the harness forgot nothing — the session is the source of truth."*

**Contingencies:** running long → drop review, fewer build tasks; short → deeper
refactor or an extra task. No phase is load-bearing on memory.

**Meta-tip:** explain each command the *first* time it runs, then let it flow.

## The multiplayer gap (deliberate answer)

"Under the River" is multiplayer/public-by-default: *"if every interaction happens in a
private window, the only person who learns is the one at the keyboard."* Stick Shift is
single-player and local — by design for the demo. The bridge to acknowledge if asked:
`decisions.jsonl` + `progress.md` are already a shareable corpus, and the
`compound-knowledge` plugin (capture → retrieve → graduate) is exactly the
"corpus-is-the-compounding-asset" mechanism. The `/journal` close is where this point
lands.

## Packaging

- **A new, self-contained plugin** in the `oliphant-plugins` marketplace — not an
  extension of `autonomous-sdlc`, and not a throwaway repo. Separateness is what makes
  the "two independent harnesses" story honest.
- **Self-sufficient for interview safety:** ships its own trimmed `session_state.py`
  (manual ops only — `transition`, `decide`, `note-progress`, `task`, `status`; no
  `tick`/driver/budgets). The five commands carry their phase guidance inline (or as
  tiny skills) so the plugin does not depend on `autonomous-sdlc` being installed.
- **Optional later upgrade (not for interview day):** register the session CLI in
  `scripts/shared/` and let `sync_shared.py` keep both plugins' copies from diverging —
  the candidate's own existing no-divergence pattern. YAGNI until after the interview.
- **Hard rule:** pre-install and **rehearse** Stick Shift on a clean checkout before the
  interview. The commerce repo is created live; the plugin is not.

## Success criteria

- Five commands (`/spec`, `/plan`, `/build`, `/verify`, `/journal`) run reliably on a
  clean checkout with no dependency on `autonomous-sdlc`.
- Each command does exactly one phase, writes its artifact to `.sdlc/`, records to the
  shared Session, and ends by handing control back with a decision point.
- A full dry run of the 75-minute walkthrough completes inside the time box with buffer.
- The candidate can narrate every piece of the plugin from memory.

## Open questions / risks

- **Phase guidance: inline vs. tiny skills.** Inline in `commands/*.md` is simplest and
  most self-contained; tiny skills are more reusable. Default to inline for interview
  day unless rehearsal shows a reason to extract.
- **`session_state.py`: trimmed copy vs. shared-source.** Ship the trimmed copy first;
  decide on `sync_shared` wiring post-interview.
- **Ceremony creep.** The biggest failure mode is the workflow looking like process for
  its own sake. Every command must visibly earn its place during rehearsal; cut any that
  doesn't.

## Addendum (PR #16 review): executable spec compliance + test-convention detection

PR review raised that `/verify` checked the Given/When/Then criteria by *reading* — the
"passing ≠ satisfied" gap done by hand. Resolution: make compliance **executable**, with
the test framework **detected per project** rather than hardcoded (the plugin runs in
arbitrary repos).

- **Decide-log-proceed detection ladder** (in `references/test-conventions.md`), run once
  at `/spec`: (1) adopt any existing test pattern — no question; (2) no tests but stack
  clear → default by stack (Python → pytest-bdd) and log it — no question; (3) greenfield
  and ambiguous → ask, with a recommendation. Avoids a config-wizard interruption mid-demo.
- **Convention recorded once in the session** — in the spec header (`Test convention:
  <name>`) and as a logged `decide` entry — so it appears in `/journal` and both `/build`
  and `/verify` honor it. No `session_state.py` change required.
- **`/build`** writes each test in that convention, tied to the criterion it covers
  (pytest-bdd `Scenario` for AC-N, or `test_acN_*`). **`/verify`** maps every AC to a
  passing test; an untested or failing criterion is unmet → back to BUILD.

This generalizes the plugin beyond Python and turns the test convention into part of the
durable session. Plugin version `0.1.0 → 0.2.0`.

## Addendum (workflow fit): upstream specs + session handoff

Two follow-ups so Stick Shift slots into an existing workflow:

- **`/spec` accepts an upstream spec file**, not just a free-text task. If `$ARGUMENTS` is
  a path (a `/blueprint` plan or superpowers design doc), `/spec` ingests it, normalizes
  its criteria into the testable Given/When/Then contract in `specs/{slug}-spec.md`, and
  records a `Source:` pointer (point-in-time). Free-text input keeps the cold-start
  behavior. Detection is by "is it an existing file path?" — no new flag.
- **Clean takeover of an autonomous-sdlc session.** Both tools share `.sdlc/`, and
  `session_state.py` round-trips the superset schema (verified: autonomous keys —
  `driver`/`budgets`/`attempts`/`review` — survive a stick-shift `save()`). The one
  conflict is the autonomous Stop hook, which drives whenever `driver` is `auto`/
  `stop-hook`. New `session_state.py takeover` sets `driver` → `stick-shift` (any non-
  `auto`/`stop-hook` value makes the autonomous hook exit), and `/spec` runs it when it
  adopts such a session. This is the bidirectional "swap the harness over one durable
  session" in practice. Reverse handoff (manual → autonomous) is deliberately explicit:
  re-arm with `sdlc_state.py set-driver auto`, then `/sdlc`. (A symmetric `handoff`
  command is a possible future enhancement C.)

Note: stick-shift's `transition` only targets its own states (INIT/SPEC/PLAN/BUILD/
VERIFY/DONE); it cannot move *into* autonomous-only states (REVIEW/SHIP/REPAIR/BLOCKED) —
use autonomous's own CLI for those. Plugin version `0.2.0 → 0.3.0`.

## Addendum (PR #16 review, verify.md): detect-and-use project validations

Same detect-and-adapt principle extended to verification. `/verify` should not assume the
gate is just the test runner — it discovers what this project and the installed skills
offer and uses what's pertinent to the change (`references/validations.md`):

- **Project-defined gates → detect and run** (they exist to be run): linters, type
  checkers, `make`/`just` targets, `scripts/*verify*`, `pre-commit`, `package.json`
  scripts; CI commands define "green".
- **Review/quality skills → use what's pertinent, decide-log-proceed** (per La Boeuf:
  the verifier may use available skills without asking, surfacing only when it genuinely
  needs input — a gentle nudge, not a gate): `/code-review`, `vet`, `security-review`;
  `/simplify` only after green, then re-verify (it mutates), revert if it broke something.

Plugin version `0.3.0 → 0.4.0`.
