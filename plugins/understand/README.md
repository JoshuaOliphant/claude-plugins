# understand (v0.1.0)

Process information for real understanding — an antidote to the illusion of clarity (the confident
feeling of understanding something whose grasp is actually full of gaps).

## Skill

- **explain-back** — Names a topic and source, builds a complete answer key privately (source +
  references + model knowledge), has you explain from memory, grades against the answer key, and
  runs **struggle-then-teach** per gap: it withholds the answer until you attempt, then teaches,
  then has you re-explain it back. Outputs **Mochi cards** for each gap and a **resumable session
  record**.

## Modes

- **Standalone** — process anything you built or read.
- **Quiz** — point it at an existing draft or concept and be interrogated.
- **Blog-gate** — run it before drafting a post so the draft is built from *your* explanation.

## Configuration

Optional `.claude/understand.local.md` (project or user level):

```markdown
mochi_deck: Learning
session_dir: ~/vault/areas/learning/sessions/
follow_references: true
strictness: struggle-then-teach
card_cap: 10
```

Defaults: `session_dir` `understand-sessions/`, `follow_references` true, `strictness`
`struggle-then-teach`, `card_cap` 10.

## Requirements

- Mochi MCP (`MOCHI_API_KEY`) for card output. Without it, the ritual still runs; cards are skipped.

```bash
/plugin install understand@oliphant-plugins
```
