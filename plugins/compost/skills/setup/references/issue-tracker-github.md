# Issue tracker: GitHub

Specs, slices, and maps for this repo live as GitHub issues. Use `gh api` (GitHub's REST API) for
every operation. Run inside a clone, it fills `{owner}/{repo}` from `git remote -v`. The porcelain
commands (`gh issue view`, `list`, `create`, `comment`, `edit`, `close`, `gh pr create`, `edit`, `view`, `ready`, `merge`, `gh repo view`) go through
GraphQL, which Claude Code cloud sessions block with an HTTP 403; REST works there and locally.

## Commands

- **Create:** `gh api repos/{owner}/{repo}/issues -f title="..." -f "labels[]=..." -F body=@-` with
  a heredoc body on stdin. It prints the new issue's JSON; `--jq .number` keeps just the number.
- **Read:** `gh api repos/{owner}/{repo}/issues/<n> --jq '.title, .state, .body'`, then
  `gh api repos/{owner}/{repo}/issues/<n>/comments --paginate --jq '.[] | .user.login, .body'`.
- **List:** `gh api "repos/{owner}/{repo}/issues?state=open&labels=<label>" --paginate --jq '.[] | select(.pull_request | not) | {number, title, labels: [.labels[].name], assignees: [.assignees[].login]}'`.
  The issues endpoint returns pull requests too; the `select` drops them.
- **Comment:** `gh api repos/{owner}/{repo}/issues/<n>/comments -F body=@-` with a heredoc body.
- **Labels:** `gh api repos/{owner}/{repo}/issues/<n>/labels -f "labels[]=..."` to add,
  `gh api -X DELETE repos/{owner}/{repo}/issues/<n>/labels/<label>` to remove.
- **Close:** comment first, then
  `gh api -X PATCH repos/{owner}/{repo}/issues/<n> -f state=closed -f state_reason=completed`
  (`not_planned` for a won't-do).
- **Sub-issue:** `gh api --method POST repos/{owner}/{repo}/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`.
  Where sub-issues aren't enabled, add the child to a task list in the parent body and put
  `Part of #<parent>` at the top of the child.
- **Blocking:** `gh api --method POST repos/{owner}/{repo}/issues/<n>/dependencies/blocked_by -F issue_id=<blocker-db-id>`.
  Always also write a `Blocked by #<n>` line in the body, so the edge is readable everywhere.
- **Database id** (needed by the two calls above, not the `#number`):
  `gh api repos/{owner}/{repo}/issues/<n> --jq .id`.

GitHub numbers issues and pull requests in one sequence, so a bare `#42` may be either:
`gh api repos/{owner}/{repo}/issues/42 --jq '.pull_request != null'` prints `true` for a pull request.

## Pull requests

Used by `compost:finish`. `{owner}/{repo}` fills in as above; `<n>` is the pull request number.

- **Default branch:** `gh api repos/{owner}/{repo} --jq .default_branch`.
- **Create (draft):** `gh api repos/{owner}/{repo}/pulls -f title="..." -f head=<branch> -f base=<target> -F draft=true -F body=@- --jq '.number, .html_url'`
  with the PR body as a heredoc on stdin.
- **Edit body:** `gh api -X PATCH repos/{owner}/{repo}/pulls/<n> -F body=@-` with a heredoc body.
- **Read:** `gh api repos/{owner}/{repo}/pulls/<n> --jq '.state, .draft, .mergeable_state'`.
- **Ready for review:** the forge refuses to merge a draft, and the public REST API has no
  endpoint for leaving draft. Locally, `gh pr ready <n>` (GraphQL). In a Claude Code cloud session
  that is blocked; use `gh api -X POST repos/{owner}/{repo}/pulls/<n>/ccr/ready_for_review`.
- **Merge (merge commit):** `gh api -X PUT repos/{owner}/{repo}/pulls/<n>/merge -f merge_method=merge`.
  Never `squash` or `rebase` unless the user asks.
- **Delete the remote branch after the merge:** `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`.

## Labels

| Role | Label in this repo | Meaning |
|---|---|---|
| Spec | `spec` | The parent issue holding a spec from `compost:spec` |
| Ready for agent | `ready-for-agent` | A slice an agent can build without a person |
| Ready for human | `ready-for-human` | A slice that needs a person (credentials, a manual step) |
| Map | `map` | A map issue for long, foggy work |
| Decision | `decision` | A decision sub-issue of a map |

Edit the middle column if the repo already uses other names for these roles. `compost:setup`
creates every label in the middle column that the repo lacks with
`gh api repos/{owner}/{repo}/labels -f name=<name>`.

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
- **Claim:** `gh api repos/{owner}/{repo}/issues/<n>/assignees -f "assignees[]=$(gh api user --jq .login)"`,
  before any other work.
- **Resolve:** comment the answer and close the issue (Commands above), then add the gist and link
  to the map's Decisions so far.
