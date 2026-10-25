---
name: learn-setup
description: >
  Bootstrap a learning harness for one subject. Use when the user says "set up a learn harness",
  "make this project my learning project for <subject>", "start learning <subject> with the
  harness", or when learn-session finds no learn root. Creates the learn root (doctrine, graph,
  sessions, ledger), writes the profile, curriculum, frontier and feedback records, and drafts the
  project instructions header. One subject per project.
---

# Learn setup

## Goal

A project (or folder) where `learn <goal>`, `practice` and `field <scenario>` work from the first
message, with the subject layer kept separate from the subject-neutral doctrine.

## Hard rules

- **Never overwrite** an existing learn root, ledger, graph file or record. Report what exists and
  stop or merge with the user's OK.
- **The doctrine stays subject-neutral.** Subject content goes in the curriculum record and the
  instructions header only.
- **Propose, then write.** Show the user the drafted curriculum and instructions header before
  writing records, unless they already approved the shape.

## Workflow

1. **Locate the host.** In a Claude project the learn root is `/mnt/project-files/learn/` and the
   four records go in project memory. Elsewhere the learn root is `learn/` and the records are
   files in it. Check for an existing learn root first.
2. **Pin the subject**, one question per turn: the subject, why the user wants it (a talk, a role,
   a project), and any sources that inspired it. Fetch and read those sources; cite them.
3. **Draft the subject layer.**
   - Curriculum: 5 to 9 strands, each with a slug (its `graph/<slug>.md`), the source it comes
     from, and a rough goal state. Mark which strands are your additions. Mark the whole map a
     hypothesis until the first probe.
   - Profile: background to bridge from, answer format, voice rules, timing. Ask only what you
     can't find in what the user or host already says about them.
   - Instructions header from `assets/instructions-template.md`.
4. **Write the learn root**: copy `${CLAUDE_PLUGIN_ROOT}/skills/learn-session/references/doctrine.md`
   to `HARNESS.md`, and create `graph/`, `sessions/` and an empty `ledger.jsonl`.
5. **Write the records** from `assets/records-template.md`: profile, curriculum, frontier (seeded
   with the first session), session-feedback.
6. **Hand over** the instructions header for the user to paste into project settings (or a
   CLAUDE.md for a folder), and propose the first session: a probe-only Lesson that brackets every
   strand and writes the first frontier. Optionally propose a twice-weekly Practice routine at a
   time the user picks.
