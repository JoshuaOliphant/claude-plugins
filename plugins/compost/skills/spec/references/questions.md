# Questions

Two kinds of question list: the rounds that settle decisions during the interview, and the open
questions left after the self-review. Both go in the conversation, never in the spec itself.

## A round

Ask the frontier: the decisions whose prerequisites are all settled. A question whose answer
depends on another question in the same round belongs in a later round.

Put the shorthand hint first, then the questions. Leave two blank lines between questions and one
between the question, its context line, and its options.

```
> Answer with shorthand like `1a, 2b, 3c`, write freely, or say `ok` to take every recommendation.

---

**Q1. Should a partially shipped order be cancellable?**

_Context: `Order` today moves to `cancelled` only from `pending`; nothing handles split shipments._

a) No: once anything ships, the order can only be returned **(recommended: matches the current
   state model and the returns flow already covers it)**
b) Yes, for the unshipped lines only
c) Yes, the whole order, with a return raised for the shipped lines
d) Other (describe)


**Q2. Which roles can cancel?** (select all that apply)

_Context: the admin panel already lets support staff edit orders._

a) The customer who placed it **(recommended)**
b) Support staff **(recommended)**
c) Warehouse staff
d) Other (describe)


**Q3. What should the customer see in the confirmation email?**

_Context: no cancellation email exists; the order-confirmed email is the nearest template._

Recommended: the cancelled lines, the refund amount, and when the refund lands.
```

Rules for writing them:

- Every question carries a recommended answer, with the reason in a few words. The user should be
  able to accept it in one keystroke.
- Give lettered options when the choices are enumerable, and always end with "Other (describe)".
  Mark "(select all that apply)" when more than one can hold. Drop the options for a question that
  is better answered in prose, and give the recommendation as a sentence instead.
- The context line grounds the question in what you found: the code, a doc, an ADR, or the
  request. Keep it to one or two lines.
- Ask about decisions that change what gets built. Skip trivial choices, choices the code already
  makes, and questions about the spec template itself.
- Assume the user wants to continue existing patterns. Question a pattern only when the request
  clearly conflicts with it.
- Ask at the level of the class: bounded work asks about behavior; architectural work may also ask
  about structure and interfaces. Neither asks about file paths.

Accept answers in any shape: `1a, 2b, 3c`, `1a 2b 3c`, prose, or a mix. If the user answers a
question with a question, settle that exchange before the next round. Acknowledge the answers in a
line, show the refined prompt, then ask the next frontier.

## Open questions after the self-review

Same shape, but the context line quotes the spec line the question concerns, so the user can find
it and the answer lands in the right place.

```
**Q1. Does "refund lands" in the email mean the date issued or the date settled?**

_Spec: "AC-4 Then the email states when the refund lands"_

a) Date issued, which we know at cancellation time **(recommended)**
b) An estimated settlement date from the payment provider
c) Other (describe)
```

Fold each answer back into the spec and add its bullet to the Clarifications section. When the
self-review turns up nothing, say "No open questions" rather than inventing some.
