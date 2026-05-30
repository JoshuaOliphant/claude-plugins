<!-- ABOUTME: Strategy/design note for closing the compound-knowledge engine's missing "improve" stroke. -->
<!-- ABOUTME: Diagnosis + design for one reservoir and a graduate/refresh ritual; sequenced, not yet implemented. -->

---
title: Closing the Compound Engine — the missing "improve" stroke
date: 2026-05-30
status: design
tags: [compound-engineering, compound-knowledge, plugins, vault, strategy]
---

# Closing the Compound Engine

A strategy note, not an implementation plan. It names why the plugin marketplace
doesn't *feel* like it compounds, locates the single missing piece, and designs the
smallest change that closes the loop. Built from a brainstorm against Every's
[Compound Engineering guide](https://every.to/guides/compound-engineering) and the
ground truth of the `compound-knowledge` plugin.

## 1. The itch

In La Boeuf's words:

- "I don't find myself using my own plugins from the marketplace that much."
- "I capture all knowledge in my vault."
- "I don't use the knowledge I capture to reinforce and feed back into the plugins I have."

The felt problem is a one-way street: knowledge flows *into* the vault every day and
never flows back out to make the tools better.

**The bet this whole design rests on:** the reason the plugins go unused is that they
don't benefit from accumulated knowledge, so the vault's bespoke skills always feel
sharper. Make captured knowledge visibly improve the tools and the living context, and
they become worth reaching for. That is an assumption, not a certainty — the honest risk
is polishing tools that still sit on the shelf. **What would tell us the loop actually
closed:** vault-captured lessons producing a steady trickle of concrete `CLAUDE.md` /
`AGENTS.md` / plugin edits in the first few weeks, and at least one instance of reaching
for a plugin *because* it now carries a lesson it didn't before.

## 2. Diagnosis

**The vault compounds. The plugins don't.** Knowledge accumulates daily (close-day,
compound-capture, the wiki layer) and then stops. It never returns to improve the
plugins, so they stay generic while the vault gets smarter — which is exactly why the
vault's bespoke skills always feel more useful than the marketplace plugins.

Underneath sit **two separate capture systems that don't know about each other**:

| | Fed by | Writes to | Status |
|---|---|---|---|
| Vault capture | close-day, compound-capture, wiki | `knowledge/solutions/` (281 files) | Active daily |
| Plugin feedback | correcting a plugin *while using it* | plugin-local state → SKILL.md | Dormant |

The vault reservoir is fed constantly but never reaches the plugins. The plugin
feedback skill *would* reach the plugins, but it only fires when a plugin is used —
which seldom happens. That is the **chicken-and-egg**: the plugins aren't used, so no
knowledge about them accumulates, so they don't improve, so they aren't used.

The vault's `knowledge/solutions/` *already holds plugin-relevant lessons* (the plugin
deploy flow, the `installed_plugins.json` trap, damage-control gotchas). They sit in the
vault where nothing routes them back to the tools they describe.

## 3. What already exists (the gap is precise)

The engine is more built than the itch suggests. Two of its three strokes are strong:

- **Capture** — `compound-capture` writes structured YAML-frontmatter solution files.
- **Retrieve** — `compound-retrieve` does tiered search: grep on frontmatter **plus**
  semantic `vault-recommender --topic` queries when the reservoir is an Obsidian vault.
  It also federates across projects via `~/.claude/compound-knowledge-registry.md`.
- **Configurable reservoir** — `/compound-knowledge:setup [path]` already points the
  reservoir at a project-local `knowledge/solutions/` or a custom path (e.g. a shared
  second brain). The public-configurability requirement is largely met.

So capture and retrieve are configurable, semantic, and cross-project. They are also
**invisible plumbing** — they do their work without showing it. The only missing stroke,
**improve**, is the one that produces *visible* payoff (better plugins, better living
context). Its absence is why the system never feels like it compounds.

```
capture  →  [reservoir]  →  retrieve  →  ...work...  →  ⌀
   ↑__________________________________________________|
                  improve (missing edge)
```

### The full loop, mapped across both systems

Every's loop has eight steps (ideate, brainstorm, plan, work, review, polish, compound,
plus the improve edge). The roadmap doc called ideate/brainstorm/polish "no owner" — but
that read *only the marketplace*. Across **both** systems, most cells are already filled:

| Loop step | Where it lives for La Boeuf today | Strength |
|---|---|---|
| Ideate | Vault: `/second_brain_analyze ideas`, monthly-heartbeat, capture | owned (vault) |
| Brainstorm | Vault + superpowers `brainstorming` skill | owned (vault) |
| Plan | `autonomous-sdlc` architect / superpowers `writing-plans` | owned (marketplace) |
| Work | `autonomous-sdlc` builder + worktree isolation | owned (marketplace) |
| Review | `autonomous-sdlc` validator (thin) / `/code-review` | partial |
| Polish | `verify` / `run` skills | partial |
| Compound — capture/retrieve | `compound-knowledge` (configurable, semantic, cross-project) | strong |
| **Improve** | **— nothing —** | **empty** |

The unification story falls out of the table: **the vault owns the front of the loop**
(ideate, brainstorm), **the marketplace owns the middle** (plan, work, review, polish), and
**`compound-knowledge` is the spine meant to run through both**. Ideate and brainstorm only
*looked* missing because the marketplace was viewed in isolation; for this user they already
work. The one genuinely empty cell is **improve** — which is why this design targets it and
nothing else. Review and polish are "partial," but they are downstream concerns parked with
Move B's marketplace-wiring (Section 6), not part of completing the engine.

## 4. The design: one reservoir + one ritual

Confirmed against Every's guide. The guide's **step 7 ("Compound")** is exactly this
stroke: *capture the solution → make it findable → **update the system** (add patterns to
`CLAUDE.md`/`AGENTS.md`, create new agents) → verify the system would catch it next time.*
And `/ce-compound-refresh` is the corpus-gardening pass (keep / update / merge / replace /
archive). The reference plugin already speaks this vocabulary.

One move is load-bearing; the second is prerequisite plumbing that waits for usage.

### Move A — Add the `improve` stroke (load-bearing)

This is the single move that breaks the chicken-and-egg, because it draws on the vault
reservoir that is *already full and fed daily* — it doesn't depend on the plugins being
used first. A new skill in `compound-knowledge` (working name `compound-graduate`, with a
`refresh` mode) that reads the *same configured reservoir* the other two strokes use, and
has two faces:

- **Promote** (the visible payoff, build first) — scan the reservoir for lessons aimed at a
  target; turn them into concrete edits to that target's living context (`CLAUDE.md` /
  `AGENTS.md`), elevate broadly-useful ones into `critical-patterns.md`, and create a new
  agent/skill when a pattern warrants it. Close with the guide's verification question:
  *would the system catch this next time?* **Primary promote fuel is the synthesized wiki**,
  not just raw solution files: `wiki/theses/` already holds distilled beliefs with confidence
  markers (`[solid]`, `[evolving]`), and a `[solid]` thesis is exactly the kind of position
  worth promoting into living context — pre-distilled, unlike individual lessons.
- **Garden** — find stale, duplicate, overlapping, or obsolete entries and decide
  keep / update / merge / replace / archive. This keeps retrieval precision from rotting as
  the corpus grows (the roadmap's G3).

Built to the same bar as the existing strokes: configurable reservoir, grep +
vault-recommender to find clusters of related lessons, cross-project aware.

### Move B — Collapse the two capture systems into one (prerequisite plumbing)

Redirect each plugin's `feedback` skill to write into the *same configured reservoir*
(tagged with a `target:` frontmatter field naming the plugin or context file) instead of
plugin-local state. **Note the dependency:** the diagnosis in Section 2 says plugin
feedback is dormant *because the plugins aren't used* — so there is little feedback to
redirect today. Move B's payoff is forward-looking: it ensures that once usage picks up
(driven by Move A making the tools better), every correction lands in the one reservoir the
`improve` stroke already mines, instead of in per-plugin state the stroke can't see. It is
foundational, not the thing that closes the loop now. Build it after Move A's promote face
has proven the stroke.

## 5. Architecture details

- **Reservoir path config already exists** (verified). `compound-retrieve` resolves the
  solutions directory by first match: `{project_root}/.claude/compound-knowledge.local.md`
  (`solutions_path` key), then `~/.claude/compound-knowledge.local.md`, then default
  `{project_root}/knowledge/solutions/`. The `improve` stroke reads this same config — no
  new mechanism needed for Move A. **But plugin feedback is stored separately**, via
  `feedback_manager.py` per-plugin, *not* through `solutions_path`. That split is precisely
  why Move B needs real plumbing: redirecting feedback into the reservoir means routing it
  through the `solutions_path` config instead of the per-plugin store.
- **Read and write paths configured independently** (design refinement). Generalize the
  single `solutions_path` into two settings:
  - `write_path` — where capture puts new structured lessons. Default `knowledge/solutions/`.
    Stays a clean, frontmatter-schema'd directory so promote/garden have reliable input.
  - `read_paths` — the corpus that retrieve and the promote face sweep. Defaults to
    `write_path`; can add `wiki/`, `journal/`, or other high-signal areas.
  Keep `solutions_path` as a backward-compatible alias meaning both, so existing installs
  and single-dir users are unaffected. The semantic layer points at `vault_root` regardless,
  so `vault-recommender` already reads the whole vault.
  **Principle: read wide, write structured** — capture stays narrow and schema'd while
  retrieval and promotion draw on the whole vault, especially the synthesized wiki.
- **`target:` frontmatter tag** routes a lesson to its destination: a plugin name
  (improve that plugin's SKILL.md), `claude-md` / `agents-md` (promote to living context),
  or `general` (stays a retrievable solution). The promote face filters by `target`.
- **Living-context target is tool-aware.** The generic plugin promotes to `CLAUDE.md` *or*
  `AGENTS.md` depending on the host tool. In this repo the always-read file is `AGENTS.md`;
  in the vault it is `CLAUDE.md`.
- **Tiered discovery.** Grep always works on any reservoir; semantic
  (`vault-recommender`) augments when the reservoir is a vault. Mirrors the existing
  `vault-search` skill and `compound-retrieve`.
- **Verify the learning.** Each promotion ends by asking whether the now-updated system
  would catch the issue automatically next time — the guide's completeness check.

## 6. Sequencing

1. **First brick — promote to living context.** Build the `target: claude-md` / `agents-md`
   promotion path first. It is the cheapest, most visible graduation and proves the stroke.
2. **Then — unify feedback storage (Move B).** Redirect plugin feedback skills into the
   reservoir with `target:` tags.
3. **Then — garden mode.** Add the refresh/prune face once there is enough corpus to rot.
4. **Parked (downstream) — wire the marketplace to call the engine.** Have
   `autonomous-sdlc`'s architect retrieve before planning and capture after; add a
   learnings-researcher reviewer (the roadmap's P1/G1, and the guide's review agent). This
   only pays off once the loop is closed *and* those plugins are reached for daily, so it
   waits.

## 7. Housekeeping (minor)

The vault is *not* stale — it runs `compound-knowledge` **0.7.0** (verified via the
version-stamped plugin cache), the current engine. The only real drift is the manifest:
`marketplace.json` advertises **0.5.0** while the plugin's own `plugin.json` says **0.7.0**.
Reconcile `marketplace.json` to 0.7.0 so the marketplace listing stops lying. Small, but
it is the kind of inconsistency the `garden` face should eventually catch automatically.

## 8. Ladder positioning

Per the guide's five-stage maturity ladder, the `improve` stroke is what moves the *system
of plugins* up a rung: it is the "teach the system, don't do the work yourself" investment
(the 50% half of the 50/50 rule). The marketplace currently reads as five separate tools;
closing this loop makes `compound-knowledge` the meta-engine the others plug into, which is
the unifying story.

## 9. Open questions

- **`target:` taxonomy** — fixed set (plugin names + `claude-md` / `agents-md` / `general`)
  or free-form with a normalizer? Start fixed; widen if it chafes.
- **Promotion autonomy** — does promote propose-then-apply (write the CLAUDE.md edit and
  show a diff) or apply-then-log? Living context is high-trust; lean propose-then-apply for
  context edits, auto-apply for `critical-patterns.md` elevation.
- **Feedback migration** — is there existing plugin-local feedback worth migrating into the
  reservoir, or start clean from the redirect point?
- **Cross-repo reach** — should promotion be able to edit a *different* repo's context file
  (vault lesson → marketplace `AGENTS.md`), or stay within the reservoir's own project and
  rely on the registry? Likely the latter to start.
- **Wiki synthesis loop** — the wiki is both a promote *source* and a `wiki-ingest`
  *output*. If promote mines `wiki/theses/` into `CLAUDE.md` while `wiki-ingest` keeps
  synthesizing the wiki, ensure the two don't double-synthesize or feed back on each other
  (e.g. promote reads theses but never writes them; only `wiki-ingest` writes the wiki).
