# Domain docs

Template for `docs/agents/domain.md`. Keep the layout section that matches the choice and delete
the other.

````markdown
# Domain docs

How agents read this repo's domain documentation before working in it.

## Before exploring, read these

- `CONTEXT.md` at the repo root, or `CONTEXT-MAP.md` if it exists, which points at one
  `CONTEXT.md` per context. Read each one relevant to the topic.
- `docs/adr/`: the ADRs that touch the area about to change. In a multi-context repo, also the
  context's own `docs/adr/`.

If a file doesn't exist, proceed without it. Don't flag the absence or create the file up front;
`compost:spec` and `compost:deepen` create them when a term or decision actually settles.

## Layout: single context

```
/
├── CONTEXT.md
└── docs/adr/
```

## Layout: multiple contexts

```
/
├── CONTEXT-MAP.md
├── docs/adr/                 system-wide decisions
└── <package>/
    ├── CONTEXT.md
    └── docs/adr/             decisions for this context
```

## Use the glossary's vocabulary

Name domain concepts (in issue titles, test names, hypotheses, refactor proposals) with the terms
`CONTEXT.md` defines, never the synonyms it lists under _Avoid_. A concept missing from the
glossary is either invented language to reconsider or a real gap for `compost:spec` to fill.

## Flag ADR conflicts

When work would contradict an ADR, say so explicitly instead of overriding it quietly:

> Contradicts ADR-0007 (event-sourced orders), but worth reopening because...
````
