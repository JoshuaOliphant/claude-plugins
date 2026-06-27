---
name: visual-plan
description: >-
  Use when turning a plan into a self-contained interactive HTML document
  (diagrams, file maps, annotated code, wireframes, open questions) saved locally
  and opened in the browser — no account or external service.
---

# Visual Plan

Visual Plan is structured visual planning mode for coding agents. Build the plan
you would normally write in Markdown, but as a scannable interactive document
with rich elements mixed in: inline diagrams, code snippets, file maps, open
questions, and an optional top visual review area (wireframe canvas for UI work).
Architecture and backend plans stay document-only; UI and product plans start
with a top visual surface (the Visual Surface Choice section owns that rule).

The deliverable is a single self-contained HTML file the agent saves locally and
opens in the browser — everything inline, no account, no external service. Choose
the review emphasis from the task: UI-first when the work is primarily product UI
and review should start with screens, prototype-style when review should walk a
functional flow, or document-only for architecture, backend, and data work. When
a Codex, Claude Code, Markdown, or pasted plan already exists, use that source
plan as the starting point and build the review surface from it instead of
starting over.

## When To Use

Create or adapt a visual plan whenever the plan would be better as a reviewable
artifact than a chat paragraph. This includes modest work such as a single UI
surface with states, a small workflow, a before/after product change, or a
component/API/data-shape decision that needs alignment, plus larger multi-file,
ambiguous, long-running, risky, or UI-heavy work. Use it when architecture /
data flow / UI direction / options / open questions would benefit from inline
diagrams or structured sections, when the user needs to react to a direction
before you implement, or when an existing text plan needs a richer review
surface.

## Plan Discipline

- **Gate thoughtfully.** A visual plan is a richer review surface, not only a
  tool for giant projects. Use it when the user needs to see, compare, comment
  on, or approve a direction before code, even for a modest UI/state/workflow
  change. Skip it for truly trivial, unambiguous work — typos, one-line fixes, a
  single well-specified function, anything whose diff you could describe in one
  sentence — and just make the change. Never pad a plan with filler and never
  ship a single-step plan.
- **Research before you draft.** Read the real files, actions, schema, and
  patterns first; name actual files, symbols, and data shapes instead of
  inventing them. Check existing `actions/` before proposing endpoints and prefer
  named client helpers over raw fetch. Delegate wide exploration to a sub-agent.
  Lead with reuse: for each step, name what it reuses — existing actions, schema,
  components, helpers — before what it adds, so the plan explains the genuinely new
  delta instead of redescribing what already exists.
- **Decide the hard-to-reverse bets first.** For non-trivial backend, data, or API
  work, sketch where the feature is headed, then call out the decisions that are
  expensive to undo once data or callers depend on them — wire format, public ids,
  data-model shape, auth and ownership boundaries — and get those right in the plan
  even if most of the feature ships later. Then scope to the smallest first cut that
  proves the approach without foreclosing it, stating both what is in and what is
  explicitly deferred.
- **Keep examples at the right altitude.** When the user's idea is a broad
  framework, product, or operating-model change, do not collapse it into the
  first concrete example, provider, or sync path they mention. Separate the core
  abstraction from motivating examples and app/provider adapters. Use examples
  to make the plan legible, but label them as examples unless they are the whole
  requested scope.
- **Write standalone plans.** If the user pasted, referenced, or already has a
  Codex / Claude Code / Markdown plan, treat it as source material, but rewrite
  the plan as a clean standalone proposal. Preserve the source plan's useful
  intent and codebase facts, label inferred visuals as inferred, and avoid
  revision language such as "preserve the prior plan", "do not drop the old
  idea", "unlike the previous version", or "this revision changes...". A reader
  who never saw the chat or earlier drafts should understand the plan.
- **Make the first read concrete.** If the plan is meant to be shared with
  someone outside the chat, or if the concept is abstract, lead near the top with
  one concrete product example before mode tables, architecture, or roadmaps. For
  UI-capable concepts, that usually means a top-of-document app state that shows
  the real user workflow in product terms. Do not rely on phrases that only make
  sense in conversation, and do not frame the plan as "not the old idea"; state
  the positive model directly.
- **Planning is read-only.** Make no source edits while building or reviewing the
  plan. Start editing only after the user approves the direction.
- **Clarify vs. assume.** Do not ask how to build it — explore and present the
  approach and options in the plan. Ask a clarifying question only when an
  ambiguity would change the design and you cannot resolve it from the code; use
  the host agent's normal ask-user-question flow and batch 2-4 high-leverage
  questions before finalizing. Otherwise state the assumption explicitly and
  proceed, and keep anything unresolved in the plan's Open Questions section. For
  complex plans, do a final open-question pass before handoff: if a decision
  would affect architecture, scope, UX, data shape, or rollout, either decide it
  in the plan with rationale or put it in Open Questions with a recommended
  default.
- **The plan is the approval gate.** After surfacing it, ask the user to review
  and approve before you write code, and name which files/areas the work touches.
  Presenting the plan and requesting sign-off is the approval step — do not ask a
  separate "does this look good?" question.
- **The document is the source of truth, not the chat.** When scope shifts,
  update the HTML document rather than only changing course in chat, and make the
  updated document stand alone. Do not describe the update as a correction to an
  earlier draft inside the plan itself. Re-read the approved plan before major
  steps.

## Deliverable: a self-contained local HTML file

The deliverable is ALWAYS one self-contained HTML file, never inline chat prose.
Read `references/artifact.md` first — it is the correctness contract (everything
inline, no external network references, valid document, self-validate).

Workflow:

1. Research the codebase first (see Plan Discipline). Planning is read-only.
2. Choose the visual surface (see Visual Surface Choice). Author the plan as a
   single HTML document under `plans/<slug>/plan.html`, where `<slug>` is
   `YYYY-MM-DD-<short-topic>`. Write all CSS/JS inline; design it for this plan
   (no fixed template). Follow `references/wireframe.md`,
   `references/document-quality.md`, and `references/exemplar.md` for quality.
3. Validate self-containment:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_artifact.py" plans/<slug>/plan.html`.
   Fix any violation before handoff.
4. Open it for the user: use a browser tool if available, else run `open`
   (macOS) / `xdg-open` (Linux) on the file, else report the absolute path.
   Then ask the user to review and approve before you write code — presenting
   the plan IS the approval gate.
5. Iterate from feedback: the user comments in chat. Edit
   `plan.html` directly, re-validate, and reopen. The document is the source of
   truth; keep it standalone (no "this revision changes…" language).

## Self-Review Before Handoff

For high-stakes plans — architecture, backend, data-model, migration, multi-file,
or otherwise risky work — run one adversarial self-review pass before treating the
plan as final. Skip it for small, UI-only, or single-decision plans where the cost
outweighs the value. Keep the pass cheap and non-blocking:

- **Surface the plan first, review concurrently.** Open the document and let the
  user start reading, then run the review in parallel — never make the user wait
  on it.
- **Review the written plan; do not re-research.** Critique the plan text and its
  own sections. The grounding was already done while drafting, so the review checks
  the output instead of re-exploring the repo.
- **Spawn one skeptical reviewer** whose only job is to find what is weak, missing,
  or wrong — not to praise. Point it at: hard-to-reverse decisions made implicitly
  or not at all (wire format, public ids, data-model shape, auth, ownership); steps
  not anchored in real files or symbols; a menu of options where the plan should
  commit to one; obvious missing decisions ("what happens when X?", "why not Y?");
  and padding or single-step filler.
- **Fix vs. ask.** Apply clear-cut fixes yourself by editing the HTML — vague
  non-goals, unanchored claims, an obvious missing decision. Route genuine
  judgment calls back to the user instead: add them to the Open Questions section
  or batch them into the normal ask-user-question flow. Do not silently decide
  them.
- **Do not surprise the user mid-read.** If you must edit while they are reading,
  note briefly that a self-review is running so the document changing under them is
  expected. When you next respond, summarize what the review changed and what it
  surfaced for the user to decide.

## Visual Surface Choice

Choose the surface before authoring the plan or after reading the source plan. Do
not add visual chrome by default:

For UI/product plans, a top visual surface is usually the primary review surface.
Put the first meaningful wireframes there, not buried deep in the document body.
Use multiple wireframe states when they matter, such as the default view, an
overflow menu or popover, a side panel, loading, or error. Put short annotations
beside frames; keep implementation details, tradeoffs, file maps, data contracts,
risks, and verification in the document body below the wireframes.

When the user asks for a flow, storyboard, journey, wireframe, or "what this looks
like", treat that as a wireframe-first request. Make one frame per user-visible
state, connect only adjacent transitions, and use short annotations for the
product notes. Do not substitute an explanatory diagram for the requested
storyboard just because diagrams are faster to write; diagrams belong below the
wireframes for backend mechanics, architecture, or data-flow explanation.

Keep product wireframes and explanatory/meta diagrams separate. Start with pure
screens that look like the app state under discussion, without callout prose or
architecture notes embedded inside the UI. Put arrows, labels, contracts, data
flow, and mode explanations in separate annotations, separate diagrams, or the
document body.

When the plan touches an existing app, inspect the current shell/components
before drawing. The first wireframe should look like the real app at the same
density: existing sidebars, toolbar placement, overflow menus, and app chrome stay
in their real places. Model secondary surfaces as separate states, such as a
top-right overflow popover, sheet, panel, or loading state, rather than inventing
a permanent inspector or folding chrome into the product UI.

- **No visual surface** for architecture-only, backend-only, data migration,
  copy-only, or otherwise non-visual plans. Do not use a top wireframe surface for
  architecture diagrams, dependency maps, file plans, API contracts, or
  data-flow-only reviews. Use a strong document with local inline diagrams
  only when relationships need a visual explanation, usually one spatial diagram
  per recommendation or decision. Prefer grouped regions, layers, quadrants,
  matrices, or before/after panels over a single-axis chain unless the
  relationship is truly sequential.
- **Wireframes only** for one static screen, a before/after comparison, a
  component state, a small popover, or a visual direction that does not require
  clicking. Put those wireframes at the top of the document.
- **Wireframes + interactive flow** for multi-step UI flows, onboarding, wizards,
  review/approval flows, navigation changes, or anything where the reviewer needs
  to follow the behavior. Keep the static wireframes at the top, add the aligned
  step-by-step flow below or in tabs, and let dependency-free vanilla JS switch
  between states.
- **Flow-first** when the user asks to operate the UI or when interaction is the
  main question. Lead with the operable flow while still preserving static mocks
  where useful.

For mixed wireframe + flow plans, reuse the same real labels, app statuses, and
screen ids across both. The static wireframes are the inspectable reference; the
flow is the interactive version of that same path, not a separate design
direction.

## Artifact correctness — read `references/artifact.md` first

The deliverable is ONE self-contained HTML file: everything inline, no external
network references, a valid document, and self-validated with
`scripts/validate_artifact.py` before handoff. Before authoring the file,
READ `references/artifact.md` in this skill directory — it is the correctness
contract. Read it first, before the quality references below.

## Wireframe quality — read `references/wireframe.md`

UI plan wireframes must meet a strict quality bar — full-width chrome, pinned
bottom bars, real product content, before/after comparability, and the right
visual density. Before authoring ANY wireframe / screen, READ
`references/wireframe.md` in this skill directory — it is the source of truth for
HTML wireframe quality. Do not author wireframes from memory.

## Canvas layout — read `references/canvas.md`

When a plan benefits from a top storyboard/canvas (one frame per user-visible
state), the canvas is just a horizontal row of wireframe panels in plain
HTML/CSS. `references/canvas.md` owns the layout rules: one artboard per state,
laying out mixed-width surfaces, annotation placement, and keeping product
screens separate from explanatory diagrams. Read it before authoring a canvas.

## Document quality — read `references/document-quality.md`

The document is a serious technical plan, not marketing: outcome-first,
prose-first, self-contained, built from the right sections, with open questions
in a single place and a pre-handoff visual check. Before authoring the plan
document, READ `references/document-quality.md` in this skill directory — it is
the source of truth for the document quality bar. Do not write the document from
memory.

## Good vs. bad exemplar — read `references/exemplar.md`

For a worked example of the bar — a great UI-first plan, plus the anti-patterns to
avoid — READ `references/exemplar.md` in this skill directory before authoring a
plan.
