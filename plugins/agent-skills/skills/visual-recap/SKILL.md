---
name: visual-recap
description: >-
  Use when turning a PR/branch/commit diff into a self-contained interactive HTML
  recap (annotated diffs, file maps, API/schema summaries, wireframes) saved
  locally and opened in the browser.
---

# Visual Recap

`/visual-recap` builds a self-contained `recap.html` **from** a diff, not toward
one. It is the reverse of forward planning: instead of describing the change you
are about to make, you describe the change that was just made, at a higher
altitude than line-by-line review — same structured thinking, in reverse. Schema,
API, file, and architecture changes become the same data-model, API-endpoint,
file-tree, and diagram sections a forward plan would use, only now they summarize
work that exists. A reviewer scans the shape of the change before spending
attention on the literal lines. The deliverable is ONE self-contained HTML file
`plans/<slug>/recap.html` — everything inline, no external network references,
opened locally.

## When To Use

Build a recap when a PR or commit is large, multi-file, or touches schema, API
contracts, or architecture, and a reviewer would benefit from seeing the change
mapped to structured sections before reading the raw diff. An agent can generate
one on request ("recap this PR", "show me what this branch changed"). Skip it for
small, single-file, or obvious diffs — a recap is review overhead, and a tiny
change reviews faster as plain diff.

## Recap The Whole Work Unit

When `/visual-recap` is invoked in a chat thread after work has already happened,
the default scope is the whole current work unit/thread, not only the most recent
user message, tool action, or follow-up fix. Gather the thread-owned changes
across the conversation: original implementation work, later bug fixes, UI
follow-ups, tests, changesets, skill/instruction updates, and any generated
artifacts.

Use the current diff plus conversation context to separate thread-owned changes
from unrelated dirty work that existed before the thread. Exclude unrelated
pre-existing edits. If the scope is genuinely ambiguous and cannot be inferred,
state the assumption or ask a concise question before producing the recap.

When updating an existing recap after feedback, revise the recap so it still
covers the whole thread/work unit plus the new correction. Do not replace a broad
recap with a narrow recap of only the latest feedback unless the user explicitly
asks for that narrower scope.

## Keep The Recap Body Lean

Do not add boilerplate intro, disclaimer, provenance, or summary prose to the
recap body. In particular, do not add a prose section just to say the recap is an
aid, that the reviewer should still review the diff, how many files changed, or
which ref/working tree generated the recap. The recap title, brief, and file-tree
(which carries the per-file change stats) already carry that context.

Only add prose when it tells the reviewer something specific about the change that
the structured sections do not: the objective, a real compatibility risk, an
important decision visible in the diff, or a grounded review note.

## Recaps Must Be Substantial

Lean is not the same as thin. A recap is not a single wireframe plus one
sentence — that under-serves the reviewer as much as boilerplate prose over-serves
them. Alongside the visual/structural headline (wireframes, data-model,
API-endpoint, diagram), a substantial recap also carries the implementation
evidence:

- A short surface/state inventory before authoring: list the changed routes,
  components, popovers/dialogs, role/access states, empty/error states, and
  shared abstractions visible in the diff. The final recap must either represent
  each meaningful item with a section or intentionally omit it because it is tiny,
  redundant, or not user-visible.
- A file-tree of the changed files with each entry's change flag, so the reviewer
  sees the footprint of the work at a glance.
- The split diff of the KEY changed files, grouped under a `## Key changes`
  heading in a single horizontal tabs control (one file per tab), with a one-line
  summary and a few annotations on each — so the reviewer can drop from the
  high-altitude shape straight into the load-bearing code. Use horizontal file
  tabs, not a vertical side rail, so the selected file has enough width for the
  side-by-side diff.

Skip the diff appendix only for a genuinely tiny change that reviews faster as
plain diff (see "When To Use"); for any change worth recapping, the file-tree and
key-change diffs belong in the recap.

## Canonical Shape And Budgets

A strong recap follows one skeleton, top to bottom:

1. UI-impact headline — wireframes first, when the diff changed rendered UI.
2. Short outcome narrative: what changed and why, 1-3 paragraphs.
3. data-model / API-endpoint sections for schema and contract changes.
4. file-tree of the changed files with change flags.
5. `## Key changes` — one horizontal tabs control of split diffs / annotated code.

Budgets that keep the recap reviewable:

- 3-8 key-change tabs. Fewer than 3 on a large change under-serves the
  reviewer; more than 8 stops being a summary.
- Keep each diff/annotated-code excerpt focused — prefer under ~150 lines per
  tab; summarize or link the rest of a long file instead of dumping it.
- Title at most ~70 characters; brief 1-3 sentences.

**GOOD.** A 25-file auth change: Before/After wireframes of the login surface,
a two-paragraph narrative, a diff-aware data-model of the sessions table, an
API-endpoint for the new refresh route, a file-tree with change flags, and
`## Key changes` with five focused tabs, each with a one-line summary and a
few annotations on the load-bearing hunks.

**BAD.** One giant unsegmented diff dump with no summaries or annotations; or a
sparse three-section recap of a 40-file change (one wireframe, one sentence, one
file list) that forces the reviewer back into the raw diff anyway.

## UI Impact Needs Wireframes

When the diff changes rendered UI, layout, density, visual state, interaction
affordances, navigation, controls, menus, dialogs, or design tokens, the recap
MUST include one or more wireframes. Prose and file diffs are not a substitute
for showing what changed visually.

Before choosing wireframes, make a UI coverage pass from the diff:

- Identify the entry surface where the change appears, such as a page header,
  list row, toolbar, route shell, or menu trigger.
- Identify the interaction surface that opens or changes, such as a popover,
  dialog, tab, sheet, dropdown, inline editor, or toast.
- Identify the resulting destination or persistent state, such as a public page,
  read-only view, empty state, error state, loading state, permission-denied
  state, or saved/shared state.
- Identify access or role variants when permissions change. Owner/admin/editor
  versus viewer/non-manager differences are visual behavior and need a compact
  matrix, paired wireframes, or clearly labeled state sequence.

For UI-heavy PRs, a single before/after of the entry surface is not enough.
Show the changed entry point, the main changed interaction surface, and the
resulting/destination state. Add more states when the diff adds tabs, role-based
controls, public/private visibility, invite/manage flows, destructive controls,
or empty/error branches.

Choose the smallest visual surface that makes the review clear:

- Use a `Before` / `After` wireframe pair when the reviewer benefits from direct
  comparison, such as a removed or added control, a changed state, layout
  density, ordering, navigation, or a visible component replacement.
  `../visual-plan/references/wireframe.md` owns how to lay that pair out (columns
  vs. vertical stack by geometry).
- Use an after-only wireframe when the change is purely additive or the "before"
  state would only show absence without adding review value.
- Use more than two wireframes when the UI change is flow-dependent, responsive,
  or stateful; show the meaningful states in order instead of forcing a single
  before/after pair. For a storyboard or flow sequence of multiple states, read
  `../visual-plan/references/canvas.md` for the horizontal canvas layout.
- For tiny surfaces like menus, popovers, dialogs, toasts, or panels, show the
  focused sub-surface. Do not redraw a full page unless placement in the page is
  itself part of the change.

Ground each wireframe in the changed UI behavior, component names, file paths,
and diff-visible labels/states. If exact pixels are inferred rather than
captured, say so in the wireframe caption or a concise annotation.

## Wireframe Quality — read `../visual-plan/references/wireframe.md`

> **Shared references:** The wireframe and artifact reference docs live in the
> sibling visual-plan skill at `../visual-plan/references/`. Both skills share the
> same plugin's `skills/` directory, so those relative paths are valid from here.

UI recap wireframes must meet a strict quality bar — full-width chrome, pinned
bottom bars, real product content, before/after comparability, the right surface
density, theme tokens instead of hex. Before authoring ANY wireframe, READ
`../visual-plan/references/wireframe.md` and `../visual-plan/references/artifact.md`
— together they are the source of truth for HTML wireframe quality and for the
self-contained-file correctness contract. Do not author wireframes from memory.

When a browser tool is available, open the rendered recap and visually inspect it
at the current theme before reporting. If any label, annotation, toolbar, or
wireframe content overlaps another element, fix the HTML and reopen. A text-match
screenshot is not enough; visually inspect the captured image. When no browser is
available (for example a headless CI agent), state that in the recap handoff
instead.

## Deliverable: a self-contained local HTML file

The deliverable is ALWAYS one self-contained HTML file
`plans/<slug>/recap.html` (`<slug>` = `YYYY-MM-DD-<short-topic>`), never inline
chat prose. Read `../visual-plan/references/artifact.md` first — it is the
correctness contract.

1. Collect the diff with git (`git diff`, `git diff --stat`, `git log`) for the
   whole work unit. Build every structured section mechanically from the real
   diff (see Grounding Rule).
2. Author `recap.html` as a single self-contained document, all CSS/JS inline,
   designed for this change. Use the reframed `../visual-plan/references/`
   docs for wireframe and document quality.
3. Validate: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_artifact.py" plans/<slug>/recap.html`.
   Fix any violation before handoff.
4. Open it (browser tool, else `open`/`xdg-open`, else report the path).
5. Feedback is file/chat based: edit `recap.html`, re-validate, reopen. Keep it
   covering the whole work unit unless asked to narrow scope.

## Diff → HTML Section Mapping — read `references/diff-mapping.md`

READ `references/diff-mapping.md` before authoring sections. It maps every kind
of diff change — schema, API, code hunks, new files, UI, architecture — to its
corresponding recap HTML section, with grounding, formatting, and annotation rules
for each. Do not build sections from memory.

## Before / After Is The Headline

The recap's center of gravity is the before/after comparison. `references/diff-mapping.md`
defines the two document-body primitives (side-by-side columns for structured
comparisons; split diff for code) and how wireframes serve as the visual
comparison primitive for UI diffs, including layout ownership from
`../visual-plan/references/wireframe.md`.

## Grounding Rule

Structured sections are **true by construction** only if they are derived from the
actual changed lines. The diff, data-model, API-endpoint, and file-tree sections
MUST be built mechanically from the real diff — real paths, real fields, real
method/path, real before/after text — never inferred, rounded, or invented. The
model writes only the prose: the "why", the narrative, the risk read. A
confidently wrong recap is dangerous in a review context, because a reviewer who
trusts the summary may skip the very line the summary got wrong. When the diff
does not contain a fact, leave it out rather than guess; mark anything the model
inferred (not extracted) as inferred in prose.

## Security

See `references/diff-mapping.md` for the full security guidelines: keep recaps
local and private (treat them like the source they summarize), and never
transcribe secrets — redact any keys, tokens, or credential-looking literals.

## Related Skills

- **visual-plan** — the canonical command and the source of the shared wireframe,
  artifact, and document-quality references; a recap follows the same section
  discipline in reverse.
