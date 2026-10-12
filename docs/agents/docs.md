# Docs

The code is the source of truth. Docs hold only what the code can't say, and live in the core
docs below. Anything else in markdown is a candidate for `compost:prune`.

## Core docs

| Doc | Holds |
|---|---|
| `README.md` | What the marketplace and each plugin are, and how to install them |
| `AGENTS.md` | How to work here: layout, versioning, commands, conventions |
| `CONTEXT-MAP.md` / `plugins/*/CONTEXT.md` | Each bounded context and its vocabulary |
| `docs/adr/` | Why decisions were made; records, never edited to match the code |
| `docs/agents/` | How the compost skills work in this repo |
| `CHANGELOG.md` | What changed, release by release |

Core patterns beyond the defaults, one per line:

```
```

## Not documentation

Product, not prose about it: never pruned, never scanned. Plugin READMEs and glossaries stay
core, since a core doc is never excluded. One pattern per line:

```
plugins/**
scripts/shared/**
knowledge/**
ai_docs/experiments/**
ai_docs/agent_sdk_overview.md
ai_docs/agent_sdk_python.md
ai_docs/skills.md
ai_docs/subagents.md
```

`plugins/**` is shipped skill, agent, command, and reference text; `scripts/shared/**` is the
canonical source of shipped copies; `knowledge/**` is compound-knowledge's own records;
`ai_docs/experiments/**` holds eval outputs; the four `ai_docs/*.md` files are vendored copies of
Anthropic's docs.

## Before writing something down

Put it in the first place that holds it: a name, a type or a check, a test, a comment where the
code lives (why, never what), and only then a core doc. Don't add a markdown file outside the core
docs; if one is truly needed, add its pattern above in the same change. Plans and specs go in the
issue tracker, not in `docs/`.

When docs and code disagree, the code is the likely truth: run `compost:prune`.
