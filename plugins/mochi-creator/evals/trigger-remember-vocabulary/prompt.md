---
description: "Retention vocabulary the description claims (\"so I remember\") should reach the skill without the user saying \"Mochi\" or \"flashcard\". The content is inline on purpose — a prompt pointing at an unattached document tests attachment handling, not triggering."
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---
We decided to version the API in the URL path rather than a header, because CDN caching
keys off the path, and to return 422 rather than 400 for validation errors.

Turn that into cards so I remember the rationale behind each choice. Draft them here
rather than creating them.
