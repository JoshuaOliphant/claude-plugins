---
name: turn
description: Checks the skill repos compost was made from for upstream changes worth working in, and adds skill repos to watch as references. Use when asked "anything upstream worth pulling in?", "turn the pile", "check superpowers / Matt Pocock / pstack for updates", "add this skill repo as a reference", or on the monthly scheduled run.
---

# turn

Turning a compost pile mixes new material in. compost was made by breaking other people's skills
down and rebuilding them; those sources keep improving. `turn` finds what changed upstream since
compost last took from each source, decides what is worth working in, and files that as issues.
It never edits compost's skills itself: an adopted change goes through `compost:implement` like
any other work, so it gets built, verified, and reviewed.

`pile.toml` at the plugin root lists every source:

- `input`: a source compost takes text from. `pin` is the upstream commit compost reflects, and
  `feeds` maps upstream paths to the compost skills they fed.
- `frozen`: an input that will not change again (a retired plugin). Listed for attribution only.
- `reference`: a repo watched for ideas and not drawn from yet.

`${CLAUDE_PLUGIN_ROOT}/scripts/pile.py` does the bookkeeping (Python 3.11+, stdlib only).

## Check for upstream changes

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/pile.py status`. For each input it keeps a blobless
   clone under `~/.cache/compost/upstream/`, lists every file changed since the pin, and groups
   them by the compost skill they feed. It prints the `git diff` command for reading each change.
2. Read the diff of every file listed under a compost skill. Skim the unmapped files' names for a
   skill that did not exist when the pin was set; a promising one becomes a `feeds` entry.
3. Judge each change against the compost skill it feeds and the [canon](../../canon/README.md):
   - **adopt**: better than what compost has, fits as is (a sharper step, a fixed bug, a clearer
     example)
   - **adapt**: the idea is good, the form conflicts with compost's rulings (a new approval gate,
     a TDD ritual, beads, a size rule); take the idea, not the text
   - **ignore**: churn, tooling specific to the source, or already covered
   When there are dozens of changes, sort them first with parallel subagents, one per compost
   skill, each returning adopt / adapt / ignore with a one-line reason; then read the adopt and
   adapt candidates yourself.
4. File one issue per adopt or adapt on the compost repo (the `repository` in
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`), labeled `upstream`, with the upstream diff
   link, the compost skill it touches, and what to take.
5. Once every change since a pin has a ruling, move the pin. Pins live in the source repo, not the
   installed plugin: in a worktree of that repo run
   `python3 plugins/compost/scripts/pile.py advance <source> <commit>`, then
   `python3 plugins/compost/scripts/pile.py notice`, and commit both with the ignored changes and
   their reasons in the commit message. That is the record that keeps them from resurfacing.
6. Report: per source, how many changes were adopted, adapted, and ignored, with the issue links.

## Add a reference

1. Clone the repo and read its skills. When `skill-atlas` is installed, run
   `skill-atlas --claude-dir <clone> judge` then `report` to get each skill's category, craft, and
   the techniques it uses; otherwise read the SKILL.md files directly.
2. Report which compost skills each one overlaps and what it would bring that compost lacks:
   worked examples, a verification step, a decision procedure, a sharper trigger.
3. Add a `[[source]]` with `role = "reference"`, its license, and `pin` set to the commit you read.
4. A reference becomes an `input` the first time compost takes text from it: set the role, add
   `feeds`, and regenerate NOTICE.

## Run it on a schedule

A monthly run needs no one watching: it only reads upstream and files issues. Set it up with a
scheduled routine or a cron-driven `claude -p "/compost:turn"` in the compost repo.

## Next moves

- `compost:implement` when `turn` filed issues worth doing now.
- `compost:spec` when an adapted idea is big enough to need its own design.
