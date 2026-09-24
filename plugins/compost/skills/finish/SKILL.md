---
name: finish
description: Integrates reviewed work by testing it against the branch it will merge into, opening or updating the pull request, and merging or discarding only on the user's word. Use when the user says "finish this", "wrap it up", "open the PR", "update the PR", "ready to merge", "merge it", "clean up the worktree", or "throw this branch away".
---

# Finish

Review is addressed and the branch is ready to leave its worktree. This skill proves the work
still holds once it meets the branch it merges into, writes the pull request so a reviewer can
audit every decision made without them, and cleans up after the merge. Merging into the default
branch is the user's decision, and so is throwing work away. Everything before that point is
yours to do without asking.

## Steps

1. **Confirm the branch is ready.** Every `compost:review` finding is fixed or answered on the
   issue with a `file:line` reason. `compost:verify` ran on the current HEAD. If commits landed
   after its last run, run it again first.

2. **Record where you are.** Capture these now, because cleanup runs from another directory:

   ```bash
   worktree_path=$(git rev-parse --show-toplevel)
   branch=$(git branch --show-current)          # empty on a detached HEAD
   main_root=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
   ```

   A detached HEAD means the harness manages this workspace. Push it as a named branch
   (`git push origin HEAD:refs/heads/<issue>-<slug>`) and leave the workspace in place.

3. **Name the merge target.** It is the branch this work forked from. Take it from the issue: a
   parent issue may name an integration branch for its sub-issues. Otherwise it is the default
   branch (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`). State it in the PR.

4. **Run the suite on the actual merge result.** A green branch proves only the branch. Build
   the merge in a throwaway worktree so neither branch moves:

   ```bash
   check="$main_root/.worktrees/merge-check-<issue>"
   git fetch origin
   git worktree add --detach "$check" origin/<target>
   git -C "$check" merge --no-ff --no-edit "$branch"
   ```

   Install dependencies there, run the full suite and the recorded gates, then
   `git worktree remove "$check"`. A conflict means the target moved:
   merge the target into your branch, resolve, and go back through `compost:verify`. Do not
   rebase a branch you have already pushed. A red merge result stops here and goes to
   `compost:diagnose`.

5. **Open or update the pull request.** Push the branch and open a draft PR against the target,
   or update the open one. The body has five sections: Goal, Decisions, Changes, Validation,
   Risk. Decisions summarizes the rulings posted as issue comments. Validation carries
   `compost:verify`'s evidence and the merge-result run. Risk names whatever is unproven,
   deferred, or excluded from coverage. End the body with a `Closes` line for the issue, or for
   the parent and every sub-issue (`Closes #12, closes #13, closes #14`), keeping any the PR
   already has. Use the
   [PR body template](references/pr-body.md) and the tracker's own CLI (`gh pr create --draft`,
   `gh pr edit`, `glab mr create --draft`). With a local tracker, post the same body on the
   issue file instead.

6. **Stop for the merge decision when the target is the default branch.** Report the PR link,
   the merge-result run, and three options: merge, keep the branch open for more feedback, or
   discard. Wait for the answer. A merge into an integration branch that is not the default
   branch does not need to wait; go on to step 7.

7. **Merge with a merge commit, then clean up.** When told to merge:
   - With an open PR, mark it ready with `gh pr ready <n>` (the forge refuses to merge a draft),
     then merge through the forge with a merge commit: `gh pr merge <n> --merge`. That is the
     forge's `--no-ff`. Never squash or rebase unless the user asks for it.
   - Without a PR, merge from the main checkout, never from inside the worktree:
     `git -C "$main_root" switch <target>`, `git -C "$main_root" pull --ff-only`, then
     `git -C "$main_root" merge --no-ff "$branch"`. Run the suite on the result. If it is red,
     stop with the branch and worktree in place and nothing pushed. If it is green, push the
     target.

   Then remove the worktree from `$main_root`. Use the harness's exit tool (such as
   `ExitWorktree` with remove) if it created the worktree; otherwise
   `git worktree remove "$worktree_path"`. If removal is refused because of uncommitted files,
   list them with `git -C "$worktree_path" status --porcelain -uall` and ask the user whether to
   commit, move, or delete them. Never add `--force` on your own. Delete the branch with
   `git branch -d "$branch"`, which refuses if the branch is not merged, and delete the remote
   branch. Pull the target in `$main_root` first so `-d` can see the merge.

8. **Discard only on request, and only after the user types "discard".** When the user asks to
   throw the work away, show what will be lost: the branch, the commits
   (`git log --oneline <target>..$branch`), the worktree path, and any open PR. Ask them to type
   `discard`. A paraphrase such as "yeah, get rid of it" is not the confirmation. Once the word
   arrives, close the PR, remove the worktree as in step 7, delete the branch with
   `git branch -D "$branch"`, and delete the remote branch.

9. **Capture what was learned.** If the work turned up a gotcha, a non-obvious root cause, or a
   verdict reached from measurement, and the compound-knowledge plugin is installed, use
   `compound-knowledge:compound-capture` to record it. When no `compost:implement` run worked this
   parent, tick the issue in its parent's checklist; otherwise implement already did.

## Next moves

- `compost:implement` when the parent issue still has unblocked issues.
- `compost:build` when review or the user asks for changes on the open PR.
- `compost:diagnose` when the merge result is red.
- `compost:pause` when stopping with the PR open and work still in flight.
