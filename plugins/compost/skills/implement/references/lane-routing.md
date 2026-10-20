# Lane routing

By default every lane worker inherits the orchestrator's model and effort, so a run on Opus runs
every lane on Opus, including the mechanical ones. This table sets an explicit model and effort per
lane instead. It is opt-in for one run: use it only when the user's ask for this run says to tier
the lanes ("tiered lanes", "route lanes by model", "use the routing table"). A run without that ask
leaves both unset on every spawn. An ask for the untiered control run of the A/B ("untiered
baseline", "A/B control") also leaves both unset, and keeps the record below.

The table becomes the default only once an A/B on a real implement run shows tiering cuts tokens
without drawing more review findings
([#138](https://github.com/JoshuaOliphant/claude-plugins/issues/138)).

## Table

Take the lowest row that fits every issue in the lane: a lane is as hard as its hardest issue.

| Lane | Model | Effort |
|---|---|---|
| Mechanical: doc text, copied files, labels, a config value; no new behavior and no test to design | haiku | low |
| One issue with Given/When/Then criteria and an Interfaces block, inside one module | sonnet | medium |
| Several issues in order, an issue whose criteria leave a design call, or a bug with an unknown cause | opus | high |
| An issue that crosses bounded contexts or changes an interface other lanes consume | opus | xhigh |

Pass the row's values as `model` and `effort` on the lane's Agent spawn. When unsure between two
rows, take the higher one: a stronger model costs tokens, a weaker one that lands wrong work costs
a review round and a respawn.

## What stays inherited

- **The orchestrator.** It keeps the session's model; the table routes only the lanes it spawns.
- **Review.** `/compost:review-changes` and its reviewers and skeptics keep their own settings.
  Review findings are what the A/B measures tiering against, so review must not differ between
  the two runs.
- **A resumed worker.** Fixing review findings resumes the same worker, on the model it was
  spawned with.

## Escalation

A lane that reports BLOCKED moves one row up for its respawn; that is the "more capable model"
option in [handling the report](task-brief.md#handling-the-report). Post it as a ruling on the
issue, naming the row it left and the row it moved to. NEEDS_CONTEXT gets context, not a bigger
model.

## Record for the A/B

In the close-out recap's Validation section, list each lane once: its issues, the row it ran on,
any escalation, the total tokens the harness reported for the worker, and the blocker and major
review findings it drew. The control run records the same lines with "inherited" as its row, so
the two runs compare line by line.
