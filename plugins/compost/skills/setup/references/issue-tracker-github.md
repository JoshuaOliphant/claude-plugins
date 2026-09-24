# Issue tracker: GitHub

Specs, slices, and maps for this repo live as GitHub issues. Use the `gh` CLI for every operation;
it infers the repo from `git remote -v` when run inside a clone.

## Commands

- **Create:** `gh issue create --title "..." --label "..." --body-file -` with a heredoc body.
- **Read:** `gh issue view <n> --comments`.
- **List:** `gh issue list --state open --label <label> --json number,title,labels,assignees`.
- **Comment:** `gh issue comment <n> --body "..."`.
- **Labels:** `gh issue edit <n> --add-label "..."` / `--remove-label "..."`.
- **Close:** `gh issue close <n> --comment "..."`.
- **Sub-issue:** `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`.
  Where sub-issues aren't enabled, add the child to a task list in the parent body and put
  `Part of #<parent>` at the top of the child.
- **Blocking:** `gh api --method POST repos/<owner>/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<blocker-db-id>`.
  Always also write a `Blocked by #<n>` line in the body, so the edge is readable everywhere.
- **Database id** (needed by the two calls above, not the `#number`):
  `gh api repos/<owner>/<repo>/issues/<n> --jq .id`.

GitHub numbers issues and pull requests in one sequence, so a bare `#42` may be either: try
`gh pr view 42` and fall back to `gh issue view 42`.

## Labels

| Role | Label in this repo | Meaning |
|---|---|---|
| Spec | `spec` | The parent issue holding a spec from `compost:spec` |
| Ready for agent | `ready-for-agent` | A slice an agent can build without a person |
| Ready for human | `ready-for-human` | A slice that needs a person (credentials, a manual step) |
| Map | `map` | A map issue for long, foggy work |
| Decision | `decision` | A decision sub-issue of a map |

Edit the middle column if the repo already uses other names for these roles. Create a missing
label with `gh label create <name>` the first time it is needed.

## Records

- **Rulings** (a decision made without stopping: what, why, cost if wrong) are comments on the
  issue being worked, summarized in the pull request.
- **Progress** is the checklist of slices on the parent issue plus the git log. Commits reference
  the issue number; the issue closes when its pull request merges.

## Map operations

Used by `compost:slice` for map issues.

- **Map:** one issue labelled `map`; its decisions are sub-issues labelled `decision`.
- **Frontier:** the map's open sub-issues with no open blocker
  (`issue_dependencies_summary.blocked_by` is 0, or every issue on the `Blocked by` line is
  closed) and no assignee; first in map order wins.
- **Claim:** `gh issue edit <n> --add-assignee @me`, before any other work.
- **Resolve:** `gh issue comment <n> --body "<answer>"`, `gh issue close <n>`, then add the gist
  and link to the map's Decisions so far.
