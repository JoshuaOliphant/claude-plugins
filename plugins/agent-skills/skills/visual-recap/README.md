# /visual-recap

Turn a branch, commit, or PR diff into an interactive visual recap with
annotated diffs, diagrams, API/schema summaries, file maps, UI state summaries,
and focused review notes.

`/visual-recap` is the reverse of `/visual-plan`: instead of planning a future
change, it summarizes a diff, branch, commit, or PR after the work exists. The
goal is to help reviewers understand the shape of a change before they dive into
raw line-by-line diffs.

It solves for diffs that hide the shape of the change. Reviewers can understand
contracts, architecture moves, schema changes, and UI impact before diving into
raw line-by-line review.

The recap is a human-optimized interactive document with custom components for
the things raw diffs are bad at explaining: annotated diffs, diagrams, visual
schema maps, OpenAPI-style API diffs, file maps, UI state summaries, and focused
review notes.

<picture>
  <img alt="Visual recap review surface animation" src="../../media/visual-recap.gif">
</picture>

Produces a self-contained `recap.html` from a branch/PR/commit diff, opened
locally — no account, no server, no external services.

## What It Does

- Reads the actual changed files and diff.
- Produces a self-contained interactive recap with file maps, diagrams, visual
  schema maps, API diffs, annotated diffs, UI state summaries, and focused key changes.
- Keeps recaps substantial enough for real review without dumping every line.
- Makes large changes consumable before a reviewer opens raw diff view.

## When To Use It

Use it for PRs or work units that are large, multi-file, UI-heavy, or touch
schema, API contracts, permissions, architecture, or review-critical behavior.

Skip it for tiny, obvious diffs that review faster directly in source control.

## What Reviewers Get

Reviewers get the shape of the change first: what moved, which contracts
changed, what data or API surfaces were touched, how UI states differ, and where
the risky lines are. Then they can review the raw diff with a map in their head.

## Install

Install via the Claude Code plugin marketplace (see the root README). This skill
shares its reference docs with `visual-plan` (it reads
`../visual-plan/references/`), so if you copy folders by hand, copy both
`skills/visual-plan/` and `skills/visual-recap/` together.
