---
name: explain-back
description: >
  Process information for real understanding and expose the illusion of clarity. Use when the user
  says "help me actually understand this", "test my understanding", "process what I learned", "quiz
  me on this", "am I fooling myself about X", "explain-back", "make sure I get this before I blog
  it", or after building/reading something they want to internalize. Makes the user explain from
  memory, grades against the real source, and teaches only after they attempt. Not for writing
  content for the user — this withholds answers on purpose.
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash, mcp__mochi-donut__list_decks, mcp__mochi-donut__create_cards]
---

# Explain-Back

## Goal

Defeat the illusion of clarity: the confident feeling of understanding something whose grasp is
full of gaps. Force the user to *generate* an explanation from memory, grade it against a real
answer key, and teach only after they attempt — so fluency never passes for understanding.

## Hard rule

**Never supply a gap's answer before the user has genuinely attempted it.** The withhold-until-
attempt gate is the entire point. Breaking it re-creates the illusion this skill targets.

## Workflow

1. **Resolve settings.**

   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_config.py
   ```

   Gives `mochi_deck`, `session_dir`, `follow_references`, `strictness`, `card_cap`.

2. **Set topic + source.** Ask what is being processed and locate the artifact (repo, draft,
   article, note). If `follow_references` is true, note references the source points to for step 3.

3. **Build the answer key — privately.** Read the source and (if `follow_references`) its
   references, and integrate your own domain knowledge into the complete picture. Do NOT reveal it.
   The source artifact outranks your own knowledge; mark any knowledge-only claims as
   lower-confidence (see `references/friction-signals.md`).

4. **User explains from memory.** Prompt: "Explain this to me from memory, no looking. Teach it to
   me cold." Do not hint.

5. **Grade against the answer key.** Identify gaps using the friction signals — vague phrases,
   broken cause→effect chains, restating outcomes instead of mechanisms — plus anything from the
   source/references they omitted or got wrong.

6. **Per gap, apply strictness:**
   - `struggle-then-teach` (default): name the gap, have them attempt it; only after a genuine
     attempt supply the missing mechanism; then have them **re-explain it back** in their words.
   - `pure-examiner`: name the gap and withhold entirely; they re-derive or go read, then explain
     again. Do not teach.

7. **Outputs.**
   - **Mochi cards:** for each closed/confirmed gap (up to `card_cap`), write a card via the Mochi
     MCP into `mochi_deck`. List decks with `mcp__mochi-donut__list_decks` first; if `mochi_deck`
     is empty, ask which deck. If the Mochi MCP is unavailable, skip cards and say so — do not fail
     the session.
   - **Session record:** write a resumable record to `{session_dir}` using
     `assets/session-record-template.md`, filling topic, source, the user's explanation, gaps,
     what was taught, confirmed understanding, and still-open gaps.

8. **Verify:** before closing, confirm each "closed" gap was re-explained by the user, not just
   explained at them. Still-open gaps stay logged as the resume handle.

## Modes

- **Standalone** (default): process anything built or read.
- **Quiz:** point at an existing draft/concept; run the same loop to interrogate it.
- **Blog-gate:** when invoked before drafting a post, the user's confirmed explanation is the raw
  material for the draft. (The `blog-publish` hook itself is a future increment.)

See `references/friction-signals.md` for grading heuristics, answer-key construction, and card rules.

## Additional Resources

- `scripts/resolve_config.py` — resolves plugin settings.
- `references/friction-signals.md` — grading heuristics and protocol.
- `assets/session-record-template.md` — resumable session-record template.
