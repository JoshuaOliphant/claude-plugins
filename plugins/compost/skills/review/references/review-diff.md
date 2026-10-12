# Review the diff in a browser

Opens the change in a local browser so the user can leave inline, merge-request style comments,
then reads those comments back. The page is self-contained: no CDN, no scripts from elsewhere, no
telemetry. The scripts are stdlib-only, so they run with `python3` and need no environment.

What it shows is chosen automatically:

- With **uncommitted changes**, the working tree against `HEAD`, untracked files included.
- With a **clean tree**, the committed branch against its base (the merge-base with `origin/main`,
  falling back to `main`), the same diff a pull request shows.
- When the user names a base ("review against `origin/develop`"), pass `--base <ref>`.

The server prints contract lines: `Mode: <what is shown>`, `Diff review server: <url>`,
`Review file: <path>`, and `PID: <pid>`. Parse those rather than building paths or ports yourself.
The review file lives in a temp dir, so it never shows up as an untracked file in the repo.

## Steps

1. **Launch the server in the background** from the repo being reviewed, and poll its log until it
   reports a result. Add `--base <ref>` when the user named one.

   ```bash
   LOG=$(mktemp)
   nohup python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_diff/serve.py" --path "$(pwd)" > "$LOG" 2>&1 &
   for _ in $(seq 1 60); do
     grep -qE 'Diff review server:|NO_CHANGES|^Error:' "$LOG" && break
     sleep 0.5
   done
   cat "$LOG"
   ```

   - `NO_CHANGES`: there is nothing to review (no uncommitted changes and no commits ahead of the
     base). Say so and stop.
   - An `Error:` line (not a git repository, a bad `--base` ref, a repo with no commits): relay it
     and stop. It does not mean there are no changes.
   - Otherwise keep the `Mode:`, `Review file:`, and `PID:` values for the later steps.

2. **Tell the user what is shown** (from `Mode:`) and end your turn: they click a line to comment,
   add an overall summary if they like, click **Submit review**, and tell you when they are done.

3. **When they say they are done,** read the file at the `Review file:` path.

4. **Work through it.** The `summary` first, then each comment, located by its `file`, `line`,
   `side`, and `code`. Ask about any comment that is ambiguous rather than guessing.

5. **Stop the server** with the captured PID: `kill <PID> 2>/dev/null || true`.

## No display

Write a standalone page instead and give the user its path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_diff/serve.py" --path "$(pwd)" --static /tmp/review.html
```

Submitting from that page downloads `review.json`; the user tells you where they saved it.
