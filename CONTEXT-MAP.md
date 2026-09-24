# Context map

This repo is a Claude Code plugin marketplace. Each plugin is a separate bounded context with its
own vocabulary; the marketplace itself (catalog, versions, shared artifacts, CI) is one more.

| Context | Glossary | What it is about |
|---|---|---|
| Marketplace | this file and `docs/adr/` | plugin registration, version sync, shared-artifact copies, CI |
| agent-skills | `plugins/agent-skills/CONTEXT.md` | small workflow skills: plan arbitration, recaps, visual plans |
| autoloop | `plugins/autoloop/CONTEXT.md` | generated optimization loops and their experiments |
| autonomous-sdlc | `plugins/autonomous-sdlc/CONTEXT.md` | deprecated: the on-disk SDLC state machine |
| compost | `plugins/compost/CONTEXT.md` | the SDLC skills, the canon, the pile of sources, Jev tools |
| compound-knowledge | `plugins/compound-knowledge/CONTEXT.md` | captured solutions, retrieval, graduation |
| hexagonal-agents | `plugins/hexagonal-agents/CONTEXT.md` | agent-generated HTML UI behind ports and adapters |
| jev-lint | `plugins/jev-lint/CONTEXT.md` | semantic lint rules judged by Jev |
| mochi-creator | `plugins/mochi-creator/CONTEXT.md` | flashcards, decks, and prompt quality |
| observability-harness | `plugins/observability-harness/CONTEXT.md` | local OTLP telemetry: traces, metrics, logs |
| review-diff | `plugins/review-diff/CONTEXT.md` | browser diff review fed back to the agent |
| stick-shift | `plugins/stick-shift/CONTEXT.md` | deprecated: the hand-driven SDLC session |
| understand | `plugins/understand/CONTEXT.md` | explain-back sessions and graded recall |

A glossary listed here but missing on disk has no settled terms yet; `compost:spec` creates it
when the first one settles.

## Relationships

- compost supersedes autonomous-sdlc and stick-shift, and its `pile.toml` lists them as frozen
  sources.
- mochi-creator and understand share `prompt_design_principles.md`; compound-knowledge and
  understand share `config_loader.py`. The canonical copies live in `scripts/shared/`.
- autonomous-sdlc composes observability-harness as a soft dependency.
