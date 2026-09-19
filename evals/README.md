# evals/

Skill-trigger eval **fixtures** — **not** a plugin, which is why they live here and
not under `plugins/`.

Each `*-eval.json` file is a list of `{ "query": ..., "should_trigger": bool }`
cases for one skill. They check that a skill's description fires on the requests it
should and stays quiet on the ones it shouldn't:

```json
[
  {"query": "help me create Mochi flashcards for the key concepts", "should_trigger": true},
  {"query": "write documentation for our API endpoints",          "should_trigger": false}
]
```

| File | Skill under test |
|---|---|
| `mochi-creator-eval.json` | `mochi-creator:mochi-creator` |
| `compound-capture-eval.json` | `compound-knowledge:compound-capture` |
| `compound-retrieve-eval.json` | `compound-knowledge:compound-retrieve` |
| `hexagonal-agents-eval.json` | `hexagonal-agents:hexagonal-agents` |
| `bdd-spec-eval.json` | `autonomous-sdlc:bdd-spec` |
| `bdd-generate-eval.json` | `autonomous-sdlc:bdd-generate` |
| `tdd-workflow-eval.json` | `autonomous-sdlc:tdd-workflow` |
| `beads-workflow-eval.json` | `autonomous-sdlc:beads-workflow` |
| `verification-stack-eval.json` | *(orphaned — see below)* |

## Running them

The fixtures are data. What executes them is `claude plugin eval`, which reads cases
from an `evals/` directory **inside a plugin** — never from the marketplace root, so
`claude plugin eval .` at the top of this repo will always report "no eval cases
found". `scripts/gen_trigger_evals.py` compiles these fixtures into real cases under
each owning plugin:

```bash
python scripts/gen_trigger_evals.py --write            # 3 cases per polarity per fixture
python scripts/gen_trigger_evals.py --write --limit 8  # wider sample, proportionally pricier
python scripts/gen_trigger_evals.py --check            # fail if generated cases are stale
```

`--check` runs as part of `scripts/check_all.py`, so a fixture edit that isn't
recompiled fails CI. Generated cases carry a marker comment and are owned by the
script: edit the fixture, not the case.

Then run a plugin's suite:

```bash
cd plugins/compound-knowledge
claude plugin eval . --ablation none                   # whole suite
claude plugin eval . --ablation none --case '*-pos-*'  # positives only
```

Pass `--ablation none` for generated trigger cases. The default `with-without` mode
adds a no-plugin baseline arm, and a skill cannot possibly fire without its plugin
loaded — the second arm is a foregone conclusion that doubles the bill. Ablation
earns its cost on behaviour cases, where the question "is this better than Claude
without the plugin?" has a real answer.

**Cost.** Every case is a full `claude` child run on your own credential, times
`runs` (3 by default) times the number of arms. 48 generated cases at the default
sample is ~144 runs. Use `--case` while iterating, `-j 4` to parallelise, and
`--max-cost-usd` if you want a hard ceiling.

## How a generated case asserts triggering

The grader is a regex over the run trace, pinned to the plugin-qualified skill id
that the `Skill` tool records in its own input:

```yaml
type: regex
target: trace
pattern: "\"skill\":\"compound-knowledge:compound-retrieve\""
match: contains        # not_contains for a should_trigger:false case
```

This is deliberately narrower than `tool_used: Skill`, which only reports that
*some* skill fired. That distinction matters inside a multi-skill plugin: a
"have we seen this before?" query should fire `compound-retrieve` and must *not*
fire `compound-capture`, and only a per-skill assertion can hold both at once. The
`"skill":"` anchor keeps the pattern off the skill listing in the system prompt,
where the same id appears as bare prose.

Trace regexes are free to score — no LLM judge is billed. The cost is the agent run.

## Writing fixture queries

A fixture query becomes an eval prompt verbatim, and the harness attaches nothing to
it. So a query that points at content the user would have pasted — "turn **these
meeting notes** into cards", "make cards from **this article**" — does not test
triggering. The agent correctly answers "I don't see the notes in your message",
loads no skill, and the case fails for a reason that has nothing to do with the
skill description.

Inline enough content to make the request answerable:

```diff
- turn these meeting notes about our API design decisions into flashcards
+ we decided to version the API in the URL path rather than a header, because CDN
+ caching keys off the path. turn that into flashcards
```

Two queries in `mochi-creator-eval.json` had this defect and produced a phantom
"skill never fires" result until the content was inlined; one of them then passed
3/3. Grep new fixtures for `these|this|my <noun>` before trusting a red case.

## Hand-authored cases

Generated cases only answer "did the right skill load?". Cases that test what a
skill actually *produces* are written by hand alongside them, e.g.
`plugins/mochi-creator/evals/flashcards-from-reading/`, which grades drafted cards
against the 5 properties of effective prompts. Those are worth running under the
default `with-without` ablation, since the delta against no-plugin Claude is the
number that says whether the skill is earning its place.

## The orphaned fixture

`verification-stack-eval.json` asserts on a verification surface no skill in this
repo exposes — its queries ("run pytest, ruff and mypy") describe `stick-shift`'s
`/verify`, which is a slash command, and a command never appears as a `Skill` call.
It is excluded from generation rather than mapped to a skill it does not test.
Either give it a real skill to assert on, or retire it.
