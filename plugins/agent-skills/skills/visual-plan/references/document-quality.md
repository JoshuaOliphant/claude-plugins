# Plan document quality — single source of truth

This file is the canonical quality bar for the plan document below the canvas:
how it reads, how to structure its sections, how open questions are surfaced, and
the pre-handoff check. Read it in full before authoring the plan document; it is
the quality bar. Do not write the document from memory or paraphrase these rules
per mode.

<!-- SHARED-CORE:document-quality START -->

**The document is a serious technical plan, not marketing.** Write it the way a
strong Claude or Codex implementation plan reads: outcome-first, prose-first,
self-contained, and specific. State the objective and what "done" means, the
scope and non-goals, the proposed approach with the key decisions and their
rationale, ordered steps that name real files, symbols, actions, and data
shapes, the risks, and a closing verification step (tests, build, or a checkable
behavior). Replace vague prose with specifics; never ship a step like "make it
work." No hero art, gradients, logos, nav bars, slogans, value props, giant
landing-page headings, or marketing cards unless the user explicitly asks.

**Every published plan must stand alone.** Even when the agent is revising an
existing plan, the output is a plan to do the work, not a changelog of the
conversation. Do not write phrases like "preserve the previous plan", "do not
drop the old idea", "as discussed above", "this revision", "unlike the prior
version", or "correction from the earlier plan". Fold the right decisions into
the plan as normal objective, architecture, scope, and roadmap prose. A reviewer
who opens the plan with no chat history should understand it. Avoid negative
framing that only makes sense against absent context ("not the old mode", "not
just X") unless the contrast is defined in the plan and genuinely helps; state
the positive model directly.

**Make abstract plans instantly legible.** If the idea is broad, strategic, or
intended for a third-party reviewer, put one concrete product snapshot near the
top before dense architecture, mode tables, manifests, or roadmaps. For
UI-capable concepts, that snapshot is usually a top-canvas app state plus a
short paragraph that says what the user sees and what changes under the hood.
Then put mechanics, data flow, sync boundaries, and implementation detail in
separate diagrams or document sections.

**Preserve the user's level of abstraction.** A motivating use case is not
automatically the architecture. When the prompt describes a broader framework,
product mode, or reusable primitive, separate the reusable core from specific
apps, providers, customers, scripts, or launch examples. Use the concrete
example to make the plan understandable, then make clear which parts are core,
which are app-specific adapters, and which are future examples.

**When top visuals exist, they and the document never duplicate each other.**
For UI work, the UI story lives in the top canvas; the document carries the
technical depth the visuals cannot show — concrete file/symbol maps, API and
data contracts, code snippets, migration or implementation phases, risks, and
validation. For architecture/code reviews, invert that: the document is the
visual surface, and each recommendation carries its own nearby inline diagram or
data-model summary plus file evidence. Repeat a wireframe in the document only
for a genuinely new detail view or comparison. Skip the visual surface entirely
for non-visual work and write a clean rich document. For a simple binary UI
visual choice, show the two directions in the canvas only; do not repeat the same
options as body wireframes or prose. Put the actual choice in the bottom "Open
Questions" section.

**Use the right section, and make it carry substance.** Build the document out of
ordinary HTML sections; choose the form that fits the content:

- Prose (real headings, paragraphs, bold/italic/code, nested lists) for the plan
  narrative.
- A file map: when a load-bearing file is worth highlighting, show the real code
  in a `<pre><code>` block AND anchor short notes to the lines that actually
  change (the new action, the changed schema, the wiring point), so the reader
  sees what matters and why instead of code for code's sake. Keep a few
  high-signal notes per file, not one per line. Highlight only the files worth
  reading; never an exhaustive list of every touched file, and never a prose-only
  description of a file. When more than one file matters, group them in a tabbed
  section (see the tabs skeleton in artifact.md) rather than a long vertical wall.
  If the exact code is unknown, show the smallest plausible planned shape or a
  commented stub naming what to fill in.
- For a decision: if the reviewer must still pick between a genuinely-open
  either/or, put it in the bottom Open Questions section as a single choice — one
  option per real alternative, each with a short detail and a marked recommended
  default; do not also restate the same choice elsewhere. If you have already
  committed to an approach, state it as settled prose or a decision callout,
  optionally with a two-column comparison of the options you weighed — not as a
  confusing mid-document form for a question you have already answered.
- A two-column section for side-by-side before/after or current/target
  comparisons where each side needs real content; label the columns clearly and
  avoid stacking comparison content vertically when parallel reading is the point.
- A diagram (semantic HTML plus inline SVG) for two-dimensional architecture,
  dependency, data-flow, or state relationships, only when it clarifies something
  real. Prefer standard two-dimensional layouts — paired before/after panels,
  layered diagrams, swimlanes, dependency maps, matrices, or grouped regions; do
  not default to left-to-right chains, and use a line only when the relationship
  is truly a sequence. Do not use a body diagram as the primary artifact for a
  requested product canvas, light storyboard, UI flow, screen flow, or wireframe;
  those belong in the top canvas as frames first. Use diagrams below that canvas
  only for architecture, data flow, or implementation mechanics. Style diagrams
  with the document's `:root` color variables (not hard-coded hex), keep labels
  short, give nodes generous width, and place boundary/annotation labels in
  unused space instead of over nodes; labels must not overlap nodes, connectors,
  or each other. In architecture/code plans, prefer a repeated section rhythm:
  recommendation title, confidence and category badges, code-path evidence, a
  local before/after or current/target spatial diagram, then concise
  Problem/Solution/Why text.
- A data-model summary section or table, and an api-endpoint summary section, when
  the plan changes a schema or a contract; carry the real field/route shapes, not
  a vague description.
- Tabs for multiple states, directions, or comparisons. A tab that reveals only
  prose usually means the plan is under-specified — include a relevant visual
  unless the tab is intentionally document-only.
- Tables, checklists, and callouts for scannable structure.

**Open questions live at the bottom as a section when answers would change the
plan.** Surface answerable unresolved decisions in a final "Open Questions"
section so the reader sees them as a distinct part of the document. That bottom
section is the ONLY place that enumerates the open questions: never add a second
"Open Questions" heading, list, or recap of the same questions earlier in the
document. A one-line pointer in the overview prose ("a few decisions are still
open — see Open Questions below") is fine, but do not reproduce the question list
or a parallel questions/decisions section above it. Use clear single/multi
choices for real alternatives, free-text for constraints, and mark the default
you would pick as recommended. Show option wireframe/diagram previews only when
the options are not already visible in the top canvas. Keep non-answerable
assumptions or risks as concise callouts in the relevant section. Never bury a
questions/decisions wall inside the plan narrative, and never ask the same
question twice.

For complex plans, do not end without an open-question audit. If architecture,
scope, UX, data shape, rollout, provider mapping, or ownership still depends on
a choice, either commit to a recommendation with rationale or add it to the
bottom section with a recommended default. A complex plan with no open questions
is fine only when every meaningful decision has been explicitly made.

**Verification must exercise the real workflow.** The final verification section
should go beyond typecheck/unit tests when the plan changes UI, local files,
sync, providers, browser behavior, or multi-app flows. Include at least one
end-to-end smoke that matches the user journey, such as a fresh repo/folder,
real manifest or data fixture, browser interaction, save/sync action, and an
on-disk or database assertion. Name the command or manual browser path when it
is known.

**Keep the whole document self-contained.** Everything — prose, diagrams,
wireframes, code, interactivity — lives in the one HTML file with inline CSS/JS
and no external network references (see artifact.md for the hard rules). Style
every section against the document's own `:root` variables so it reads in both
light and dark schemes; do not hard-code a white-card/dark-ink palette that
breaks under `prefers-color-scheme: dark`. Keep any interactivity dependency-free
vanilla JS.

**Before handoff, open the plan and check it.** Fix overlap, excessive
whitespace, clipped fragments, misleading inactive controls, poor contrast, and
unreadable diagrams before asking for approval. Run the artifact validator (see
artifact.md) and fix any reported violation.

<!-- SHARED-CORE:document-quality END -->
