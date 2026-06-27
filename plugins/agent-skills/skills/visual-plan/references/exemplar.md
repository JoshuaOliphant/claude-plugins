# Good vs. bad exemplar — single source of truth

This file is the canonical worked example of a great plan (and the anti-patterns
to avoid). Read it alongside the document-quality, wireframe, and canvas
references before authoring a plan; it is the bar these plans must clear. The
deliverable is ONE self-contained HTML file that obeys `artifact.md`.

<!-- SHARED-CORE:exemplar START -->

## A complete worked example

Below is a compact, complete `plan.html` for a small UI change ("add saved-search
filters"). It is self-contained: one file, all CSS inline in a `<style>` tag, no
external network references, a valid document, a `:root` token set with a dark
scheme, a semantic-HTML wireframe of the surface, a two-column before/after of the
key change, and an Open Questions section at the bottom. This is the shape every
plan should take — expand the sections with real product content, real file/symbol
maps, and real diffs for the actual task.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Plan: Add saved-search filters</title>
  <style>
    :root { --bg:#fff; --fg:#111; --muted:#666; --accent:#2563eb; --line:#e5e7eb; --radius:10px; }
    @media (prefers-color-scheme: dark){ :root{ --bg:#0b0d10; --fg:#e6e8eb; --muted:#9aa3ad; --line:#1f242b; } }
    body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background:var(--bg); color:var(--fg); line-height:1.55; }
    main { max-width: 860px; margin: 0 auto; padding: 32px 20px 96px; }
    h1 { font-size: 1.7rem; } h2 { margin-top: 2rem; border-bottom:1px solid var(--line); padding-bottom:.3rem; }
    .wire { border:1px solid var(--line); border-radius:var(--radius); padding:14px; }
    .diff { display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--line); border-radius:var(--radius); overflow:hidden; }
    .diff pre { margin:0; padding:10px; background:var(--bg); overflow:auto; font-size:.85rem; }
  </style>
</head>
<body>
  <main>
    <h1>Plan: Add saved-search filters</h1>
    <p>Outcome-first summary of what changes and why…</p>
    <h2>UI</h2>
    <div class="wire"><!-- semantic HTML wireframe of the surface --></div>
    <h2>Key change</h2>
    <div class="diff"><pre class="before"><code>// old</code></pre><pre class="after"><code>// new</code></pre></div>
    <h2>Open questions</h2>
    <ul><li>…</li></ul>
  </main>
</body>
</html>
```

## What makes a plan good

**GOOD — a UI-first plan.** A top canvas (a flex row of wireframe frames) shows the
real product states: an empty search, a filter being applied, the saved result.
Each frame is a real flex layout with a sidebar of links (`Inbox 12`, `Today 4`,
`Done`), an `<h1>`, accent pills for filters, a muted section label, and card rows
carrying real titles, dates, and a primary button — all colored from the
document's `:root` variables, never hard-coded hex. Short plain-text notes sit
beside the frames, pointing only at the controls that need explanation. Below it, a
Claude/Codex-grade document: objective and done-criteria, a few code blocks
(grouped in a tabbed section when more than one) showing the real shape of the
load-bearing files, a decision callout stating the chosen approach with a
two-column comparison of the two real options behind it, and a validation step —
none of it repeating the canvas.

**GOOD — a broad product-architecture plan.** It opens with a plain recommendation
and one concrete app state before the abstraction. The first canvas frame is pure
product UI matching the current app shell; nearby notes explain the user-visible
delta. A separate diagram below shows the mechanics (file or data flow). The
document then separates the reusable core from app/provider adapters and examples,
covers contracts, folder or schema shape, sync boundaries, roadmap, non-goals, a
bottom Open Questions section for unresolved decisions, and a verification section
with at least one realistic end-to-end smoke. A reviewer who was not in the chat
gets the idea from the top snapshot before reading the technical plan.

**GOOD — a backend architecture review.** No top canvas. The document opens with
context and a legend, then repeats recommendation sections: title,
confidence/category badges, a monospace grid of real file paths, one inline
two-dimensional before/after or layered architecture diagram (built from semantic
HTML plus inline SVG, colored from the `:root` variables), and terse
Problem/Solution/Why bullets using the codebase's vocabulary. The diagram uses
space to show boundaries, layers, and ownership; it is not a default
left-to-right chain. The plan ends with a top recommendation and a bottom Open
Questions section only if the next architecture direction is genuinely open. This
is better than a top canvas because each diagram is local to the claim it
supports.

## Anti-patterns to avoid

- **Padding and filler.** Hero headings, value props, gradients, logos, or
  marketing cards that just restate what the canvas already shows; a tab or
  section that reveals only filler prose.
- **Single-step plans.** A "step" like "make it work"; a plan with one vague
  paragraph and no ordered, file-naming steps, scope, risks, or verification.
- **External fonts or CDNs.** Any `https://`/`http://`/`//host` reference, a
  Google Fonts link, a CDN script, or a remote image. Everything is inline
  (system font stack, inline `<svg>` or `data:` images) per artifact.md.
- **Wireframes authored from memory.** Mockups with hard-coded hex colors or a
  baked-in `font-family`; gray placeholder bars insinuating text on a non-skeleton
  frame; a forced desktop + mobile pair for a popover; floating bordered
  annotation cards hugging the frames; a product screen that mixes real UI with
  repo names, file-contract arrows, or a made-up permanent inspector instead of
  reproducing the actual current screen.
- **Duplication and stale framing.** The same wireframe repeated in canvas and
  document with no new detail; an architecture-only plan forced into a top canvas
  of labeled boxes with overlapping text while the real evidence lives elsewhere;
  a plan that describes itself as a revision of a prior conversation instead of a
  standalone proposal.

Never produce these.

<!-- SHARED-CORE:exemplar END -->
