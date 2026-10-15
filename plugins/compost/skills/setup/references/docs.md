# Docs

Template for `docs/agents/docs.md`. List the core docs that exist in the repo, add any the repo
needs beyond the defaults (a runbook, a published docs site), and list what is not documentation.
`compost:prune` reads the two pattern blocks and passes them to `doc_refs.py` as `--core` and
`--exclude`. A pattern matches from the right, so `README.md` covers every README at any depth;
one ending in `/**` covers everything under that directory. A core doc is never excluded.

````markdown
# Docs

The code is the source of truth. Docs hold only what the code can't say, and live in the core
docs below. Anything else in markdown is a candidate for `compost:prune`.

## Core docs

| Doc | Holds |
|---|---|
| `README.md` | What the project is, why it exists, how to install and run it |
| `AGENTS.md` | How to work here: commands, conventions, gates |
| `CONTEXT.md` / `CONTEXT-MAP.md` | The domain vocabulary |
| `docs/adr/` | Why decisions were made; records, never edited to match the code |
| `docs/agents/` | How the compost skills work in this repo |
| `CHANGELOG.md` | What changed, release by release |

Core patterns beyond the defaults, one per line:

```
<e.g. docs/runbooks/*.md>
```

## Not documentation

Product, not prose about it: never pruned, never scanned. One pattern per line:

```
<e.g. skills/*/SKILL.md>
```

## Before writing something down

Put it in the first place that holds it: a name, a type or a check, a test, a comment where the
code lives (why, never what), and only then a core doc. Don't add a markdown file outside the core
docs; if one is truly needed, add its pattern above in the same change.

When docs and code disagree, the code is the likely truth: run `compost:prune`.
````
