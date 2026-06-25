# evals/

Skill-trigger eval datasets — **not** a plugin, which is why they live here and
not under `plugins/`.

Each `*-eval.json` file is a list of `{ "query": ..., "should_trigger": bool }`
cases for one skill or workflow. They check that a skill's description fires on
the requests it should and stays quiet on the ones it shouldn't:

```json
[
  {"query": "help me create Mochi flashcards for the key concepts", "should_trigger": true},
  {"query": "write documentation for our API endpoints",          "should_trigger": false}
]
```

| File | Covers |
|---|---|
| `mochi-creator-eval.json` | mochi-creator card creation |
| `compound-capture-eval.json` / `compound-retrieve-eval.json` | compound-knowledge capture / retrieve |
| `hexagonal-agents-eval.json` | hexagonal-agents scaffolding |
| `bdd-spec-eval.json` / `bdd-generate-eval.json` / `tdd-workflow-eval.json` / `beads-workflow-eval.json` | autonomous-sdlc workflows |
| `verification-stack-eval.json` | observability-harness verification |

These are fixtures for evaluating skill-description quality; they are not shipped
inside any plugin.
