# Jev tools for review

Four typed judgments that review, the `compost:reviewer` agent, and spec call through
`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py <tool> --input <file>`. Write the input JSON to a file
from `mktemp`; the output is JSON on stdout. Code lists the candidates and applies the thresholds;
Jev only picks or checks. Every answer carries its raw probabilities or scores, so you can overrule
a decision you disagree with.

Exit codes: 0 answered, 2 bad input (the message says what is missing), 3 Jev unavailable (no
`TYPESAFE_API_KEY` and no Keychain item `typesafe`, or the API failed). On 2 or 3, make the call
yourself as the calling step describes. Answers are cached by content, so a re-run over unchanged
input costs nothing.

## triage-finding

How severe each review finding is, and whether a skeptic is worth spawning to refute it. A skeptic
is worth it when P(blocker) + P(major) is at least 0.3, or when Jev's confidence is under 0.25.
Measured on 26 labeled findings from this repo's review history: every blocker and major was sent
to a skeptic in three runs, and 7 or 8 of the 11 minor or not-a-finding cases were spared one.

Input: `findings` (each needs `file` and `claim`; `line` and `evidence` are optional), plus `base`
and `head` so the tool can cut the diff hunk around each line. A finding may carry its own `hunk`.

```json
{"base": "3f1c2a9", "head": "HEAD", "findings": [
  {"file": "scripts/pile.py", "line": 67, "claim": "A missing git binary escapes as a traceback",
   "evidence": "pile.py:67 `subprocess.run([\"git\", *args], ...)` with no except"}]}
```

```json
{"tool": "triage-finding", "skeptics": 1, "findings": [
  {"file": "scripts/pile.py", "line": 67, "claim": "A missing git binary escapes as a traceback",
   "severity": "major", "confidence": 0.74, "worth_skeptic": true,
   "probabilities": {"blocker": 0.02, "major": 0.87, "minor": 0.08, "not-a-finding": 0.03}}]}
```

## review-risk

Each changed file's structural risk on five levels: 0 cosmetic, 1 local logic, 2 new behavior
inside one module, 3 an interface change (a public signature, CLI, schema, file format, or an
instruction contract others rely on), 4 new structure (a new module boundary, shared state, a new
dependency, a new data flow). A file scoring 2.5 or more is `structural`; the run is structural when
any file is. Measured on 28 labeled files from 24 commits over two runs: 24 or 25 right, precision 0.86 to 0.92, recall 0.86.

Input: `base`, and optionally `head` (default `HEAD`) and `repo` (default the working directory).

```json
{"tool": "review-risk", "structural": true, "files": [
  {"file": "scripts/cache.py", "score": 3.64, "confidence": 0.81, "structural": true},
  {"file": "README.md", "score": 0.03, "confidence": 0.97, "structural": false}]}
```

## canon-pick

Which canon essays a reviewer of this change should read. One Choice over every essay (its title
and opening paragraph) plus `none` asks whose warning is most at stake; the essays at 0.15 or more
come back, at most three, most at stake first. `probabilities` has every option. A Choice beat
scoring each essay on its own: on 22 labeled changes it reached precision 0.59 to 0.62 and recall
0.59 to 0.65 across three runs, against 0.52 and 0.62 for per-essay scores, at half the tokens, because generic essays like prove-it-works scored
"relevant" on nearly every change. It is a reading list, not a verdict: about two picks in five
are ones a careful reviewer would skip.

Input: `summary` (commit messages and the key hunks), or `base` and `head` to summarize the range.

```json
{"tool": "canon-pick", "essays": [
  {"essay": "boundary-discipline.md", "title": "Boundary discipline", "probability": 0.62},
  {"essay": "tracer-bullets.md", "title": "Tracer bullets", "probability": 0.26}],
 "probabilities": {"boundary-discipline": 0.62, "tracer-bullets": 0.26, "prove-it-works": 0.07, "none": 0.01}}
```

## locate

The line of a file a claim or question is about, following TypeSafe's line-search cookbook: one
Choice over the numbered lines, and one Noul for whether the file addresses the claim at all. Files
over 250 lines take two passes: a Choice over 250-line windows, then over the lines of the chosen
window. `found` is true when `exists` is at least 0.7. Measured on 26 cases over six files, one of
621 lines: 17 of 18 claims anchored to an accepted line, every present claim found, and every
absent claim called absent.

Input: `claim` and `file`, with optional `start` and `end` (1-based, inclusive), or a batch as
`queries`. Paths are relative to `repo` (default the working directory). A range over 90,000
characters is refused with exit 2, since Jev's state holds about 32k tokens: pass `start` and `end`.

```json
{"queries": [{"claim": "What happens when the skeptic agent returns null?", "file": "workflows/review-changes.js"}]}
```

```json
{"tool": "locate", "locations": [
  {"claim": "What happens when the skeptic agent returns null?", "file": "workflows/review-changes.js",
   "line": 196, "text": "  const cast = votes.filter(Boolean)", "probability": 0.51, "exists": 0.94,
   "found": true, "alternatives": [{"line": 199, "probability": 0.3}, {"line": 198, "probability": 0.1}]}]}
```
