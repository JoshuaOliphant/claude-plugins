# meta/

Proof-of-concept of ADAS/AFlow-style meta-agent search over this repo's own workflow
artifacts. Design and rationale: `docs/meta-agent-search-design.md`. Like `evals/`,
this is repo-level tooling, not a plugin.

| Piece | Role |
|---|---|
| `program.md` | The meta-agent loop protocol (tier 1: skill trigger descriptions) |
| `auto/run.sh` | **Immutable** candidate runner: gates → fitness → `METRIC` lines |
| `archive/index.jsonl` | Ledger: one line per candidate with scores |
| `archive/candidate-NNN/` | One candidate: `genome/` (mutated files) + `meta.json` (idea, lineage, operator, scores, experience) |

Candidate-000 is the hand-crafted incumbent — its genome is the committed tree at the
recorded SHA, and its scores are the baseline every search run climbs from.

The fitness function is `evals/run_trigger_eval.py` (haiku judge via the `claude` CLI,
deterministic dev/holdout split, balanced accuracy + separate false-positive rate).
It is also useful standalone as a regression check when hand-editing a description:

```bash
python3 evals/run_trigger_eval.py --skill mochi-creator
python3 evals/run_trigger_eval.py --all
```

Launch a search run:

```bash
claude --dangerously-skip-permissions -p "Read meta/program.md and execute the loop protocol."
```

Winners are promoted to `plugins/` only via human-reviewed PR — the loop itself never
touches anything outside `meta/archive/`.
