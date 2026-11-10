# Codify the orchestration

When the shape of a multi-agent job is fixed, put the shape in a script and keep the judgment in
the conversation. Claude Code's dynamic workflows are the tool: a JavaScript script that spawns
subagents, holds their results in variables, and runs in the background while the session stays
free. Read the [official documentation](https://code.claude.com/docs/en/workflows) for the API,
limits, and approval rules, and load the bundled `workflow-authoring` skill before writing one.
This essay covers only when one is worth it, and what compost does about that.

## The test

A conversation decides what happens next turn by turn, and every intermediate result sits in its
context. A workflow decides in code, and intermediate results sit in variables. Codify when most of
these hold:

- The same step runs across a list of items (docs, files, findings, sources) and the list can be
  produced first.
- The topology is known before the run: fan out, verify, merge. You could draw it.
- Each agent's result fits a schema, so the script can branch on it without reading prose.
- Independent agents should check each other, and the check must not depend on the author's
  context.
- The run will repeat, or must survive an interruption, or should run unattended.

Keep it a skill, or work it in the conversation, when any of these hold:

- The run needs a person mid-way: an interview, an approval, a ruling. A workflow cannot ask.
- The evidence has to be seen by the main session itself. `compost:verify` must not hand its
  proof to an agent.
- The work is one agent's craft with the full context: building, diagnosing, designing.
- The list is short. Three to eight agents rarely beat a few subagents in one message, and a
  workflow costs more tokens.

## What compost has done with it

`/compost:review-changes` is the worked example (`workflows/review-changes.js`). The script owns
the fixed part: scope the diff, run the Standards and Spec reviewers, give each serious finding to
a skeptic told to refute it, and return survivors, refutations, and unjudged findings side by
side. The `compost:review` skill owns the rest: deciding which survivors hold, fixing them, and
recording the outcome. The split is the pattern: a script for topology, a skill for judgment.

A negative example keeps the test honest. Checking eight docs with `compost:prune`'s doc-check
brief, one agent per doc in a workflow found the same number of planted drifts as three plain
subagents, at about twice the tokens. Each arm missed a different drift, so what would have
helped is a second independent checker per doc, not the script. That shape is worth codifying
once the list is long enough that the redundancy is the point.

## What Claude does with this

While working in compost, notice when a job fits the test, and say so once, with the shape in a
sentence: "this is a fan-out over 40 modules with a skeptic per finding; I can codify it as a
workflow." Then ask. A workflow you write yourself needs the user's explicit ask; the plugin's own
`/compost:review-changes` needs none. Do not start one on your own, and do not raise it for a job
that fails the test.

When the user says yes, scout inline first to build the list, run the workflow on a small slice,
and read its result before the next phase. Pass a timestamp in through `args`, since the script
cannot read the clock. Write the script as a pure function of its inputs so a resume replays it.

## Traps

- Workflow agents use the session's working directory when they run. Do not `cd` into another repo
  while one is running.
- The Workflow tool is unavailable inside a subagent, so a skill that runs one needs a by-hand
  fallback, as `compost:review` has.
- Isolated worktrees per agent are costly. Use them only when agents write files in parallel.
- Test a workflow like code: run it against stub `agent`, `parallel`, and `pipeline` functions
  (see `tests/workflow.test.mjs`) so its verdict logic is pinned.
