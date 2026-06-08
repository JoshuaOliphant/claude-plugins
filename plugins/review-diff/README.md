# review-diff

Local web-based diff review for Claude Code. Opens your working-tree changes in a
browser, lets you leave inline comments like a merge-request review, and feeds the
comments back to the Claude Code session you're working in.

## Install

This plugin lives in the `oliphant-plugins` marketplace. If you haven't added the
marketplace yet:

```shell
/plugin marketplace add joshuaoliphant/claude-plugins
```

Then install:

```shell
/plugin install review-diff@oliphant-plugins
```

The scripts are Python stdlib-only — no `uv sync` or package install is needed at
runtime (just Python 3.11+ and `git`). The `Development` section below covers the
dev toolchain (used for tests / type-checks).

## Usage

Ask Claude to "review this" (or run `/review-diff`) after it has made changes.
Claude opens the diff in your browser. Click any line to attach a comment, add an
optional overall summary, then click **Submit review** and tell Claude you're done.
Claude reads your comments and works through them.

The page has a **file-tree sidebar** for navigation (click a file to jump to it,
with per-file `+/−` line stats and a badge showing how many comments it has),
**collapsible file diffs** with a Collapse all / Expand all control, and a
scroll-spy that highlights the current file as you scroll. Saved comments stay
visible inline as a "✓ Saved" row — click one to edit or remove it.

**What gets reviewed (chosen automatically):**

- If you have **uncommitted changes**, it reviews those (working tree vs `HEAD`,
  including untracked files).
- If your working tree is **clean**, it falls back to reviewing the **committed
  branch vs its base** (merge-base with `origin/main`, falling back to `main`) — the
  same diff a GitLab/GitHub MR shows. So "review this" works on an already-committed,
  pushed branch too.
- Ask Claude to "review against `<ref>`" to force a specific base.

### Advanced

- **Force a specific base** when both modes would apply: say "review against
  `origin/develop`" (the skill passes `--base <ref>` to the server).
- **Headless / no-browser mode**: run

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serve.py" --path "$(pwd)" --static /tmp/review.html
  ```

  to produce a standalone HTML file instead of starting a server. Open it,
  submit your review, and the page downloads `review.json` for you to drop back
  to Claude. Useful on machines without a display or when the browser
  integration is locked down.

## How it works

- `scripts/collect.py` — runs `git diff --no-prefix HEAD` plus untracked files
  (working-tree mode), or `git diff --no-prefix <base>...HEAD` (branch mode), and
  produces a structured diff. `resolve_base()` picks the default base ref.
- `scripts/serve.py` — a stdlib-only HTTP server that embeds the diff into
  `scripts/viewer.html`, opens it in your browser, and saves submitted comments to a
  per-repo `review.json` in a temp dir (kept out of your repo).
- `skills/review-diff/SKILL.md` — drives Claude: launch → wait → read `review.json` →
  address comments → stop the server.

No third-party runtime dependencies — just Python 3.11+ and `git`.

## Privacy & safety

- **Offline** — the page is fully self-contained: no CDN fonts, no external
  scripts, no telemetry. It works on a locked-down work machine.
- **Local only** — the server binds to `127.0.0.1` (never `0.0.0.0`).
- **XSS-safe embedding** — diff data is HTML-escaped before being inlined into
  the page's `<script>` block, so a reviewed file containing `</script>` cannot
  break out and inject markup into the reviewer's browser. Covered by a
  regression test.
- **Review file stays out of your repo** — `review.json` is written to a per-repo
  temp directory (keyed by a hash of the repo root), not the repo itself, so it
  never reappears as an untracked file in the next review.

## Development

```bash
cd plugins/review-diff
uv sync
uv run pytest            # 100% line coverage gate
uv run ruff check . && uv run ruff format --check . && uv run ty check
```
