# Prototype

A prototype is throwaway code that answers one question the spec can't settle in prose. The
question decides its shape, so write the question down first, at the top of the prototype where
anyone opening it sees it.

## Pick the shape

- **"Does this logic or state model hold up?"** Build a logic prototype.
- **"What should this look like?"** Build a UI prototype.

If the question is ambiguous and nobody is around to ask, pick the shape that matches the
surrounding code (a backend module means logic, a page or component means UI) and state that
assumption at the top.

## Logic prototype

One self-contained HTML file that anyone, including a non-developer, can open by double-clicking
and use to push the state model through the cases that are hard to reason about on paper.

1. Put the logic in one `<script>` block as a small pure module: a reducer
   `(state, action) => state`, an explicit state machine when "which actions are legal now" is
   part of the question, or a few pure functions over plain data. No DOM access inside it. The page
   calls the module; nothing flows the other way. That keeps the module liftable into real code.
2. Lay the page out top to bottom: the title and the question; the current state as a readable
   panel of labelled fields, re-rendered after every click; one free-play button per action; and
   guided walkthroughs, one tab per scenario (the happy path, a tricky edge, something that should
   be illegal), each a short description over the ordered buttons to press. Starting a walkthrough
   resets to a known state.
3. Label everything in the domain's words, not the code's.
4. Plain HTML, CSS, and JS, all inline. No framework, bundler, server, or persistence.

## UI prototype

Several structurally different variations of one screen, switchable in the browser.

1. Default to three variants; more than five stops being different and becomes noise. Variants
   must disagree about layout, hierarchy, or the primary affordance, not colour or copy.
2. Prefer mounting them on the existing page they belong to, behind a `?variant=` search param,
   keeping the page's real data fetching. Only when nothing hosts them, add a throwaway route named
   so it is obviously a prototype, following the project's routing convention.
3. Add a small floating bar at the bottom with previous and next arrows and the variant's name,
   also driven by the left and right arrow keys (except while a text field has focus), updating
   the URL so a variant can be shared. Hide it in production builds.
4. Point any mutation at a stub; the question is what it looks like, not whether the backend works.

## Rules for both

- Start it with one command, or a double-click. No setup to think about.
- State lives in memory unless persistence is the question; then use a scratch store named
  `prototype-wipe-me` or similar.
- No tests, no error handling beyond what keeps it running, no abstractions. It exists to learn
  something fast.
- Show the full relevant state after every action or on every variant switch.

## When it has answered

1. Commit the prototype to a `prototype/<slug>` branch, never to the main line. It is evidence.
2. Record the question and the verdict in the spec's Evidence section, linking the branch, and add
   the decision to the refined prompt marked `(prototype: <branch>)`.
3. If a snippet pins the decision more precisely than prose (the reducer, the state machine, the
   schema), quote the decision-rich part in the spec, marked as from the prototype.
4. Validated logic lifts into the real code during `compost:build`, rewritten to production
   standards with its tests. The prototype's page and the losing UI variants stay on the branch.
