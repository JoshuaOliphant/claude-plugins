# Code is the source of truth

Prose in the repo that explains what the code does is a second source of truth, and nothing keeps
it honest. Make the code say what it does, and keep only the docs code cannot hold: why a decision
was made, what the domain's words mean, and a thin map of where things live.

Taken from Matt Pocock's "Delete (most of) your docs".

## Why it works

A doc that restates code is not executable and no test runs against it. When the code changes,
nothing fails, so the doc goes stale without anyone noticing. Now the repo has two answers to
the same question, and a reader cannot tell which one is current without reading the code anyway.
The doc saved nobody the read; it only added a chance to believe the wrong answer.

So put the burden on the code. Names taken from the glossary, modules with small interfaces over
deep implementations, interfaces kept apart from implementations, and tests that name the
behavior they prove all explain the code, and none of them can drift from it.

## Why it matters for an agent

An agent reads the instructions file at the start of every session and trusts it before it has
opened a single source file. A stale line in `AGENTS.md` costs tokens in every session and points
every one of them the wrong way. A wrong count, a missing module, a renamed command: each one sends
the agent off to look for something that isn't there, or makes it build around a structure that
no longer exists. An explainer that duplicates the code also gets read in place of the code, so
the agent works from the summary instead of the thing.

## What stays

- **Decisions**, in `docs/adr/`: what was chosen, what else was considered, and why. The code
  shows only the winner.
- **The glossary**, in `CONTEXT.md` ([ubiquitous language](ubiquitous-language.md)): what the
  domain's words mean. The code uses them but cannot define them.
- **Navigation**: a short map of entry points, commands, and where things live. Keep a line only
  if it saves the agent a search and is cheap to check against the tree.
- **Instructions**: rules the code cannot enforce on its own, such as conventions, gates, and the
  things never to do.
- **Docs for people who don't read the code**: install steps, user guides, API references for
  callers. They describe the code's contract, not its insides.

## In practice

- Before writing prose that explains code, try to make the code say it: a better name, an
  extracted function, a type, a test whose name states the behavior.
- When a doc that describes the code disagrees with it, the doc is wrong. Fix it or delete it.
  When an ADR or an acceptance criterion disagrees with the code, that is different: a recorded
  decision was broken, so flag it instead of quietly editing either side.
- Derive lists instead of maintaining them. A count, an inventory, or a version that a script can
  produce or check belongs in that script, not in prose a person has to remember to update.
- A change that alters behavior a doc describes updates or deletes that doc in the same commit.
- Prune what is already there. A doc section that restates the code gets deleted, not refreshed:
  refreshing it only resets the clock on the next drift ([subtract before you add](subtract-before-you-add.md)).
