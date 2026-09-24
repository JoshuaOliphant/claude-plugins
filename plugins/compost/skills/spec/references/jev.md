# Jev calls in spec

Four narrow judgments in spec (and the ADR offers in deepen and implement) go to Jev first: a
typed model that answers in a second or two for a fraction of a cent. Write the input JSON to a
temp file and run:

```sh
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py <tool> --input <file>
```

Exit 0 prints the judgment as JSON. Exit 2 means the input is malformed: fix it. Exit 3 means Jev
is unavailable (no key, or the API failed): make the call yourself with the manual procedure in the
step that sent you here. Jev never writes text for the spec; it grades what you hand it, and the
raw probabilities sit beside every decision so you can overrule it out loud.

## spec-class (step 2)

Input: the request word for word, and one or two sentences of what the code survey found, above
all whether a flow the request changes already exists.

```json
{"request": "pile.py says an upstream skill vanished when it was only renamed. Make it report the rename instead.",
 "survey": "pile.py compares pinned tree hashes per skill folder and reports added/changed/removed; tests/test_pile.py covers it."}
```

Output: `classifications[0].class` is the class to state. When Jev's top pick is below 0.7
probability, code has already taken the heavier of its top two (`heavier_if_unsure: true`), which is
the step's own "when torn, take the heavier" rule.

```json
{"class": "bounded", "jev_pick": "bounded", "confidence": 1.0, "heavier_if_unsure": false,
 "probabilities": {"bounded": 1.0, "architectural": 0.0, "spike": 0.0}}
```

## question-value (step 4)

Input: the refined prompt so far, and every candidate question for this round with its options.
Mark a question `"frontier": false` when it depends on one still open. `id` defaults to Q1, Q2...

```json
{"request": "Let customers and support staff cancel orders.",
 "questions": [
   {"question": "Should a partially shipped order be cancellable?", "options": ["No: once anything ships, only returns", "Yes, the unshipped lines only"]},
   {"question": "Should the confirmation say 'cancelled' or 'canceled'?", "options": ["cancelled", "canceled"]},
   {"question": "Is a cancellation email sent?", "options": ["Yes", "No"], "frontier": false}]}
```

Output: `round` lists the ids to ask, most valuable first, at most five. Each question carries its
`value` (0 = the answer changes nothing built, 1 = a detail, 2 = which behaviors get built, 3 =
architecture or scope) and a `decision`: `ask`, `assume` (below 1.7: take your recommended answer
and list it as an assumption), `later` (not on the frontier), or `next-round` (valuable, but the
round is full).

## ac-quality (step 9)

Input: every AC-N, whole, as `{"id", "text"}`.

```json
{"criteria": [
  {"id": "AC-1", "text": "Given an order in `pending`, When payment is confirmed, Then the order moves to `confirmed`."},
  {"id": "AC-2", "text": "Given a user submitting the payment form, When the payment provider times out, Then the error is handled gracefully."}]}
```

Output: per criterion, three scores from 0 to 1 (`observable_then`, `specific_given`,
`single_behavior`), `combined` (the weakest of the three, since a sharp Given does not make an
untestable Then testable), `weakest`, and `rewrite` when the weakest is below 0.63. Rewrite those,
fixing the named dimension first.

```json
{"id": "AC-2", "observable_then": 0.005, "specific_given": 0.545, "single_behavior": 0.995,
 "combined": 0.005, "weakest": "observable_then", "rewrite": true}
```

## adr-worthy (spec step 5, deepen step 7, implement step 9)

Input: the ruling as you would post it. A string is accepted as `what` alone, but the why, the
alternatives, and the cost if wrong are what the judgment rests on.

```json
{"ruling": {"what": "Track work in GitHub issues, never beads.",
            "why": "Issues are where people look and they link to PRs; beads is a second tracker only Claude reads.",
            "alternatives": "beads; markdown plan files",
            "cost_if_wrong": "Rewriting every skill's tracker steps and migrating open work."}}
```

Output: the three tests as probabilities and `offer_adr`, true only when all three clear their
thresholds (hard to reverse 0.65, surprising 0.5, real trade-off 0.6). Offer the ADR only then.

```json
{"what": "Track work in GitHub issues, never beads.", "hard_to_reverse": 0.91, "surprising": 0.58,
 "trade_off": 0.84, "offer_adr": true}
```

Several at once: `requests`, `criteria`, and `rulings` take lists, judged concurrently.
