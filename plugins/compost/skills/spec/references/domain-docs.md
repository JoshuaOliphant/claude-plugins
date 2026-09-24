# Domain docs

The glossary and the decision record are sharpened while the spec is written, the moment a term or
a decision settles. `docs/agents/domain.md` (written by `compost:setup`) says which layout this
repo uses; without it, assume a single context.

## Layout

A single context, which is almost every repo:

```
/
├── CONTEXT.md
└── docs/adr/
    ├── 0001-event-sourced-orders.md
    └── 0002-postgres-for-write-model.md
```

Several contexts, marked by a `CONTEXT-MAP.md` at the root that points at each context's own
`CONTEXT.md` and `docs/adr/`, with system-wide ADRs in the root `docs/adr/`. When several contexts
exist, work out which one the topic belongs to, and ask only if it is genuinely unclear.

Create files lazily: `CONTEXT.md` with the first resolved term, `docs/adr/` with the first ADR.

## During the interview

- **Challenge against the glossary.** "The glossary defines cancellation as X, but you seem to
  mean Y. Which is it?"
- **Sharpen fuzzy language.** "You said account: do you mean the Customer or the User? Those are
  different things."
- **Test the model with scenarios.** Invent concrete cases that probe where one concept ends and
  the next begins, and make the user choose.
- **Cross-reference the code.** "The code cancels whole orders, but you just said partial
  cancellation is possible. Which is right?"

## CONTEXT.md

A glossary and nothing else: no implementation details, no decisions, no scratch notes.

```markdown
# Ordering

Receives customer orders and tracks them until they are fulfilled or cancelled.

## Language

**Order**:
A customer's request to buy one or more products, placed in a single checkout.
_Avoid_: purchase, transaction

**Cancellation**:
Ending an order before any of it ships, with a full refund.
_Avoid_: void, abort
```

- Be opinionated: when several words name one concept, pick one and list the rest under `_Avoid_`.
- One or two sentences per term, saying what it is, not what it does.
- Only terms specific to this project. General programming concepts (timeout, retry, cache) stay
  out even if the code uses them everywhere.
- Group terms under subheadings when clusters appear; a flat list is fine otherwise.

## ADRs

Write one only when all three hold:

1. **Hard to reverse:** changing your mind later costs something real.
2. **Surprising without context:** a future reader will wonder why it was done this way.
3. **A real trade-off:** there were genuine alternatives and one was picked for reasons.

Examples that qualify: the architectural shape, how contexts integrate, technology with lock-in,
ownership and scope boundaries, deliberate departures from the obvious path, constraints the code
can't show, and rejections that aren't obvious.

Number sequentially from the highest existing file: `docs/adr/0003-slug.md`.

```markdown
# Cancellation is refused once any line ships

Split shipments made partial cancellation a refund-accounting problem, and the returns flow
already handles shipped goods, so an order can be cancelled only while nothing in it has shipped.
```

One paragraph is enough. Add a Status line, Considered options, or Consequences only when they
carry something the paragraph doesn't.

If the spec contradicts an existing ADR, say so in the spec rather than overriding it quietly:
"Contradicts ADR-0007 (event-sourced orders), reopened because..."
