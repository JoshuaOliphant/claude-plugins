---
type: regex
target: trace
pattern: "\"skill\":\"mochi-creator:mochi-creator\""
match: contains
---
The trace must show mochi-creator itself being loaded — not merely that some skill
fired. The Skill tool records the plugin-qualified id in its input, and the `"skill":"`
anchor keeps this off the skill listing in the system prompt, where the same id appears
as bare prose.
