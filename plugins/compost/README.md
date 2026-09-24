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

## Install

```
/plugin marketplace add joshuaoliphant/claude-plugins
/plugin install compost@oliphant-plugins
```

Then run `/compost:setup` in each repo.

compost replaces several collections that cover the same stages. Leaving them on gives Claude
two answers to every request, so switch them off: disable their plugins in `/plugin`, and for
skills installed outside a plugin add `"<skill-name>": "off"` under `skillOverrides` in
`~/.claude/settings.json`. Nothing is deleted, so turning one back on is a settings change.

## Development

From `plugins/compost` (the 100% coverage gate applies when pytest runs from there):

```sh
uv run --group dev pytest        # tooling tests (100% coverage) and checks on the shipped files
uv run scripts/pile.py status    # upstream changes since each source's pin (Python 3.11+ via uv)
```
