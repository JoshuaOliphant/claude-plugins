# compost

One software-engineering workflow for Claude Code, made by breaking down several skill collections
and rebuilding the best of each: Matt Pocock's skills, obra's superpowers, Lauren Tan's pstack,
Imbue's blueprint and code guardian, and the autonomous-sdlc and stick-shift plugins it replaces.
`NOTICE` lists the sources compost takes text from; `pile.toml` records which upstream files fed which skill.

## How it works

There is no state machine. Each skill ends with **Next moves**, naming the skills that usually
follow and when, so Claude takes the obvious path or steps sideways into diagnosis or design.
Once issues exist, `compost:implement` runs build, verify, and review for each one on its own,
with review done by subagents every time, and records its rulings on the issue.

| Skill | When |
| --- | --- |
| `setup` | Once per repo: issue tracker, domain docs, test gates, AGENTS.md migration |
| `spec` | A fuzzy idea becomes user stories with Given/When/Then acceptance criteria |
| `slice` | A spec becomes tracer-bullet issues in the tracker |
| `implement` | The entry point once issues exist; picks the flow from there |
| `build` | One issue, with its tests fitted into the existing suite |
| `verify` | Before any claim of done: gates, AC-to-test map, the proof ladder |
| `review` | After verify, always: `/compost:review-changes`, then weigh the findings |
| `finish` | Integrate: re-run on the merge target, PR recap, clean up |
| `diagnose` | Any bug or failing test, before a fix |
| `deepen` | Module and interface design, refactoring for testability |
| `pause` | Stop at a safe point and pick the work back up later |
| `fan-out` | Competing designs or hypotheses, tried in parallel and judged |
| `turn` | Check the upstream sources for changes worth working in |

`canon/` holds short essays on the ideas the skills lean on: tracer bullets, ubiquitous
language, deep modules, seams, expand-contract, proving it works, and more. Skills link to the
ones they use.

Work is tracked in the repo's issue tracker (GitHub by default), recorded by `compost:setup` in
`docs/agents/issue-tracker.md`. Domain vocabulary lives in `CONTEXT.md`, decisions in
`docs/adr/`.

## Jev tools

Many steps in the workflow are narrow judgments over lists that code can already produce: which
existing test an acceptance criterion belongs in, whether a review finding is worth a skeptic
subagent, whether an upstream change needs reading. compost hands those to
[TypeSafe Jev](https://docs.typesafe.ai), which answers typed questions (Choice, Noul, Score) in a
second or two for a fraction of a cent, so the frontier model spends its tokens on the rest.

Skills call `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py <tool> --input <file.json>`; `jev.py list`
names them all. Code gathers the candidates, Jev picks or checks, and thresholds in code decide.
Results are cached by content hash in `~/.cache/compost/`. The key comes from `TYPESAFE_API_KEY`
or the macOS Keychain item `typesafe`. Without one, a tool exits 3 and the skill makes the call
itself, so Jev speeds compost up and never blocks it. `jev.py status` checks for a key without
calling the API; `compost:setup` runs it and tells you how to store one.

| Tool | Primitive | Used by | Live eval (cases) |
| --- | --- | --- | --- |
| `find-test` | Choice + Noul | build, diagnose | right test 33/34, extend-or-add 33/34 (34) |
| `duplicate-test` | Noul | build | 23/23 (23 pairs) |
| `ac-exercised` | Noul | verify | 20/22 (22) |
| `test-value` | Score | verify | 24/24 (24 uncovered blocks) |
| `claim-backed` | Noul | verify | 22/22 (22 claims) |
| `triage-finding` | Choice | reviewer, review-changes | serious findings sent to a skeptic 15/15, minor spared 8/11 (26) |
| `review-risk` | Score | review-changes, review | 24–25/28 structural calls (28 files) |
| `canon-pick` | Choice | reviewer | precision and recall ~0.6 (22) |
| `locate` | Choice + Noul | reviewer, spec | anchored 17/18, absent 8/8 (26) |
| `spec-class` | Choice | spec | 21/22, never lighter than labeled (22) |
| `question-value` | Score | spec | 24–25/25 (25 questions) |
| `ac-quality` | Score ×3 | spec | 24/24 (24) |
| `adr-worthy` | Noul ×3 | spec, deepen, implement | 24/24 (24 rulings) |
| `classify-change` | Choice | turn | every adopt/adapt read 4/4, no ignore recorded wrongly, 15/26 ignores skipped (30) |
| `route` | Choice | turn, description changes | 27/30 (30 real prompts) |
| `rulings-lint` | Noul ×8 | turn, compost's own text | 10/13 violations, 2–4 false flags (36 passages) |
| `stop-guard` | Noul ×2 | Stop hook in implement runs | 23/23 (23 final messages) |

Thresholds were chosen from the same labeled cases they are measured on, so treat the numbers as
upper bounds until the tools have run on real work. The labeled cases are drawn from private
projects and sessions, so they live in a separate private repo, `compost-evals`. With a checkout,
`COMPOST_EVALS=<checkout>/evals uv run --group dev pytest -m jev` re-runs every eval against the
live API for a few cents; without one, those tests skip.

## Install

```
/plugin marketplace add joshuaoliphant/claude-plugins
/plugin install compost@oliphant-plugins
```

Then run `/compost:setup` in each repo.

compost replaces several collections that cover the same stages, listed in the `[replaces]` table
of `pile.toml`. Leaving them on gives Claude two answers to every request, so setup finds the ones
still active on the machine and, with your yes, turns them off: it disables their plugins and sets
their personal and skills-CLI skills to `"off"` under `skillOverrides` in `~/.claude/settings.json`.
Plugins synced from claude.ai have to be turned off there. Nothing is deleted, so turning one back
on is a settings change. To check a machine directly: `uv run scripts/pile.py replaced [--apply]`.

## Development

From `plugins/compost` (the 100% coverage gate applies when pytest runs from there):

```sh
uv run --group dev pytest        # tooling tests (100% coverage) and checks on the shipped files
uv run scripts/pile.py status    # upstream changes since each source's pin (Python 3.11+ via uv)
```
