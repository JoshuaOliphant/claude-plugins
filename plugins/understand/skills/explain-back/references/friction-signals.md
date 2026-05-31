# Friction Signals and Protocol

Detailed procedure for the `explain-back` skill.

## Building the answer key

Construct the most complete reference available, in this priority:

1. **The source artifact** (repo, draft, article) — the ground truth. When it conflicts with your
   own knowledge, the artifact wins.
2. **References the source points to** (when `follow_references` is true) — read linked materials.
3. **Your own domain knowledge** — fill conceptual gaps the source assumes but does not state.

Mark claims that rest only on your own knowledge (not the artifact) as lower-confidence. If you are
unsure whether the user is wrong or you misread the source, re-read the source before flagging it —
do not mark the user wrong on a claim you cannot ground in the artifact.

## Friction signals (what a gap looks like)

- **Vague phrases** — "it just handles that", "somehow", "magic", hand-waving over a step.
- **Broken cause→effect** — the explanation jumps from A to D without B and C.
- **Outcomes restated as mechanisms** — describing *what* happens instead of *how/why* it happens.
- **Omissions vs. the source** — a component, step, or constraint present in the artifact but
  missing from the explanation.
- **Wrong claims** — contradicts the artifact (not merely your own knowledge).

## Struggle-then-teach protocol (per gap)

1. Name the gap precisely. Do not supply the answer.
2. Prompt the user to attempt it ("what do you think happens between B and D?").
3. Only after a genuine attempt, supply the missing mechanism — concise, mechanism-first.
4. Have the user **re-explain it back** in their own words. This is the second generation pass and
   is required to mark the gap closed.
5. If they cannot re-explain, the gap stays open — log it, do not paper over it.

`pure-examiner` strictness: do steps 1–2 only, then withhold entirely; the user re-derives or reads
and explains again. Never teach in this mode.

## Mochi cards

- One card per closed/confirmed gap, up to `card_cap`. If gaps exceed the cap, choose the most
  load-bearing and say which were dropped.
- Follow effective-prompt principles: focused (one idea), precise, effortful (the answer should
  require recall, not recognition). Prefer mechanism questions ("why does X cause Y?") over
  fact-lookup.
- Write into `mochi_deck`. If empty, ask which deck (list via the Mochi MCP). If the MCP is
  unavailable, skip and report — never fail the session over cards.

## Verification checklist (before closing)

- Was every "closed" gap re-explained by the user in their own words? If not, it is still open.
- Are still-open gaps recorded in the session file as the resume handle?
- Were cards capped and the dropped ones named?
