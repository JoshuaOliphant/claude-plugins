# Domain docs

How agents read this repo's domain documentation before working in it.

## Before exploring, read these

- `CONTEXT-MAP.md` at the repo root, which points at one `CONTEXT.md` per context. Read each one
  relevant to the topic.
- `docs/adr/`: the ADRs that touch the area about to change, and the context's own
  `plugins/<plugin>/docs/adr/`.

If a file doesn't exist, proceed without it. Don't flag the absence or create the file up front;
`compost:spec` and `compost:deepen` create them when a term or decision actually settles.

## Layout: multiple contexts

Each plugin is its own bounded context: a flashcard is a Mochi term, a spec is a compost term,
a span is an observability term, and none of them means anything in the others.

```
/
├── CONTEXT-MAP.md
├── docs/adr/                 marketplace-wide decisions (versioning, shared artifacts, CI)
└── plugins/<plugin>/
    ├── CONTEXT.md
    └── docs/adr/             decisions for this plugin
```

## Use the glossary's vocabulary

Name domain concepts (in issue titles, test names, hypotheses, refactor proposals) with the terms
`CONTEXT.md` defines, never the synonyms it lists under _Avoid_. A concept missing from the
glossary is either invented language to reconsider or a real gap for `compost:spec` to fill.

## Flag ADR conflicts

When work would contradict an ADR, say so explicitly instead of overriding it quietly:

> Contradicts ADR-0007 (event-sourced orders), but worth reopening because...
