# Refined prompt

The refined prompt is the original request plus what the interview settled. Show it in a
blockquote after every round so the user watches their answers shape the spec. The final version
becomes the Clarifications section of the parent issue.

Rules:

- Keep the original request exactly as written. Never reword, trim, or fix its typos.
- Add only bullets, using `*`, one per settled question-and-answer pair. Each bullet states the
  decision in one sentence, not the question.
- Put each bullet near the part of the request it concerns.
- Mark an assumption, a gap you filled without asking, with a leading `(assumed)` so the user can
  spot and overturn it.
- Mark a decision that a prototype settled with `(prototype: <branch>)`.
- No commentary, rationale, or headings inside the refined prompt. Reasons live in the spec body.

Example:

> Let customers cancel orders from their account page.
> * An order can be cancelled only while nothing in it has shipped; after that it goes through returns.
> * The customer who placed the order and support staff can cancel; warehouse staff cannot.
> * The cancellation email lists the cancelled lines, the refund amount, and the date the refund was issued.
> * (assumed) Cancelling an order that is already cancelled shows its current state and changes nothing.
