# compound-retrieve optimization workspace (experiment artifacts)

This directory holds autoloop experiment output (benchmarks, per-iteration runs, gradings, and a
`skill-snapshot/`) from optimizing the `compound-retrieve` skill. It is **reference material, not a
shipped skill**.

It previously lived under `plugins/compound-knowledge/skills/compound-retrieve-workspace/`, where
`skill-snapshot/SKILL.md` declared `name: compound-retrieve` — colliding with the real, shipped
skill at `plugins/compound-knowledge/skills/compound-retrieve/`. Two skills with the same name make
routing ambiguous (a caller can't predict which contract answers). Moving the workspace here, under
`ai_docs/` (which is explicitly not shipped in plugins), removes the collision while preserving the
benchmark history.

The canonical, shipped `compound-retrieve` skill is the grep + semantic-search implementation at
`plugins/compound-knowledge/skills/compound-retrieve/SKILL.md`.
