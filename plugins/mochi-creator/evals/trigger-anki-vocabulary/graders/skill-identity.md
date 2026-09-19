---
type: regex
target: trace
pattern: "\"skill\":\"mochi-creator:mochi-creator\""
match: contains
---
"Anki-style" and "so I remember" are both listed triggers in the skill description, so
mochi-creator specifically must load even though the user never said "Mochi".
