# compost glossary

**Upstream drift**: the changes a pile source has made since compost's pin for it. `compost:turn`
reads it with `pile.py status` and decides what to work in. In code: `pile.Drift`.
_Avoid_: drift (alone), upstream changes.

**Skill drift**: a skill's use not matching what it says. The agent skipped a step it states
(`deviated`), it left the agent working something out (`missing_guidance`), or the user corrected
work it covers (`corrected`). `compost:skill-drift` reviews it. In code: `skill_drift`.
_Avoid_: drift (alone), skill failure.

**Doc drift**: a doc saying something the code no longer does. A doc that restates the code has
none yet, and will. `compost:prune` finds it, takes the code as the likely truth, and moves what
is worth keeping into the code. The Standards reviewer reports drift a diff introduces. In code:
`doc_refs`.
_Avoid_: drift (alone), stale docs, doc rot.

**Mechanism**: a mod or hook judged by what it enforces: the event it fires on and the compost
rule it makes happen rather than states. "Mod or hook" is the kind of an upstream item;
"mechanism" is how `compost:turn` judges one, and what a `feeds` target in `pile.toml` names on
compost's side: `hooks` for its hooks as a whole, `hooks/<mod>` for one mod its hooks module
registers. In code: `pile.is_mechanism`.
_Avoid_: guard, enforcement hook.

**Semantic invariant**: a law central to what a context means, which holds whatever policy or
failure comes along, stated with the side to err on ("never charge twice; on doubt, don't
charge"). Listed under Semantic invariants in the context's `CONTEXT.md`, set by `compost:spec`,
checked by the reviewer.
_Avoid_: business rule, policy (those change; an invariant doesn't), constraint.

**Core docs**: the few docs that hold what code can't say: `README.md`, `AGENTS.md`, `CONTEXT.md`,
`docs/adr/`, plus what a repo lists in `docs/agents/docs.md`. Checked by `compost:prune`, fixed in
place, never deleted.

**Telemetry**: the traces, logs, and metrics a repo's running code emits, read through the stack
`docs/agents/observability.md` records. `compost:diagnose` and `compost:verify` query it;
`compost:build` adds to it at new boundaries.
_Avoid_: observability data, monitoring.

**Hit**: one Jev judgment that a turn showed skill drift of one kind, above that kind's threshold,
as the `skill-drift` mod writes it to `~/.claude/skill-drift/`.

**Pattern**: skill drift of one kind on one skill's current version, with hits from at least two
sessions. The unit `compost:skill-drift` acts on; a lone hit is not one.
