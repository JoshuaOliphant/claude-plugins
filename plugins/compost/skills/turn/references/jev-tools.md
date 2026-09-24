# Jev tools for turn

Three typed judgments that `turn` calls through
`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py <tool> --input <file>`. Write the input JSON to a file
from `mktemp`; the output is JSON on stdout. Code gathers the diffs, descriptions, and passages and
applies the thresholds; Jev only picks or checks. Every answer carries its raw probabilities, so you
can overrule a decision you disagree with.

Exit codes: 0 answered, 2 bad input (the message says what is missing), 3 Jev unavailable (no
`TYPESAFE_API_KEY` and no Keychain item `typesafe`, or the API failed). On 2 or 3, make the call
yourself as the calling step describes. Answers are cached by content, so a re-run over unchanged
input costs nothing.

## classify-change

Adopt, adapt, or ignore for each changed upstream file, judged against the text of the compost
skills it fed and compost's rulings. `needs_reading` is false only for an ignore Jev gives at least
0.6; everything else is in `to_read`. Measured on 30 hand-labeled changes from the real drift
(superpowers 448 commits and pstack 141 commits past their earlier pins): all 4 adopt and adapt
changes were sent to be read, and 15 of the 26 ignores were recorded without reading, none of them
wrongly. Jev over-calls adopt and adapt on long diffs that rework ideas compost already has, so
treat its adopt/adapt split as a hint and read those yourself.

Input: `source` (a name in `pile.toml`) and `paths` (upstream paths from `pile.py status`).
`pin` and `head` default to the source's pin and upstream's `origin/HEAD`.

```json
{"source": "superpowers", "paths": ["skills/writing-plans/SKILL.md", "skills/brainstorming/scripts/server.cjs"]}
```

```json
{"tool": "classify-change", "source": "superpowers", "to_read": ["skills/writing-plans/SKILL.md"],
 "changes": [
  {"path": "skills/writing-plans/SKILL.md", "skills": ["slice"], "verdict": "adapt", "confidence": 0.74,
   "probabilities": {"adapt": 0.74, "ignore": 0.21, "adopt": 0.05}, "needs_reading": true},
  {"path": "skills/brainstorming/scripts/server.cjs", "skills": ["spec"], "verdict": "ignore",
   "confidence": 0.99, "probabilities": {"ignore": 0.99, "adopt": 0.01, "adapt": 0.0}, "needs_reading": false}]}
```

## route

Which compost skill each prompt should load, or `none`, from the skills' descriptions alone: the
same choice Claude makes when it picks a skill. `margin` is the gap between the top two skills;
`close` marks a margin under 0.15, where a description edit could tip the choice. The regression set
is `tests/evals/route.json` (30 real prompts with the skills acceptable for each); it routed 27 of
30 to an acceptable skill and all 4 unrelated prompts to `none`.

Input: `prompt` or `prompts`. Output per prompt: `skill`, `margin`, `close`, `probabilities`.

## rulings-lint

Passages of compost's own markdown that drift from its rulings: an unallowed stop for the user,
asking permission to spawn agents, a test-first ritual, a time or context size rule, redaction,
a tracker other than the issue tracker, and new tests where existing ones should be extended. Each
passage gets one probability per rule; a rule flags at 0.5, except an unallowed stop at 0.45 and a
test-first ritual at 0.7. Passages from `spec`, `setup`, `finish`, and slice's map interview carry
a note that the user takes part there, so asking them is not held against the text.

Measured on 36 real passages (24 from compost that an earlier version flagged wrongly, 12 known
violations from superpowers, pstack, Matt Pocock's skills, autonomous-sdlc, and impeccable): 10 of
13 violations caught with 2 to 4 false flags across three runs, where the first version caught 2 of
4 at a third precision. Unallowed stops are the weak rule, with scores for real and false stops
both near 0.45; a clear approval gate scores above 0.6. Over the whole plugin (1,000 passages,
about 1M input tokens) it raised 3 flags. It is a triage aid: read each flag and rule on it.

Input: `{}` lints `skills/`, `canon/`, `agents/`, and `README.md`; `paths` limits it to some files.

```json
{"tool": "rulings-lint", "passages": 1000, "flagged": 1, "flags": {
  "unallowed_stop": [{"file": "skills/slice/references/map-issue.md", "line": 80, "heading": "Charting the map",
    "excerpt": "1. Settle the destination with the user first, in an interview round; it fixes the scope.",
    "probability": 0.459}],
  "asks_to_spawn": [], "tdd_ritual": [], "size_rule": [], "redaction": [], "other_tracker": [],
  "new_test_bias": []}}
```
