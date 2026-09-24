# Issue tracker: local markdown

Specs, slices, and maps for this repo live as markdown files under `.scratch/`.

## Layout

- One directory per feature: `.scratch/<feature-slug>/`.
- The spec (the parent issue) is `.scratch/<feature-slug>/spec.md`.
- Each slice is one file, `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in
  dependency order. Never one combined file.
- A `Status:` line under each file's title holds its label from the table below, or `closed`.
- Blocking is a `Blocked by: 01, 03` line under the status, using file numbers.
- Comments append under a `## Comments` heading at the bottom of the file, newest last.

## When a skill says

- **"Post the parent issue":** write `spec.md` in a fresh feature directory.
- **"Create an issue":** write the next numbered file in `issues/`.
- **"Read the issue":** read the file at the referenced path or number.
- **"Comment":** append under `## Comments`.
- **"Close":** set `Status: closed` and append the closing note as a comment.

## Labels

| Role | Status value | Meaning |
|---|---|---|
| Ready for agent | `ready-for-agent` | A slice an agent can build without a person |
| Ready for human | `ready-for-human` | A slice that needs a person (credentials, a manual step) |

Specs, maps, and decisions are told apart by their file names and locations below, so they need no
label.

## Records

- **Rulings** (a decision made without stopping: what, why, cost if wrong) are comments in the
  slice's file.
- **Progress** is the checklist of slices in `spec.md` plus the git log. Commits reference the
  slice's file number.

## Map operations

Used by `compost:slice` for map issues.

- **Map:** `.scratch/<effort>/map.md`.
- **Decision:** `.scratch/<effort>/decisions/<NN>-<slug>.md` with a `Kind:` line and a `Status:`
  line of `open`, `claimed`, or `resolved`.
- **Frontier:** decisions that are `open` and whose `Blocked by` files are all `resolved`; lowest
  number wins.
- **Claim:** set `Status: claimed` and save before any other work.
- **Resolve:** append the answer under `## Answer`, set `Status: resolved`, then add the gist and
  link to the map's Decisions so far.
