# Issue tracker: GitLab

Specs, slices, and maps for this repo live as GitLab issues. Use the `glab` CLI for every
operation; it infers the project from `git remote -v` when run inside a clone.

## Commands

- **Create:** `glab issue create --title "..." --label "..." --description "..."`, using a heredoc
  for multi-line descriptions.
- **Read:** `glab issue view <n> --comments`, or `-F json` for machine-readable output.
- **List:** `glab issue list -F json --label <label>`.
- **Comment:** `glab issue note <n> --message "..."`. GitLab calls comments notes.
- **Labels:** `glab issue update <n> --label "..."` / `--unlabel "..."`.
- **Close:** `glab issue close <n>`. It takes no closing comment, so post the note first.
- **Merge requests:** GitLab's name for pull requests: `glab mr create`, `glab mr view`,
  `glab mr note`.
- **Child issue:** put `Part of #<parent>` at the top of the child's description and add the child
  to a task list in the parent. On tiers with epics, an epic may hold the parent instead.
- **Blocking:** post the `/blocked_by #<n>` quick action as a note
  (`glab issue note <child> --message "/blocked_by #<blocker>"`). Native blocking links need
  Premium or Ultimate, so always also write a `Blocked by #<n>` line in the description.

GitLab numbers issues and merge requests separately, so `#42` means an issue and `!42` a merge
request.

## Labels

| Role | Label in this repo | Meaning |
|---|---|---|
| Spec | `spec` | The parent issue holding a spec from `compost:spec` |
| Ready for agent | `ready-for-agent` | A slice an agent can build without a person |
| Ready for human | `ready-for-human` | A slice that needs a person (credentials, a manual step) |
| Map | `map` | A map issue for long, foggy work |
| Decision | `decision` | A decision sub-issue of a map |

Edit the middle column if the project already uses other names for these roles.

## Records

- **Rulings** (a decision made without stopping: what, why, cost if wrong) are notes on the issue
  being worked, summarized in the merge request.
- **Progress** is the checklist of slices on the parent issue plus the git log. Commits reference
  the issue number; the issue closes when its merge request merges.

## Map operations

Used by `compost:slice` for map issues.

- **Map:** one issue labelled `map`; its decisions are child issues labelled `decision`.
- **Frontier:** the map's open children with no open blocker (no native `blocked_by` link to an
  open issue, per `glab api projects/:id/issues/:iid/links`, and every issue on the `Blocked by`
  line closed) and no assignee; first in map order wins.
- **Claim:** `glab issue update <n> --assignee @me`, before any other work.
- **Resolve:** `glab issue note <n> --message "<answer>"`, `glab issue close <n>`, then add the
  gist and link to the map's Decisions so far.
