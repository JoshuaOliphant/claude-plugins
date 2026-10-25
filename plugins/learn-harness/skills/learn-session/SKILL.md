---
name: learn-session
description: >
  Run one learning session under the learn-harness doctrine. Use when the user says "learn <goal>",
  "teach me <topic>", "practice", "practice <topic>", "quiz me from my graph", "field <scenario>",
  "role-play a stakeholder so I can practice discovery", or opens a thread in a learn-harness project.
  Lesson probes the learner's edge, plans a minimal tree, then teaches one checked step per turn;
  Practice trains retrieval; Field grades an artifact against a pre-committed rubric. Not for
  answering a quick question: this withholds and checks on purpose.
---

# Learn session

## Goal

Move the learner's understanding, availability or judgment on one goal, and leave the records
updated so the next session starts where this one ended.

## Hard rules

- **One question per turn, then end the turn.** The answer decides the next question.
- **Never build on a step the learner hasn't demonstrated.** A miss means repair first.
- **Commit before you ask.** Every graded question, problem and Field rubric has its answer
  written to the session log before the learner sees the question.
- **Never put a graded question on a card or picker that marks a recommended option.**
- **Close out every session**, including abandoned ones.

## Workflow

1. **Find the learn root.** `/mnt/project-files/learn/` in a Claude project, else `learn/` in
   the working directory. No learn root: offer `learn-harness:learn-setup` and stop.
2. **Read the doctrine.** Prefer the project's `HARNESS.md` (it may carry local edits); fall back
   to `references/doctrine.md`. Read all of it.
3. **Read the records**: profile, frontier, session-feedback, curriculum (memory or files, per the
   doctrine's Records paragraph), plus the `graph/` files relevant to the goal.
4. **Pick the session type** from the request: Lesson, Practice or Field (doctrine section 1).
   Ambiguous: start a Lesson and say so.
5. **Open the session log** from `assets/session-log-template.md` at
   `sessions/<YYYY-MM-DD>-<slug>.md`. Keep it current every turn.
6. **Run the session** per the doctrine: Lesson section 3, Practice section 4, Field section 5,
   with section 2 governing every question and section 6 the voice.
7. **Close out** per doctrine section 7: log, graph, ledger, frontier. Re-read each shared file
   right before writing it. Attach or link the session log in the closing message.

## Answer format to ask for

`answer / confidence % / thinking`. Thinking is the primary data, often dictated: read it
leniently for transcription noise and fully for the model it reveals.
