# HTML wireframe quality — single source of truth

This file is the canonical quality bar for HTML wireframes, shared word for word
by `/visual-plan` and `/visual-recap`. Read it in full before authoring ANY
wireframe; do not author wireframes from memory or paraphrase these rules per
command.

Wireframes are plain semantic HTML styled by the document's own inline CSS (see artifact.md). Use CSS variables you define at :root; there is no external token system.

<!-- SHARED-CORE:wireframe-quality START -->

**A wireframe is an HTML mockup of a screen.** Write a self-contained, semantic
HTML fragment of the screen inside the plan document. You own the look: write
real HTML layout, real product content, and the CSS that styles it (via the
document's `:root` variables and ordinary CSS lengths). Compose the actual
product: reproduce the current screen, then show the modification. Real labels,
real counts, real dates, real button text grounded in the screen you read — not
lorem or gray bars.

**Define your own small token set and reuse it.** Pick a few CSS custom
properties at `:root` for the document (text color, muted text, borders, surface
background, an accent, a radius) and reference them in the wireframe so a mockup
stays internally consistent and reads in both light and dark schemes. Use literal
CSS lengths for spacing — `padding:16px`, `gap:12px`, `margin-top:18px`,
`minmax(0,1fr)` — rather than guessed spacing tokens. Use the system font stack;
do not pull in external fonts.

**No decorative shadows around mockups.** Do not put `box-shadow`, `filter:
drop-shadow(...)`, or other fake depth effects on a wireframe frame, root
container, card, or canvas artboard. Mockups should read as flat, bordered
surfaces; use spacing, borders, labels, and annotations for separation. Only show
a shadow when the real product UI already has that shadow and it is essential to
the change being reviewed.

**Use icons, not visible icon words.** For icon-only buttons or leading icons
inside fields, chips, menu items, and toolbars, draw a small inline `<svg>` (or a
sized box) rather than writing the word. Do not put visible words like "email",
"lock", "search", "chevron", or "more" where the product UI would show an icon;
use text only when it is a real label a user would read.

**Lay out with flex/grid.** You write the real layout —
`display:flex; flex-direction:column; gap:10px; padding:16px` and so on. Use
HTML flex/grid with `gap`, `min-width: 0`, and sensible overflow. Avoid negative
margins, absolute positioning, or fixed child widths that can collide.

**Surface types — match the real footprint, never default to desktop+mobile.**
Pick the surface type that matches what the user will actually see, and size the
frame accordingly:

- `page`: a web page (add a browser chrome frame around it when that helps).
- `desktop`: a full desktop app page or app shell.
- `mobile`: a phone screen, only when the work is genuinely mobile.
- `popover`: a small floating menu, dropdown, or inline popover.
- `panel`: a side panel, inspector, or sidebar widget.

A sidebar popover is a small surface, not a desktop page plus a phone frame. Do
not emit `desktop` + `mobile` variants unless responsive behavior actually
changes the layout. For a component or widget, show one broader app-context frame
only when placement affects understanding, then the focused component states.

**Model the actual component shell for small surfaces.** A rendered UI change
belongs in a wireframe; reserve architecture/dependency/state/data-flow
relationships for diagrams. Popovers, dropdown menus, command palettes, and
context menus are small floating surfaces unless the surrounding page placement is
the point of the change. Dialogs, sheets, inspectors, sidebars, and long property
panels use the matching panel/desktop footprint. Show the real chrome: trigger or
anchor when it matters, title/header row, top-right actions, separators, fields,
options, selected states, body content, and footer actions visible in the
workflow.

**Modify, don't redesign.** When the task changes an existing screen, reproduce
the current screen's real layout and footprint FIRST, then change only the delta
and call it out with a single annotation. Do not restack the page into a new
layout. For net-new surfaces, compose from the real app shell. Inspect the actual
app components before drawing an existing product: sidebar density, toolbar
actions, overflow menus, property panels, and framework chrome should match the
product unless the plan intentionally changes them.

**Keep product screens pure.** A product wireframe shows the app state a user
would actually see. Do not embed file contracts, architecture arrows, repo pills,
mode explanations, or implementation callouts inside the screen just to explain
the plan. Put those in canvas annotations, a separate diagram, or the document
body. Secondary UI such as properties, history, sync, export, or agent controls
should appear where the real product would put them: an overflow popover, sheet,
panel, or separate framework sidebar state, not a generic permanent right
inspector unless that inspector is the actual design.

**Zoom in on sub-surfaces, don't redraw the page.** For a small sub-surface (a
popover, menu, dialog, toast), show the full screen once, then add a small
separate wireframe that contains ONLY that sub-surface — do not re-draw the whole
page around it, and do not scale a duplicate up. Size it to the real footprint;
never widen a popover to page width.

**Loading / skeleton states.** Fill a skeleton wireframe with neutral, textless
placeholder geometry — boxes and bars built as `<div>`s with a muted background
and explicit heights/widths, no labels or copy.

**Treat the wireframe border as part of the visible design.** Always wrap HTML
wireframe content in a root container with real inner padding before drawing
cards, fields, pills, labels, or controls. Use at least 14-16px of padding,
`box-sizing: border-box`, and `gap` between child rows on the root node itself so
the first row never sits flush against the screen border. Do not rely on padding
on a nested page section as the first visible inset; the outermost element must
create the breathing room. Keep text away from borders: every container, field,
button, menu item, and annotation needs enough padding and line-height to read
cleanly.

**For feature-cloud or abundance visuals, optimize the composition over
line-by-line reading.** Some marketing/product sections need to feel like a large
surface area of capability rather than a precise app workflow. In those cases,
use one padded root with a short headline and a dense, aesthetic cloud of short
feature labels, chips, rings, or columns. Vary scale and opacity, cluster by
meaning, and let many labels be glanceable rather than individually essential. Do
not force dozens of features into equal cards with long wrapped sentences; that
usually creates a messy unreadable mockup.

**Do not wrap intentionally single-line labels.** For toolbars, tab rails,
breadcrumbs, chip/filter rows, branch and file names, file chips, and code
filenames — any deliberately single-line row — do not let long text wrap. Put
`white-space: nowrap` on the row (and `overflow: hidden; text-overflow: ellipsis`
on the individual labels that can grow), so the wireframe demonstrates the actual
layout behavior instead of producing ugly stacked or vertical text. Use
horizontally scrollable or clipped rails for overflow.

**Fill the frame; keep labels short.** Compose enough realistic HTML to fill the
surface top to bottom with even vertical rhythm; never leave a large empty band.
On desktop/app-shell sidebars, let the nav stack flex to fill (`flex:1`) and add
any persistent bottom action/status after it so the rail reads complete in taller
frames. On mobile especially, flow real rows down the whole screen (status bar,
header, then list/detail content) rather than a header floating above a gap. Keep
every label short enough to sit on one line within its column — shorten the copy
rather than relying on the frame to absorb it.

**Persistent chrome bars span the full frame width.** Top bars, app headers,
toolbars, and bottom tab/nav bars are full-width chrome, not centered content.
Lay each one out as a single flex row that fills the frame
(`style="display:flex;align-items:center;width:100%"`) and push trailing actions
to the right edge with a flex spacer (`<div style="flex:1"></div>`) between the
leading group and the trailing group — never center a bar inside a narrow,
centered block, and never let it collapse to the width of its contents. In a
Before/After pair the bar stays full-width in BOTH states even when one state has
fewer controls; the spacer absorbs the difference so the remaining controls hold
their edge alignment instead of sliding to the center.

**Pin bottom bars to the bottom of the frame.** For mobile tab bars, footers, and
any persistent bottom action row, make the frame itself a flex column at
`height:100%` (`style="display:flex;flex-direction:column;height:100%"`), give the
scrolling body `flex:1` so it absorbs the slack, and place the bar as the LAST
child of the frame (or set `margin-top:auto` on it). The bar then sits flush at
the bottom of the surface instead of floating directly under the content with an
empty band beneath it.

**Before / after must be comparable.** When showing a state change, preserve the
unchanged controls in both states so the reviewer can see exactly what moved or
appeared; do not show an added control as a generic box floating elsewhere in the
surface. Place the new/changed affordance where the implementation puts it — for
example, a new `Edit with AI` action in a popover header belongs in the top-right
header slot, aligned with the title, not in the body or footer. Use the same
frame size, scale, outer padding, border radius, and visual density on both sides
unless the change itself alters those properties, and let the frame height fit the
content rather than leaving a tall empty lower half.

**Name the states with a heading above the frame, never inside it.** For a
before/after pair, lay the two states out in two columns and put a heading
(`Before` / `After`) above each frame. Do NOT bake a `Before`/`After` pill,
title, or heading into the wireframe HTML: a label placed inside reads as part of
the product UI, lands in a random corner, and clutters the comparison. The column
heading is the one and only place the state name belongs.

**Let the surface choose side-by-side vs. stacked.** Lay narrow surfaces
(`mobile`, `popover`, `panel`) out side by side. Stack wide surfaces (`desktop`,
`page`) vertically at full document width so a large frame is never crushed into a
half-width column and cropped. Use the real surface footprint and the matching
`Before`/`After` headings; do not duplicate the state name as body content.

**Good example — a contacts list, a `page` surface.** A small, real screen, layout
in inline flex, colors from the document's `:root` variables, no external fonts:

```html
<div style="display:flex;flex-direction:column;gap:12px;padding:16px">
  <div style="display:flex;align-items:center;justify-content:space-between">
    <h1>Contacts</h1>
    <button class="primary">New contact</button>
  </div>
  <div style="display:flex;gap:6px">
    <span class="pill accent">All 128</span>
    <span class="pill">Favorites</span>
    <span class="pill">Archived</span>
  </div>
  <div class="card" style="display:flex;flex-direction:column;gap:0;padding:0">
    <div
      style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-bottom:1px solid var(--line)"
    >
      <div
        style="width:32px;height:32px;border-radius:999px;background:var(--accent-soft)"
      ></div>
      <div style="flex:1">
        <strong>Jane Cooper</strong><br /><small>jane@acme.co</small>
      </div>
      <span class="pill">Lead</span>
    </div>
    <div style="display:flex;align-items:center;gap:10px;padding:10px 12px">
      <div
        style="width:32px;height:32px;border-radius:999px;background:var(--accent-soft)"
      ></div>
      <div style="flex:1">
        <strong>Marcus Lee</strong><br /><small>marcus@globex.io</small>
      </div>
      <span class="pill">Customer</span>
    </div>
  </div>
</div>
```

<!-- SHARED-CORE:wireframe-quality END -->
