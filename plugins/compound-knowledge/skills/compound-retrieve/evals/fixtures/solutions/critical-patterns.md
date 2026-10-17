# Critical Patterns

High-severity patterns that apply across all tasks. Read before starting work.

## Check the main checkout before merging an agent's branch

**Severity:** high

A parallel agent asked for its own checkout can still write into the main working directory.
Before merging any agent's branch, run `git status` in the main checkout and commit or stash what
is there; otherwise the merge stops with "local changes would be overwritten", and a hurried
`git checkout -- .` throws away another agent's finished work.

Source: `workflow/parallel-worktree-builders-claude-plugins-20260317.md`

## Never commit an API key to a plugin's scripts

**Severity:** critical

Plugin scripts are copied into every user's plugin cache. Read keys from the environment
(`MOCHI_API_KEY`, `TYPESAFE_API_KEY`), never from a literal in the script or its tests.
