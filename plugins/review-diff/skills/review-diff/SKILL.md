---
name: review-diff
description: Use when the user asks to "review this", "review the diff", "review my changes", "review my branch", "review against main", "open a review", or runs /review-diff. Opens the diff in a local browser for MR-style inline commenting — uncommitted changes if there are any, otherwise the committed branch vs its base — then reads the submitted comments back and addresses them.
---

# review-diff

Open changes in a local browser so the user can leave inline comments like a
merge-request review, then work through that feedback.

**Two modes, chosen automatically:**
- If the working tree has **uncommitted changes**, it reviews those (working-tree vs HEAD, including untracked files).
- If the working tree is **clean**, it falls back to reviewing the **committed branch vs its base** (merge-base with `origin/main`, falling back to `main`) — the same diff a GitLab/GitHub MR shows. This makes "review this" work on a branch you've already committed and pushed.
- To force a specific base, pass `--base <ref>` (e.g. the user says "review against `origin/develop`").

This uses a soft-wait model: launch the server in the background, tell the user,
end your turn. The user reviews at their own pace and tells you when they are done.

**Do not reconstruct paths or ports yourself.** The server prints contract lines —
`Mode: <what is being shown>`, `Diff review server: <url>`, `Review file: <path>`,
`PID: <pid>`. Parse those. The review file deliberately lives in a temp dir (not the
repo), so it never shows up as an untracked file in the next review.

The scripts are stdlib-only — run them with `python3` directly, no venv needed.

## Steps

1. **Launch the review server in the background** from the repo the user is working
   in, then poll the log until it reports a result:

   If the user named a base to compare against, add `--base <ref>` to the command.

   ```bash
   LOG=$(mktemp)
   nohup python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serve.py" --path "$(pwd)" > "$LOG" 2>&1 &
   for _ in $(seq 1 60); do
     grep -qE 'Diff review server:|NO_CHANGES|^Error:' "$LOG" && break
     sleep 0.5
   done
   cat "$LOG"
   ```

   - If the log shows `NO_CHANGES`, tell the user there are no changes to review (no
     uncommitted changes and no commits ahead of the base) and stop.
   - If it shows `Error: ... is not a git repository`, tell the user and stop.
   - Otherwise read the `Mode:` line (so you can tell the user what's being shown),
     and the `Review file:` path and `PID:` value, and remember them for steps 3 and 5.

2. **Tell the user** what's being reviewed (from the `Mode:` line), then end your turn:

   > "I've opened the diff in your browser (showing _<the Mode, e.g. 'this branch vs
   > main' or 'your uncommitted changes'>_). Click a line to comment, add an overall
   > summary if you like, then click **Submit review**. Come back and tell me when
   > you're done."

3. **When the user says they're done**, read the review file at the `Review file:`
   path captured in step 1.

4. **Work through the feedback.** Address the `summary` first, then each comment.
   Locate each comment's target using `file` + `line` + `side` + `code`. If a
   comment is ambiguous, ask the user rather than guessing.

5. **Kill the server** when you're finished, using the captured PID:

   ```bash
   kill <PID> 2>/dev/null || true
   ```

## No browser / headless

If the user has no display, generate a standalone page instead and give them the path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serve.py" --path "$(pwd)" --static /tmp/review.html
```

They open `/tmp/review.html`, submit (which downloads `review.json`), and tell you
where they saved it so you can read it.
