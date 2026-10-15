# Homes: where a keeper goes

Each rung is harder to let drift than the one below it. A name is read every time the code is; a
type is checked on every build; a test fails when the behaviour changes; a comment sits next to the
code it explains, so whoever changes that code sees it. A separate doc has none of these, which is
why it drifts. Stop at the first rung that holds the claim.

## 1. A name

The doc explains what something is or does because its name doesn't.

- "`process()` validates the order and reserves stock" becomes `reserve_stock_for(order)`.
- "`flag` is true when the user opted out" becomes `opted_out`.
- "Files in `util/` handle billing retries" becomes a `billing/retry` module.

Use the terms `CONTEXT.md` defines. A rename touches every caller in the same change; one that
crosses a public interface or a deploy boundary is filed as an issue instead.

## 2. A type or a check

The doc states a rule the code could enforce.

- "`timeout` is in milliseconds" becomes a `Milliseconds` type, or a `timeout_ms` parameter.
- "Never call `close()` before `flush()`" becomes a `close()` that flushes, or a state the type
  system tracks ([type-system discipline](../../../canon/type-system-discipline.md)).
- "`region` must be one of us, eu, ap" becomes an enum parsed at the edge
  ([boundary discipline](../../../canon/boundary-discipline.md)).
- "Set `API_KEY` before starting" becomes a startup check that names the variable when it is
  missing.

## 3. A test

The doc describes behaviour with an example. The example becomes a test, named for the behaviour
in the domain's terms, in the suite's existing layout (`docs/agents/testing.md`).

- "Cancelling a shipped order issues a refund, not a void" becomes
  `test_cancelling_a_shipped_order_refunds_it`.
- A worked example in a README becomes a doctest or an example test the suite runs.

## 4. A comment where the code lives

What survives the first three rungs is usually why: the reason for an odd choice, the alternative
that failed, the outside constraint. Put it next to the code it explains, in a sentence or two.

```python
# Stripe rejects idempotency keys over 255 characters, so the order id is hashed, not used raw.
```

Never what the code does; the code says that. A comment that restates the line below it is a doc
that will drift, moved closer.

## 5. A core doc

Some keepers are about the whole project, not a line of it.

| Keeper | Core doc |
|---|---|
| A domain term, with the words to avoid | `CONTEXT.md` |
| A decision that is hard to reverse, surprising, and a real trade-off | an ADR in `docs/adr/` |
| A command, a convention, a gate, how to work here | `AGENTS.md` |
| What the project is, why it exists, how to install and run it | `README.md` |

Add a line to the right section; don't append a new section that duplicates one already there.

## Not a home

- A new doc file. If a keeper truly needs one (a runbook an on-call engineer reads at 3am), add it
  to the core list in `docs/agents/docs.md` in the same change, so the next prune checks it rather
  than deleting it.
- A docstring that restates the signature. It is a comment that says what.
