# Context map

This repo is a Claude Code plugin marketplace. Each plugin is a separate bounded context with its
own vocabulary; the marketplace itself (catalog, versions, shared artifacts, CI) is one more.

| Context | Glossary | What it is about |
|---|---|---|
| Marketplace | this file and `docs/adr/` | plugin registration, version sync, shared-artifact copies, CI |
| compost | `plugins/compost/CONTEXT.md` | the SDLC skills, the canon, the pile of sources, Jev tools, diff review, semantic lint |
| compound-knowledge | `plugins/compound-knowledge/CONTEXT.md` | captured solutions, retrieval, graduation |
| hexagonal-agents | `plugins/hexagonal-agents/CONTEXT.md` | agent-generated HTML UI behind ports and adapters |
| mochi-creator | `plugins/mochi-creator/CONTEXT.md` | flashcards, decks, and prompt quality |
| observability-harness | `plugins/observability-harness/CONTEXT.md` | local OTLP telemetry: traces, metrics, logs |
| understand | `plugins/understand/CONTEXT.md` | explain-back sessions and graded recall |

A glossary listed here but missing on disk has no settled terms yet; `compost:spec` creates it
when the first one settles.

## Relationships

- compost supersedes the retired autonomous-sdlc, stick-shift, and agent-skills plugins, and its
  `pile.toml` lists them as frozen sources. It absorbed review-diff and jev-lint.
- mochi-creator and understand share `prompt_design_principles.md`; compound-knowledge and
  understand share `config_loader.py`. The canonical copies live in `scripts/shared/`.
