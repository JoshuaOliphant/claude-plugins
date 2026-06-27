# /visual-plan

Turn ordinary implementation plans into rich interactive visual review surfaces.

`/visual-plan` turns the plan an agent would normally write in chat into a
human-optimized interactive document. Instead of a long wall of prose, reviewers get
custom components built for understanding: architecture diagrams, wireframes,
interactive prototypes, file maps, annotated code, OpenAPI-style API specs,
visual schema maps, open questions, and comments.

It solves for plans that are too important to bury in chat. The output is
scannable, commentable, and intuitive enough for a human to approve before code
changes start.

<picture>
  <img alt="Visual plan review surface" src="../../media/visual-plan.png">
</picture>

Produces a self-contained `plan.html` you open locally — no account, no server,
no external services.

## What It Does

- Grounds plans in real repo files, schemas, actions, and symbols.
- Chooses the right visual surface: document-only, wireframe canvas, prototype,
  design direction, or visual intake.
- Uses custom components for diagrams, UI flows, API specs, schema maps,
  diffs, code annotations, and reviewer questions.
- Produces a self-contained interactive review document instead of inline chat Markdown.
- Keeps the plan as the approval gate before source edits begin.

## When To Use It

Use it for multi-file, ambiguous, risky, architecture-heavy, data-heavy, or
UI-heavy work where the wrong direction would be expensive. It is also useful
when a pasted text plan needs a richer review surface.

Skip it for trivial fixes, single-line changes, or anything whose diff is easier
to review than a plan.

## What Reviewers Get

Reviewers get a plan that is built for scanning. Decisions, files,
diagrams, contracts, UI states, prototype behavior, schema shape, API boundaries,
and unresolved questions live in one consumable place.

The point is not just prettier planning. It is a better medium for human review:
visual where visuals help, structured where structure helps, and grounded in the
actual codebase.

## Install

Install via the Claude Code plugin marketplace (see the root README), or copy
`skills/visual-plan/` into your agent's skills directory.
