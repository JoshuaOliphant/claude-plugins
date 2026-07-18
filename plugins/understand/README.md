# understand (v0.2.0)

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

The plugin **bundles** the [`mochi-donut`](https://github.com/JoshuaOliphant/mochi_donut) MCP
server via `.mcp.json`, so installing the plugin registers it automatically. It exposes:

- `fetch_url(url, format?)` — fetch a URL and convert it to clean markdown via JinaAI Reader
- `list_decks()` — list all Mochi decks with their IDs
- `create_cards(deck_id, cards)` — create one or more flashcards in a deck
- `list_cards(deck_id?, limit?, bookmark?)` — list cards, optionally filtered by deck, paginated via bookmark
- `get_card(card_id)` — fetch one card's full content, deck, and tags
- `update_card(card_id, content?, deck_id?, manual_tags?, archived?, trashed?)` — edit, move, tag, archive, or soft-delete a card
- `create_deck(name, parent_id?)` — create a deck (optionally nested under a parent)
- `update_deck(deck_id, name?, parent_id?, archived?)` — rename, re-parent, or archive a deck
- `add_attachment(card_id, file_path, filename?)` — upload an image attachment (png/jpg/jpeg/gif/svg/webp) to a card, referenced in card content as `![](@media/<filename>)`

You need:

- **`uv`** installed — the server is launched with `uvx` from the public repo.
- **`MOCHI_API_KEY`** set in your environment — the mochi-donut server reads it to call the Mochi API.

Without `MOCHI_API_KEY`, the explain-back ritual still runs; only the card-writing step is skipped.

```bash
/plugin install understand@oliphant-plugins
export MOCHI_API_KEY="your_api_key_here"
```
