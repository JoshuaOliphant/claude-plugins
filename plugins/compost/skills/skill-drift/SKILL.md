---
name: skill-drift
description: Reviews the skill-drift log that the skill-drift mod writes, and turns skills that keep drifting across sessions into draft fixes. Use when asked "review skill drift", "which skills keep going wrong", or on the daily scheduled run.
---

# skill-drift

A skill drifts when the way it gets used stops matching what it says: the agent skips a step it
states, it leaves out something the agent then has to work out, or the user corrects work it
covers. This is not upstream drift, which `compost:turn` handles; that is compost's copy falling
behind a source.

The `skill-drift` mod collects the evidence. After each turn that loaded a skill it asks TypeSafe
Jev whether the turn drifted, and writes each hit to `~/.claude/skill-drift/<date>-<session>.jsonl`
with the turn's prompt, a trace excerpt, and a hash of the skill's text. It never interrupts a
session. This skill reads that log, usually from a daily scheduled task, and proposes fixes.

One hit proves little: a turn can stray for reasons of its own. The same kind of drift on the
same skill in two separate sessions is a pattern, and patterns are what this skill acts on.

`${CLAUDE_PLUGIN_ROOT}/scripts/skill_drift.py` does the bookkeeping (Python 3.11+ via uv, stdlib
only). It drops hits on skills that are no longer active (a disabled plugin, a `skillOverrides`
entry set to `off`, a removed personal skill) and counts only hits on each skill's latest version,
so a skill already fixed stops producing patterns from its old text.

## Review the log

1. From the marketplace checkout, run
   `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/skill_drift.py patterns`. It prints JSON: each pattern's
   skill, kind (`deviated`, `missing_guidance`, `corrected`), owner, skill file, session count,
   `earlier_versions` (hits on the skill's text before its last change), and the hits with their
   `evidence`, `prompt`, and `transcript` path. With no patterns, report the `retired` and
   `unreadable` counts and stop.
2. **Read each pattern against the skill.** Open the skill file and read every hit's evidence
   next to the step it concerns. When the excerpt is too thin, search the hit's transcript for its
   prompt and read that turn. A pattern whose hits describe different things is not a pattern:
   treat each hit on its own.
3. **Decide where the fault is, and record the ruling** (what, why, cost if wrong):
   - **The skill.** A step is wrong, missing, or unclear, or real use keeps needing something it
     does not say. The fix goes in the skill.
   - **The instruction files.** The skill is right for its purpose but `CLAUDE.md` or `AGENTS.md`
     tells the agent otherwise, so the agent follows one and breaks the other. Name the conflict
     and propose which side changes.
   - **The agent.** The skill is clear and the instruction files agree; the agent ignored it. No
     edit, unless the step lacks the reason that would make it stick: then add the reason.
   - **A false flag.** The evidence does not show drift. Note it; enough of these on one kind
     mean the mod's threshold needs raising.
4. **Act by owner.**
   - `repo`, fault in the skill: branch `claude/skill-drift-<skill>` from the default branch,
     edit the skill file, and when the skill is compost's run the regression checks in
     [turn's "Check compost's own text after a change"](../turn/SKILL.md#check-composts-own-text-after-a-change). Bump the plugin's version as `AGENTS.md` says, run the
     repo checks, commit (`fix(<plugin>): <what the skill now says>`), push, and open one draft
     pull request per skill whose body carries the ruling and each hit's prompt and evidence. It
     stays a draft for the user to merge.
   - Everything else (`personal` and `third-party` skills, instruction-file conflicts): write the
     proposed change, as exact text, in the digest. Never edit files outside the checkout, and
     never edit `CLAUDE.md` or `AGENTS.md` from a scheduled run.
5. **Mark what you handled:** `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/skill_drift.py mark <id>...`
   with the `id` of every hit you ruled on, whatever the ruling, so the next run starts clean.
6. **Write the digest** to `~/.claude/skill-drift/digests/<date>.md` and end with the same text:
   one line per pattern with its ruling and outcome (pull request link, proposal, or no change),
   the retired and unreadable counts, and any skill whose `earlier_versions` is non-zero and has
   drifted again, since that means its last fix did not hold.

## Run it on a schedule

Make it a local scheduled task in Claude Desktop (Routines, New routine, Local), not a remote
routine: the log lives on this machine, and a remote routine only sees a fresh clone.

- **Instructions:** `/compost:skill-drift`
- **Folder:** the marketplace checkout, with the worktree toggle on so each run starts clean.
- **Schedule:** daily. A day the machine slept through gets one catch-up run on wake.
- **Permission mode:** one that edits without asking. Click **Run now** once, answer each
  prompt with "always allow", and later runs go through unattended.

Each run appears under Scheduled in the sidebar with a notification; the digest is its last
message.

## Next moves

- `compost:build` when a proposed fix is bigger than an edit to one skill's text: file it as an
  issue and build it.
- `compost:turn` when a pattern shows compost's copy of a skill drifted because its upstream
  source already fixed the same thing.
