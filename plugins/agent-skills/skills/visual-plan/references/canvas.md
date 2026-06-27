# Canvas & storyboard layout — single source of truth

This file is the canonical guide for when and how to put a "canvas" — a top row
of wireframe panels — at the top of the plan document. Read it in full before
authoring or editing any canvas content; do not author canvas layouts from memory
or paraphrase these rules per mode.

<!-- SHARED-CORE:canvas-surface START -->

**What a canvas is.** A canvas is simply a horizontal row of wireframe panels at
the top of the HTML document — a flex or grid row whose cells are the wireframe
frames described in `wireframe.md`. It gives a UI plan a top "review area" the
reader sees before the prose. Build it with plain HTML/CSS, e.g.:

```html
<div class="canvas" style="display:flex;gap:24px;overflow-x:auto;padding:16px 0">
  <figure class="frame"><figcaption>Empty state</figcaption><div class="wire">…</div></figure>
  <figure class="frame"><figcaption>Filled state</figcaption><div class="wire">…</div></figure>
  <figure class="frame"><figcaption>Saved</figcaption><div class="wire">…</div></figure>
</div>
```

**When a canvas helps.** Use a top canvas when the work is UI/product and the
reviewer needs to see the screens before the technical detail: a static mockup, a
UI state, a loading state, a layout, a visual comparison, or a short flow. Skip
it entirely for non-visual work (e.g. a backend/architecture review) and write a
clean document instead. Architecture/code diagrams stay inline in the document
next to the claim they support, not in the top canvas.

**One artboard per user-visible state.** Give each distinct screen or state its
own frame in the row, with a short heading above it (an empty state, the filled
state, an error, a confirmation). Do not cram several states into one frame, and
do not fake a sequence with connector lines between independent states. Lay the
frames out left to right in the order the user moves through them.

**Lay out mixed surfaces sensibly.** When the canvas mixes broad page/desktop
frames with compact `mobile`, `popover`, or `panel` frames, do not force
everything into one cramped strip. Give broad frames their own row and group the
compact surfaces together (a second row, or a column beside the main flow), with
generous gaps so frame borders, headings, and labels never touch. Each frame
keeps its real footprint (see the surface types in `wireframe.md`); never widen a
popover to page width just to fill the row.

**Annotations are short notes beside the frame they explain.** When a frame needs
explanation, put a short plain-text note (a heading plus a line or two, or a few
bullets) next to it — not a bordered or shadowed card, and never a box drawn
around the frame. Keep each note adjacent to the frame it describes. Use a small
arrow only to point at one specific control or transition; a frame-level note
needs no connector.

**Keep product screens separate from explanatory diagrams.** A canvas frame shows
real product UI a user would actually see. Do not mix architecture arrows, repo
names, file contracts, or mode explanations into a product screen just to explain
the plan — that belongs in a separate diagram or in the document body. For an
abstract concept, make the first frame one real app state that creates the "I get
it" moment, and put the mechanics in a separate diagram or prose below.

**Storyboards are canvas artifacts, not document diagrams.** When the requested
output is a product flow, onboarding journey, "light storyboard", or screen flow,
author it as multiple canvas frames with real screen content laid out in order.
Keep document-body diagrams for architecture and mechanics that are not themselves
user-visible screens. A storyboard made from a single inline diagram is the wrong
surface.

**Every frame must carry real wireframe content.** Each panel in the canvas must
contain an actual HTML wireframe — never a titled-but-empty frame. If all you have
is a title, write it as a section heading or an annotation, not an empty frame.

**The canvas and the document never duplicate each other.** When a top canvas is
present, the UI story lives there; the document below carries the technical depth
the screens cannot show (file/symbol maps, contracts, snippets, phases, risks,
validation). Repeat a wireframe in the document only for a genuinely new detail
view or comparison.

<!-- SHARED-CORE:canvas-surface END -->
