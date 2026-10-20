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

## Starting and ending the run

Before the first spawn, post "Lane routing: tiered" or "Lane routing: control" on the parent issue,
so a run picked up in a new session, paused or not, keeps the mode. At close-out, post "Lane
routing: ended", so a later run on the same parent goes back to the default.

In either mode, spawn every lane as a plain subagent the way step 4 spawns parallel lanes
(`isolation: "worktree"`, in the background), a lone lane included, and never as a teammate. Every
lane then has a worker and a token count, and the two runs split the work the same way.

## Table

Tier 1 is the cheapest. A lane takes the tier of its hardest issue; how many issues it holds does
not raise it.

| Tier | Issue | Model | Effort |
|---|---|---|---|
| 1 | Mechanical: doc text, copied files, labels, a config value; no new behavior and no test to design | haiku | low |
| 2 | Criteria that settle every design call, including a bug whose cause is known | sonnet | medium |
| 3 | Criteria that leave a design call or are vague, or a bug with an unknown cause | opus | high |
| 4 | Crosses bounded contexts, or changes an interface other lanes consume | opus | xhigh |

Pass the tier's values as `model` and `effort` on the lane's Agent spawn. When unsure between two
tiers, take the higher number: a stronger model costs tokens, a weaker one that lands wrong work
costs a review round and a respawn.

## What the table does not change

- **The orchestrator.** It keeps the session's model; the table routes only the lanes it spawns.
- **Review.** `/compost:review-changes` and its reviewers and skeptics keep their own settings.
  Review findings are what the A/B measures tiering against, so review must not differ between
  the two runs.
- **Review fixes.** They resume the same worker, on the tier it was spawned with. A lane whose
  findings don't converge goes through step 6's round cap like any other, and its parked findings
  count against its tier.

## Escalation

A lane that reports BLOCKED respawns one tier up, as the "more capable model" option in
[handling the report](task-brief.md#handling-the-report). The respawn's brief names the blocked
worker's branch head in place of the feature SHA, so its commits carry over, and adds the BLOCKED
report verbatim. Post the escalation as a ruling naming both tiers. Tier 3 to 4 keeps the model and
raises only effort, so pair it with more context or a ruling, as that section requires. A tier 4
lane has no tier above it: take the other options there. NEEDS_CONTEXT gets context, not a higher
tier.

## Record for the A/B

When a lane finishes, whether its issues passed review or step 6 parked findings, post one line for
it on the parent issue: its issues, the tier it ran on (or "inherited" in a control run), any
escalation, its total tokens, and the blocker and major review findings it drew. The total sums
every worker invocation for the lane as the harness reported it: the first spawn, any respawn, and
every resume for review fixes. A lane whose worker was stopped by a pause or a lost session has no
reported count for that worker: mark its total "incomplete", and leave it out of the token
comparison.

The close-out recap's Validation section lists every lane's line, so a tiered run and its control
compare line by line.
