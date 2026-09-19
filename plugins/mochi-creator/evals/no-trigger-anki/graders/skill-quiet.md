---
type: regex
target: trace
pattern: "\"skill\":\"mochi-creator:mochi-creator\""
match: not_contains
---
Spaced repetition is the shared idea, but the destination is not: this skill creates
cards in Mochi via the Mochi API. Firing here would build the user's deck in the wrong
application. The skill description must not claim Anki.
