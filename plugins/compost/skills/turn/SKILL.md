---
name: turn
description: Checks the skill repos compost was made from for upstream changes worth working in, and adds skill repos to watch as references. Use when asked "anything upstream worth pulling in?", "turn the pile", "check superpowers / Matt Pocock / pstack for updates", "add this skill repo as a reference", or on the monthly scheduled run.
---

# turn

Turning a compost pile mixes new material in. compost was made by breaking other people's skills
down and rebuilding them; those sources keep improving. `turn` finds what changed upstream since
compost last took from each source, decides what is worth working in, and files that as issues.
It never edits compost's skills itself: an adopted change goes through `compost:spec`, or
`compost:build` for a single small adopt, like any other work, so it gets built, verified, and
reviewed.

`pile.toml` at the plugin root lists every source:

- `input`: a source compost takes text from. `pin` is the upstream commit compost reflects, and
  `feeds` maps upstream paths to the compost skills they fed.
- `frozen`: an input that will not change again (a retired plugin). Listed for attribution only.
- `reference`: a repo watched for ideas and not drawn from yet.

`${CLAUDE_PLUGIN_ROOT}/scripts/pile.py` does the bookkeeping (Python 3.11+ via uv, stdlib only).

## Check for upstream changes

1. Run `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/pile.py status`. For each input it keeps a blobless
   clone under `~/.cache/compost/upstream/`, lists every file changed since the pin, and groups
   them by the compost skill they feed, then lists the names of the changed files no `feeds` entry
   maps. It prints the `git diff` command for reading each change.
2. Skim the unmapped file names for a skill that did not exist when the pin was set; a promising
   one becomes a `feeds` entry, and its paths go into the sort below.
3. Sort the changes before reading them. Ask Jev first: per source, write
   `{"source": "<name>", "paths": [<every path listed under a compost skill, plus promising
   unmapped ones>]}` to a temp file and run
   `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py classify-change --input <file>`. Record each change
   with `needs_reading: false` as ignored, with Jev's verdict as the reason, without reading it.
   Read the diff of every path in `to_read` and judge it yourself; Jev's verdict there is a hint,
   since it over-calls adopt and adapt on long diffs ([Jev tools](references/jev-tools.md)). Exit 3
   means Jev is unavailable: read every listed diff. Judge each change you read against the compost
   skill it feeds and the [canon](../../canon/README.md):
   - **adopt**: better than what compost has, fits as is (a sharper step, a fixed bug, a clearer
     example)
   - **adapt**: the idea is good, the form conflicts with compost's rulings (a new approval gate,
     a TDD ritual, beads, a size rule); take the idea, not the text
   - **ignore**: churn, tooling specific to the source, or already covered
   When dozens of changes remain to read, split them across parallel subagents, one per compost
   skill, each returning adopt / adapt / ignore with a one-line reason; then read the adopt and
   adapt candidates yourself.
4. File one issue per adopt or adapt on the compost repo (the `repository` in
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`), labeled `upstream`, with the upstream diff
   link, the compost skill it touches, and what to take.
5. Once every change since a pin has a ruling, move the pin. Pins live in the source repo, not the
   installed plugin: in a worktree of that repo run
   `uv run plugins/compost/scripts/pile.py advance <source> <commit>`, then
   `uv run plugins/compost/scripts/pile.py notice`, and commit both with the ignored changes and
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

## Check compost's own text after a change

An adopted change rewrites a skill, and a description edit changes which skill Claude loads. After
any change to a skill's text or description, run the plugin's two regression evals before the
change merges ([Jev tools](references/jev-tools.md)):

1. **Routing.** From `plugins/compost` in the source repo, run
   `uv run --group dev pytest -m jev tests/test_evals_meta.py -k route -s`. It routes the 30 real
   prompts in `tests/evals/route.json` through every skill's description and fails below 27 of 30.
   A new miss, or a prompt now marked `close`, points at the description that moved; fix the
   description, not the eval.
2. **Rulings.** Write `{"paths": [<the changed markdown files, relative to the plugin root>]}` to a
   temp file and run `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/jev.py rulings-lint --input <file>`
   (`{}` lints the whole plugin). Read each flagged passage against the rulings it names: reword
   the ones that drifted, and leave the false flags with a line in the commit message.

Exit 3 from either means Jev is unavailable: re-read the changed text against the rulings yourself.

## Run it on a schedule

A monthly run needs no one watching: it only reads upstream and files issues. Set it up with a
scheduled routine or a cron-driven `claude -p "/compost:turn"` in the compost repo.

## Next moves

- `compost:build` when `turn` filed a single small adopt worth doing now.
- `compost:spec` when filed issues are worth doing now: it turns them into a parent issue that
  `compost:implement` can work, and gives an adapted idea the design it needs.
