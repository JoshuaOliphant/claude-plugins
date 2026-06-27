# Diff → HTML Section Mapping

Map each kind of change to the HTML section that carries it, derived mechanically
from the actual diff. Each conceptual item below becomes a section you render in
`recap.html`.

- **Schema / migration change** → a **data-model** section for the resulting
  entities, fields, and relations. Flag what moved per field/entity
  (`added` / `modified` / `removed` / `renamed`), and for a changed type show the
  prior value (e.g. the old column type) — grounded in the real migration diff.
  That diff-aware data-model is the headline; reach for a split diff of the
  literal SQL only when the exact statement still matters, not by default.
- **API / action / route change** → an **API-endpoint** section with the method,
  path, params, request, and responses as they are after the change. Flag each
  changed param/response (and the prior type/shape on a param that changed), and
  mark a wholly added or removed route. Mark removed endpoints as deprecated and
  explain in prose. Keep multiple API endpoints in the normal single-column
  document flow unless they are an explicit before/after contract comparison.
  Author each request/response example as a SINGLE valid JSON value — one
  top-level object or array, parseable on its own — so it renders cleanly. Do not
  put `//` or `/* */` comments, prose, trailing commas, or two or more
  concatenated top-level objects inside one example. When an endpoint has several
  distinct message shapes (for example separate websocket frame types, or a
  success body versus an error body), give each its OWN labeled example rather
  than cramming them into one body.
- **Compatibility-sensitive change** → a short **prose** note beside the relevant
  data-model / API-endpoint section. Name the changed field, endpoint, or behavior
  and mark whether it is breaking, risky, or non-breaking; pair that note with a
  split diff for the literal lines.
- **Any meaningful code hunk** → a **split diff** carrying the real before / after
  text and the filename / language. Split layout is the default for recap code
  review because before/after legibility is the point; use a unified hunk only for
  a genuinely narrow standalone change where side-by-side would hide the code.
  Give every diff a one-line summary saying what the hunk changes and why; render
  it as a description above the code so the reviewer reads intent first. Never
  leave a diff unlabeled. For the KEY changed files, attach annotations to the
  diff so the recap calls out what each important hunk does — this is the headline
  affordance for annotating the key files updated. Anchor each annotation to the
  after-side line numbers by default (point at removed lines when needed). Keep it
  to a few high-signal notes per file, not one per line.
  When several key files each need a substantial diff, introduce the group with a
  `## Key changes` heading, then place the diffs under it in a horizontal tabs
  control (one file per tab) so the selected file's split diff gets the full
  document width. Keep each tab label to the file path or a short basename plus
  directory hint. If the recap ends with more than one supporting diff, that
  trailing diff appendix should be one horizontal tabs control under its own
  `## Key changes` heading, not a stack of separate diff sections.
- **Brand-new file or a substantial added block with no meaningful "before"** →
  an **annotated-code** section rather than a one-sided split diff. Carry the real
  new code with its filename / language and anchor a few high-signal notes to the
  lines that matter so the reviewer reads what the new code does, not code for
  code's sake. Keep split diffs for true before/after hunks where the removed
  lines still carry meaning, and group several annotated walkthroughs in a
  horizontal tabs control the same way diffs are grouped.
- **Files added / removed / renamed** → a **file-tree** section with each entry's
  change flag (`added`, `removed`, `modified`, `renamed`) and a short note; attach
  a snippet only when one tells the reviewer something the path does not.
- **Rendered UI / interaction change** → one or more **wireframes** showing the
  visible UI delta before the reviewer reads code. Use Before / After wireframes
  when the comparison clarifies the change; otherwise use after-only or a short
  state/flow sequence. Use realistic UI surfaces: for a popover change, show a
  popover with its title row, top-right actions, options/fields, tabs,
  selected/disabled states, people/lists/rows, and any opened prompt/menu anchored
  to the correct trigger. If a route was added, show the route body and the
  unavailable/empty state when the diff implements one. If permissions changed,
  show what managers can do and what viewers/non-managers see instead. Keep the
  body lean: the wireframe carries the UI story, while the file-tree and diffs
  carry implementation evidence.
- **Architecture or data-flow shift** → a **diagram** section as a two-panel
  before/after, layered, or swimlane layout. Use two-dimensional layouts; do not
  reduce a structural change to a left-to-right chain. Do not use a diagram as a
  stand-in for rendered UI controls; UI changes need wireframes. Author the
  diagram with the same theme tokens `../visual-plan/references/wireframe.md`
  defines — never one-off hex/rgb/hsl literals or one-off dark/light palettes.
- **Outcome-first narrative** → **prose** for the "what changed and why": the
  objective the diff served, the key decisions visible in it, and the risks a
  reviewer should weigh. This is the only place the model writes freely.

# Before / After Is The Headline

The recap's center of gravity is the before/after comparison. For document-body
comparisons there are two primitives, and they cover the whole need together:

- **Side-by-side columns** — for **structured** comparisons. Use two columns
  labeled `Before` and `After`, each holding a section (commonly a data-model,
  API-endpoint, or prose block), so the reviewer reads the old shape against the
  new shape in one glance. This is the right primitive for "the schema went from
  X to Y" or "the endpoint contract changed like this." Do not use columns simply
  to compact or group a list of API endpoints.
- **Split diff** — for **code**. It renders the literal removed and added lines.
  Use it for the actual hunks. Use split layout by default for recap code review;
  reserve a unified hunk for genuinely narrow standalone changes where
  side-by-side would hide the code. Key-file diff groups should use horizontal
  tabs so split diffs get the full document width.

For UI diffs, wireframes are the visual comparison primitive. Use before/after
wireframes when the comparison clarifies the change; use after-only or a state
sequence when that better matches the change. The visual headline must show exact
placement, realistic chrome, and adequate padding before any abstract
explanation. Do not stop at the first visible affordance when the diff adds a
flow; show the entry point, the opened surface, and the resulting state or page so
the reviewer can trace the actual user path. `../visual-plan/references/wireframe.md`
owns the before/after layout choice — narrow surfaces stay side by side and wide
desktop/browser frames stack vertically; never hand-build a side-by-side wireframe
layout from scratch.

# Security

- **Keep recaps local and private.** A recap can expose unreleased schema,
  internal endpoints, and architecture; treat it like the source it summarizes.
  The recap is a local HTML file — keep it out of shared locations unless the user
  asks for it, and do not commit it to a repo where the audience should not see
  the change.
- **Never transcribe secrets.** A diff can contain API keys, tokens, webhook
  URLs, signing secrets, `.env` values, or credential-looking literals. Do not
  copy any of these into a diff, file-tree snippet, API-endpoint, or prose
  section — redact them (`sk-•••`, `<redacted>`). This mirrors the repo's
  hardcoded-secret rule: obviously fake placeholders only, never the real value,
  in any section, caption, or note.
