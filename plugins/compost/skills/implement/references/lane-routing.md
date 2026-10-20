# Lane routing

By default every lane worker inherits the orchestrator's model and effort, so a run on Opus runs
every lane on Opus, including the mechanical ones. This table sets an explicit model and effort per
lane instead. It is opt-in for one run, in one of two modes:

- **Tiered:** the user's ask for this run says to tier the lanes ("tiered lanes", "route lanes by
  model", "use the routing table"). Each lane spawn takes its tier's model and effort.
- **Control:** the ask is for the untiered run a tiered one is compared against ("untiered
  baseline", "A/B control"). Spawns leave both unset, as by default, and keep the record below.

The table becomes the default only once an A/B on a real implement run shows tiering cuts tokens
without drawing more review findings
([#138](https://github.com/JoshuaOliphant/claude-plugins/issues/138)).

## Starting the run

Post the mode on the parent issue before the first spawn ("Lane routing: tiered" or "Lane routing:
control"). A run resumed after `compost:pause` reads it there, since the original ask does not
carry over to a new session. In either mode, spawn every lane as a plain subagent, a lone lane
included, instead of building it in this session, so every lane has a worker and a token count and
the two runs split the work the same way.

## Table

Tier 1 is the cheapest. A lane takes the tier of its hardest issue; how many issues the lane holds
does not raise it.

| Tier | Issue | Model | Effort |
|---|---|---|---|
| 1 | Mechanical: doc text, copied files, labels, a config value; no new behavior and no test to design | haiku | low |
| 2 | Given/When/Then criteria and an Interfaces block, inside one module | sonnet | medium |
| 3 | Criteria that leave a design call, or a bug with an unknown cause | opus | high |
| 4 | Crosses bounded contexts, or changes an interface other lanes consume | opus | xhigh |

Pass the tier's values as `model` and `effort` on the lane's Agent spawn. When unsure between two
tiers, take the higher number: a stronger model costs tokens, a weaker one that lands wrong work
costs a review round and a respawn.

## What stays inherited

- **The orchestrator.** It keeps the session's model; the table routes only the lanes it spawns.
- **Review.** `/compost:review-changes` and its reviewers and skeptics keep their own settings.
  Review findings are what the A/B measures tiering against, so review must not differ between
  the two runs.

## Escalation

Fixing review findings resumes the same worker, on its tier. A lane moves to the next tier number,
respawned from its own branch with the brief and any open findings verbatim, when:

- it reports BLOCKED; that is the "more capable model" option in
  [handling the report](task-brief.md#handling-the-report). NEEDS_CONTEXT gets context, not a
  bigger model.
- a second review round on tier 1 or 2 still finds blockers.

Post each escalation as a ruling on the issue, naming the tier it left and the tier it moved to. A
tier 4 lane has no tier above it: take the other options in handling the report (more context, a
smaller issue, a ruling).

## Record for the A/B

When an issue passes review, add its lane's line to the step 7 comment: the tier it ran on (or
"inherited" in a control run), any escalation, the lane's total tokens, and the blocker and major
review findings it drew. The total sums every worker invocation for the lane as the harness
reported it: the first spawn, any respawn, and every resume for review fixes. The close-out recap's
Validation section lists those lines, so a tiered run and its control compare line by line.
