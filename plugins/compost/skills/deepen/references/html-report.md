# HTML report

Only when the user asks for a visual report of the candidates. Write one self-contained HTML file to
the OS temp directory so nothing lands in the repository: `$TMPDIR` (falling back to `/tmp`), named
`architecture-review-<timestamp>.html`. Open it (`open` on macOS, `xdg-open` on Linux) and give the
absolute path.

## Scaffold

Tailwind and Mermaid come from CDNs; nothing else runs.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review: {{repo}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral" });
    </script>
    <style>
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header><!-- repo, date, legend --></header>
      <section id="candidates" class="space-y-10"><!-- one article per candidate --></section>
      <section id="top-recommendation"><!-- one card --></section>
    </main>
  </body>
</html>
```

## Header

Repository name, date, and a legend: solid box is a module, dashed line is a seam, red arrow is
leakage, thick dark box is a deep module. No introduction.

## Candidate card

One `<article>` per candidate:

- **Title** naming the deepening ("Collapse the Order intake pipeline").
- **Badges**: strength (Strong in emerald, Worth exploring in amber, Speculative in slate) and the
  dependency category.
- **Files** in a monospaced list.
- **Before and after diagram**, side by side, about 320px tall. This carries the card.
- **Problem**: one sentence.
- **Change**: one sentence.
- **Gains**: short bullets in glossary terms ("locality: pricing bugs land in one module").
- **ADR note**, when it contradicts one: one line in an amber box saying which ADR and why reopen it.

If a diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Vary them; the same diagram on every card stops carrying information.

- **Mermaid flowchart** for call flow and dependencies. Colour leaking edges red with `classDef`. A
  sequence diagram suits "six round-trips before, one after".
- **Boxes and arrows** in divs with inline SVG, when the after state should read as one heavy module
  with its old parts faded inside.
- **Cross-section**: stacked bands for the layers a call passes through; six thin bands before, one
  thick band after.
- **Mass diagram**: two rectangles per module, interface and implementation. Shallow has them nearly
  equal; deep has a short interface over a tall implementation.
- **Call-graph collapse**: a tree of calls before, the same tree folded into one box after.

## Top recommendation

One larger card: the candidate's name, one sentence on why it goes first, and a link to its card.

## Style

Editorial rather than dashboard: generous whitespace, one accent colour plus red for leakage and amber
for warnings, module labels in small uppercase so they read as schematic. Glossary terms only; no
"component", "service", "layer", or "wrapper" where module is meant.
