# compost glossary

**Upstream drift**: the changes a pile source has made since compost's pin for it. `compost:turn`
reads it with `pile.py status` and decides what to work in. In code: `pile.Drift`.
_Avoid_: drift (alone), upstream changes.

**Skill drift**: a skill's use not matching what it says. The agent skipped a step it states
(`deviated`), it left the agent working something out (`missing_guidance`), or the user corrected
work it covers (`corrected`). `compost:skill-drift` reviews it. In code: `skill_drift`.
_Avoid_: drift (alone), skill failure.

**Doc drift**: a doc saying something about the code that the code no longer does. The cost of
prose that restates code ([code is the source of truth](canon/code-is-the-source-of-truth.md)).
`compost:setup` flags it as Derivable lines; the Standards reviewer reports it.
_Avoid_: drift (alone), stale docs.

**Hit**: one Jev judgment that a turn showed skill drift of one kind, above that kind's threshold,
as the `skill-drift` mod writes it to `~/.claude/skill-drift/`.

**Pattern**: skill drift of one kind on one skill's current version, with hits from at least two
sessions. The unit `compost:skill-drift` acts on; a lone hit is not one.
