<!-- ABOUTME: Design for the `understand` plugin — an anti-illusion-of-clarity ritual that forces real understanding. -->
<!-- ABOUTME: Public, configurable Claude Code plugin; explain-from-memory, grade against a real answer key, struggle-then-teach. -->

---
title: The `understand` plugin — process for real understanding
date: 2026-05-30
status: design
tags: [learning, understanding, mochi, spaced-repetition, plugins, anti-illusion-of-clarity]
---

# The `understand` Plugin

A public, configurable Claude Code plugin whose skill runs an anti-illusion-of-clarity
ritual: it makes the user *generate* an explanation from memory, grades it against a real
answer key, and refuses to let fluency pass for understanding. Built from a brainstorm
against Ness Labs' [The Illusion of Clarity](https://nesslabs.com/illusion-of-clarity).

**Working name:** `understand` (plugin), primary skill `explain-back`. Naming is changeable.

## 1. The problem

The illusion of clarity is the confident feeling of understanding something whose grasp is
actually full of gaps. The article names three causes: **shallow mental models**, **familiarity
masquerading as understanding** (processing fluency feels like comprehension), and **outsourcing
knowledge to external systems** (the "Google Effect"). The antidote is the **generation effect**:
explain a concept from memory with no external resources, then hunt for friction points (vague
phrases, broken cause→effect chains, restating outcomes instead of mechanisms).

For La Boeuf this is acute and specific. His `project_learning_system` strategy is
Build → Blog → Mochi, betting that "if you can blog it and Mochi-card it, you can speak to it."
But AI lets him build and *ghost-write* faster than understanding consolidates. Having Claude
write a blog post in his voice is the **purest form of cause #3** (outsourcing), and reading it
back creates **cause #2** (familiarity). So the bet has a hole: a blogged post no longer proves
understanding. This plugin closes the hole — it makes "I processed it ⟹ I understand it" true by
forcing *him* to generate the explanation and exposing the gaps.

## 2. The bet and success criteria

**Bet:** Forcing generation (explain from memory) and grading against a real reference produces
durable understanding that ghost-written prose does not — and the friction is worth it.

**Success looks like:** sessions that surface gaps the user did not know they had; Mochi cards
seeded from *real* holes (not guessed-at ones); and the user able to speak cold to a topic they
have run through the ritual. **Failure mode to watch:** the skill quietly reverting into an
answer-giving machine (teaching before the user generates), which would re-create the very
illusion it targets.

## 3. The engine (core loop)

1. **Set topic + source.** The user names what they are processing; the skill locates the
   artifact (repo, draft, article, note).
2. **Build the answer key privately.** Read the source plus any references it points to, integrate
   the model's own domain knowledge, and form the complete picture — **without showing the user**.
   The reference is always source + references + model knowledge, integrated (no
   knowledge-only fallback; always enrich the source).
3. **User explains from memory.** No resources, no peeking. Teach it cold.
4. **Grade against the answer key.** Hunt the article's specific friction signals — vague phrases,
   broken cause→effect chains, restating outcomes instead of mechanisms — plus anything in the
   source/references the user omitted or got wrong.
5. **Struggle-then-teach, per gap.** Name the gap and **withhold the answer**. The user attempts
   it first. Only after a genuine attempt does the model supply the missing mechanism. Then the
   user **re-explains it back** in their own words — the second generation pass that proves the
   gap closed rather than just got explained at them.
6. **Loop** until gaps are closed or logged as still-open.

**Hard rule:** never supply a gap's answer before the user has genuinely attempted it. The
withhold-until-attempt gate is the discipline that keeps this from becoming a tutor.

## 4. Outputs

- **Mochi cards** via the Mochi MCP — one per gap/concept, seeded from real holes, written to a
  configurable deck. Follows the mochi-creator card-quality principles (focused, precise,
  effortful) where practical.
- **Resumable vault session record** — a markdown file capturing: topic, source, the user's
  from-memory explanation, gaps found, what was taught, confirmed understanding, and
  **still-open gaps**. Saved to a configurable directory so a session can be picked back up and
  re-reviewed. Open gaps are the resume handle.

## 5. Modes (all the same engine)

- **Standalone** (default, v1): process anything built or read.
- **Quiz** (v1): point the engine at an existing draft/concept and interrogate understanding of it.
- **Blog-gate** (documented v1, wired later): run before drafting a post so the draft is built
  from the user's explanation, not the model's knowledge. The `blog-publish` integration is a
  follow-up (see Scope).

## 6. Configurable settings (public but works for me)

Same "public default, personal override" pattern proven by compound-knowledge's reservoir config.
Settings (via a `.local.md`-style config or skill args):

- **Mochi deck** — name/id for generated cards.
- **Session-record directory** — where vault records are written (the user's vault is just their
  configured target).
- **Follow references** — whether to read links the source points to when building the answer key.
- **Strictness** — `struggle-then-teach` (default) or `pure-examiner` (withhold the answer entirely;
  the user must re-derive). The i/ii dial from the brainstorm.

## 7. Packaging

- **New plugin** in `claude-plugins`, distinct from `mochi-creator` (which it *uses* via the Mochi
  MCP, not duplicates).
- Form: a markdown `SKILL.md` orchestrating the interactive ritual, a session-record template
  (`assets/`), a config reader, and a references file for the friction-signal heuristics and the
  propose-then-teach protocol. No heavy code — it is an interactive procedure, like the vault's
  `close-day`. Mirrors the existing marketplace plugins' structure.
- **Dependency:** the Mochi MCP (`MOCHI_API_KEY`), same as `mochi-creator`. Cards are skipped
  gracefully (logged) if the MCP is unavailable, so the core ritual still runs.

## 8. Scope

**v1 builds:**
- The engine skill (`explain-back`): topic/source → private answer key → explain-from-memory →
  graded gap detection → struggle-then-teach with re-explain → outputs.
- Standalone + quiz modes (both are the engine pointed at different inputs — near-free).
- Mochi card output + resumable vault session record.
- Config: deck, record directory, follow-references, strictness.

**Deferred (follow-ups, not v1):**
- `blog-publish` wiring for the blog-gate mode (documented as a mode; the actual hook into the
  vault skill is separate).
- Auto-detecting "you just built/shipped something, want to process it?" triggers.
- Spaced re-prompting from still-open gaps (the engine writes them; a scheduler that resurfaces
  them is later).

## 9. Open questions

- **Naming** — keep literal `understand` / `explain-back`, or an evocative codename? (Public name
  should stay discoverable for triggering regardless.)
- **Session-record default location** — for the user's vault, a sensible default is
  `areas/learning/sessions/` or `knowledge/understanding/`; confirm on first run via the config.
- **Answer-key honesty for things the model gets wrong** — when grading a repo the model
  misreads, the user could be marked "wrong" while actually right. Mitigation: the source artifact
  outranks model knowledge in the answer key; flag model-knowledge-only claims as lower-confidence
  during grading.
- **Card volume** — cap cards per session (e.g. top N gaps) so a session does not flood the deck;
  make the cap configurable.
