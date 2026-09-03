# autonomous-sdlc vs. Anthropic's AI-Native SDLC Playbook

**Date**: 2026-09-03
**Plugin audited**: `autonomous-sdlc` v2.3.1 (with the v3.0.0 slim-down plan in
`docs/superpowers/plans/2026-07-18-autonomous-sdlc-v3-slimdown.md` taken as the direction of travel)
**Reference**: [The AI-Native SDLC Playbook](https://claude.com/blog/the-ai-native-sdlc-playbook)

## Verdict

The plugin already implements the playbook's spine: a loop instead of a linear pipeline,
a committed artifact chain (`spec.md` → `plan.md` → diff → PR), hooks as deterministic
guardrails, worktree-isolated subagents, and a human-approval boundary at the PR. The
decision journal (`.sdlc/decisions.jsonl` rendered into the PR) is something the playbook
does not have and should keep.

Three things are structurally missing, and they are the ones that make the playbook a
*closed* loop rather than a build pipeline:

1. **No `intent.md` in or out.** The loop starts from a one-line `request` string and
   ends at a PR. The playbook's Plan stage produces `intent.md`, and its Maintain stage
   *emits* `intent.md` back into Plan. Without an intent artifact the plugin cannot be
   the consumer of the observability-harness's future monitoring output, so the two
   plugins cannot compose into the playbook's full cycle.
2. **No human gate between plan and code.** The playbook's Build stage is "approved plan
   committed before code is written". The plugin explicitly proceeds on the plan without
   approval (`agents/architect.md:59`). That is a deliberate autonomy choice, and it
   should stay the default, but there is no way to opt into the gate short of switching
   to `stick-shift`.
3. **No test-lock on fix tasks.** The playbook's Test stage requires a hook that blocks
   editing test files while fixing a bug, so a green run proves the bug is gone rather
   than that the test was changed. The VERIFY → BUILD fix-task path has no such hook.

Everything else is either a match, a small addition, or explicitly outside the plugin's
boundary (deploy, production monitoring).

## Scorecard

Status: **match** / **partial** / **gap** / **out of scope**.

| Playbook practice | Status | Evidence in plugin | Recommendation |
|---|---|---|---|
| **Plan**: capture as committed `intent.md` | gap | Request is a string in `.sdlc/state.json` (`scripts/sdlc_state.py:160`); no intent artifact | Accept `/sdlc <path-to-intent.md>`; when given a sentence, INIT writes `specs/{slug}-intent.md` in playbook format |
| **Design**: `spec.md` committed, flagged concerns | match | SPEC state writes `specs/{slug}-spec.md` with numbered AC (`skills/sdlc-loop/SKILL.md:62-67`); v3 keeps the file and its own commit (`v3 plan:315`) | Keep the separate commit; the playbook's rework metric counts `spec.md` commits after the first `plan.md` commit |
| **Design**: spec constrained by org policy skills | gap | Signs and `feedback` are learned guardrails, not declared policy | `init --policies <skills>` mirroring `--reviewers`; load them at SPEC/PLAN and REVIEW |
| **Design**: concerns resolved by a human before build | partial (by design) | Decide-log-proceed batches decisions to the PR (`SKILL.md:205-260`) | No change by default; the optional plan gate below covers teams that want it |
| **Build**: plan mode, `plan.md` names files, order, tests | match | Architect template has Relevant Files, Tasks, Validation Commands (`agents/architect.md:86-108`) | None |
| **Build**: approved plan committed before code | gap (by design) | `agents/architect.md:59` "Don't wait for approval of the plan" | `init --gate plan`: after PLAN commits, `transition BLOCKED --reason "plan review"` with an escalation file that says "review `specs/{slug}-plan.md`, re-run `/sdlc`". Zero new states |
| **Build**: PR review checks diff against committed plan | gap | VERIFY checks spec compliance AC by AC (`SKILL.md:130`); nothing compares the diff to `plan.md` | REVIEW step 0: diff `git diff --name-only main...` against the plan's Relevant Files table; unplanned files become a logged decision or a finding |
| **Build**: CLAUDE.md as institutional knowledge, updated on repeated mistakes | partial | Signs (`SKILL.md:249-255`) capture repeated mistakes into `.sdlc/signs.md`, graduate to per-user `feedback`; never to the project's CLAUDE.md | SHIP proposes a CLAUDE.md diff from `signs.md` inside the PR so the team reviews it |
| **Build**: skills as versioned policy | match | Six skills, versioned, in git | None |
| **Build**: hooks run formatter/linter after edits | partial | Ruff + type validators on `*.py` only, hardcoded `uv run` (`agents/builder.md:23-32`) | Detect the project's lint/type commands at INIT and store them in `state.json`; validators read from there |
| **Build**: hooks block edits to protected paths | gap | Denylist covers git/publish commands only (`hooks/scripts/auto-approve.sh:36-47`) | Add a `protected_paths` list to `state.json` (default: `.github/workflows`, lockfiles, migrations) enforced by a PreToolUse hook on Write/Edit |
| **Build**: keep credentials out of diffs | gap | Nothing scans staged changes | Builder pre-commit check with `gitleaks protect --staged` when available, else a regex sweep; secrets are already on the escalate list |
| **Build**: parallel sessions, worktrees, scoped subagents | match | `isolation: "worktree"` builders, wait-aware Stop hook, `WorktreeCreate/Remove` hooks | Ship the v3 Task 6 fix for the hook-stdout bug; it currently breaks `EnterWorktree` |
| **Test**: one test target, listed with healthy output | partial | INIT "detects test runner" (`SKILL.md:57`) but records nothing; Builder hardcodes `uv run pytest tests/ -x` (`builder.md:121`) | INIT writes `test_command` to `state.json`; Builder, VERIFY and the completion verifier all read it |
| **Test**: failing test first, committed, then fix | partial | TDD is enforced for features; VERIFY red creates a fix task but does not require the failing test to be committed first | Fix tasks carry `type: fix`; Builder commits the reproducing test before touching source |
| **Test**: hook blocks test edits during fix tasks | gap | No such hook | PreToolUse deny on `tests/**` when any in-flight task in `state.json` is `type: fix` |
| **Test**: UI screenshot loop | out of scope | Plugin is stack-agnostic at the loop level | None |
| **Test**: continuous evals on agent-config change, incidents become evals | partial | Skill-trigger evals in `evals/`; `check_all.py` in CI on every PR; no task-level evals, no incident-to-eval path | Add a `ci-evals` job that runs `claude plugin eval` when `plugins/autonomous-sdlc/**` changes; seed 20 real `/sdlc` tasks from past loop runs |
| **Review**: identical passes ranked by severity | match | REVIEW runs `code-review`, optional `security-review`, then `simplify`; configurable reviewers and block/annotate mode | None |
| **Review**: `REVIEW.md` policy with passes and Important vs Nit | gap | Review policy lives in CLI flags (`init --reviewers`), not a committed file | Read `REVIEW.md` from the project root when present and pass it to the review skills; flags remain the override |
| **Review**: compliance pass against `spec.md`, `plan.md`, principles | partial | Spec compliance in VERIFY; no plan compliance; no principles input | Covered by the plan-alignment check and `--policies` above |
| **Review**: Claude addresses comments on its own PRs | partial | SHIP "optionally suggests" `/loop` (`SKILL.md:183`); DONE is terminal at PR-open | SHIP prints the exact `/loop` command the way `/sdlc` prints the `/goal`, and records `pr_url` in `state.json` |
| **Review**: separation of duties, human approval via branch protection | match | Loop never merges; denylist blocks push to main; PR is the boundary | Document this explicitly in the README's safety section |
| **Review**: hooks as approval gates | partial | BLOCKED is the only gate, and only for escalations | The `--gate plan` flag reuses BLOCKED as an approval gate; `--gate ship` (pause before `gh pr create`) is the same mechanism |
| **Deploy**: CI/CD, tiered autonomy, MCP deploy tools, rollback | out of scope | Plugin ends at PR | State the boundary in the README |
| **Deploy**: managed settings, deny lists | partial | Deny rules are regexes in a hook; the playbook puts them in managed `settings.json` | Publish the denylist as a copy-pasteable `permissions.deny` block so admins can enforce it outside the plugin |
| **Maintain**: deterministic detection, `bands.yaml`, Claude only after breach | out of scope for this plugin; gap for the pair | `observability-harness` has `status.sh --json` and `verify.sh` but no band checker | The harness grows a `bands.yaml` checker that writes `specs/{slug}-intent.md` on breach; `/sdlc <intent.md>` consumes it |
| **Cross-cutting**: artifact chain in git with author and timestamp | match | `state.json.history` has timestamps and reasons (`sdlc_state.py:178,321`); `decisions.jsonl`; `progress.md` | None |
| **Cross-cutting**: metrics per stage | gap, but computable | `history` carries every transition with time | `sdlc_state.py metrics` subcommand emitting the playbook table |

## Stage-by-stage notes

### Plan: intent

The playbook's originator produces a proto-spec (pain points, proposed outcome, affected
systems, open questions), reviews it, and commits it. The plugin's equivalent is
`$ARGUMENTS`. For a solo loop this is fine. It stops being fine at both edges of the
cycle: the Maintain stage hands over an `intent.md`, and the Design stage's rework metric
is measured from the `intent.md` commit. `stick-shift` already accepts `/spec <file>` and
records a `Source:` pointer, so the input side has prior art in this repo.

Concrete shape: `/sdlc "<sentence>"` keeps working. `/sdlc specs/foo-intent.md` reads the
file, derives the slug from its title, stores the path in `state.json` as `intent`, and
SPEC derives AC from the intent document instead of the request string. INIT writes an
intent file from a sentence so every loop has one.

### Design: spec

Strong match. The AC-N Given/When/Then format is exactly the "human-readable,
machine-actionable" artifact the playbook wants, and the `@ac-N` tags in `bdd-generate`
give the traceability the playbook asks for in review.

The v3 slim-down merges SPEC into PLAN as states but still writes and commits
`specs/{slug}-spec.md` separately (plan line 315). Keep that. If spec and plan ever land
in a single commit, the playbook's "requirements rework after build starts" metric
becomes uncomputable.

What is missing is the policy input. The playbook loads brand, security, and compliance
skills *while the spec is written*. The plugin has no slot to declare which skills
constrain a project. A `--policies` init flag with the same persistence as `--reviewers`
closes it in one afternoon, and the same list feeds REVIEW's compliance pass.

### Build: plan and code

The plan artifact matches. The gate does not, on purpose. The redesign doc's whole thesis
was "a question costs the whole loop". That is still right for the default. The playbook
is written for organizations, where the plan review is where a tech lead earns their
keep. Rather than argue about it, make it a flag:

```
python3 $STATE init --feature x --gate plan
```

After PLAN commits, the loop transitions to BLOCKED with an escalation file that reads
"review `specs/x-plan.md`, edit it if needed, re-run `/sdlc`". Resume already works from
BLOCKED. No new states, no new hooks, and it doubles as the playbook's "hooks as approval
gates" pattern. `--gate ship` (pause before `gh pr create`) is the same mechanism for
release-authorization shops.

The plan-alignment review is the cheaper and higher-value addition: the Architect already
writes a Relevant Files table, so REVIEW can diff the branch's touched files against it.
Files outside the plan are the playbook's lagging Build metric ("alignment between merged
diff and committed plan.md"), and today nobody looks.

Signs are the plugin's best idea for institutional knowledge and they currently dead-end.
`.sdlc/signs.md` is per-loop, `feedback` is per-user. The team-shared file is CLAUDE.md,
and the playbook's rule is "update it when Claude repeats a mistake twice". SHIP should
propose a CLAUDE.md diff from `signs.md` inside the PR, where a reviewer can accept or
reject it. That is adoption by default instead of a note in a journal.

### Test: feedback loop

The TDD discipline covers feature work. The gap is the *fix* path. When VERIFY goes red
it creates a fix task and sends the loop back to BUILD; the Builder that picks it up can
edit the failing test. The playbook is explicit that a hook must block that. The
information is already on disk: `state.json.in_flight` names the task, and the task
tracker holds its type. A PreToolUse hook on Write/Edit that denies `tests/**` when any
in-flight task is a fix task is a fifteen-line script in the pattern of
`auto-approve.sh`.

The single test target is half-done. INIT detects the runner and forgets it; the Builder
hardcodes pytest; the completion verifier prompt looks for `uv run pytest tests/`. A
`test_command` field in `state.json`, written once at INIT and read everywhere, makes the
plugin honest about being stack-agnostic.

Evals: the repo has skill-trigger evals and a real CI job, which is more than most. The
playbook's evals are task-level (20 to 50 real tasks with expected outcomes, rerun when
CLAUDE.md, skills, or hooks change). The v3 plan already cites eval results as its
justification for retiring `bdd-spec`, so the appetite exists. A `ci-evals` job scoped to
`plugins/autonomous-sdlc/**` changes is the natural next step.

### Review

The REVIEW state is a good match for "identical passes ranked by severity" and the
block/annotate split is a nice touch the playbook lacks. Two additions:

- **`REVIEW.md`.** The playbook commits the review policy; the plugin passes it as flags.
  Read `REVIEW.md` if it exists and hand it to the review skills as context. Flags stay as
  the override so nothing changes for current users.
- **Own-PR follow-through.** The playbook's loop continues past PR-open: Claude addresses
  review comments on its own PRs. DONE is terminal today. The minimum is printing the
  exact `/loop` command at SHIP the way `/sdlc` prints the `/goal`, so the handoff is
  copy-paste, and recording `pr_url` in `state.json` so a future post-SHIP state has it.

Separation of duties is a match worth naming in the README: the loop reviews its own
code but never approves or merges it, the denylist blocks pushes to main, and the PR is
the human boundary.

### Deploy and Maintain

Deploy is outside the plugin and should be stated as such. Maintain is outside
`autonomous-sdlc` but inside the marketplace: `observability-harness` is two pieces away
from the playbook's shape. It needs a deterministic band checker (`bands.yaml`, thresholds,
tiers) and an output contract (write `specs/{slug}-intent.md` on a 2σ or 3σ breach). With
the intent input from the Plan section, `/sdlc specs/{slug}-intent.md` closes the loop.
That composition is the single biggest step toward the playbook and it costs less than
the v3 slim-down.

## Where the plugin is ahead of the playbook

- **Decision journal.** Every autonomous decision is logged with a rationale and rendered
  into the PR. The playbook asks reviewers to check "behavior and risk" but gives them no
  list of judgment calls to check. Keep this, and keep the "cite the docs you checked"
  nudge.
- **Budgets and no-progress detection.** The playbook has no notion of bounded cost per
  change. `max_iterations`, `max_attempts`, and the two-idle-iteration force-block are
  operational maturity the playbook does not reach.
- **Resume from disk.** The playbook's "artifact chain" is an audit trail. The plugin's is
  also a resume point: context loss, session death, and next-increment all recover from
  `.sdlc/`.
- **Block vs annotate review modes.** The playbook only has blocking review.

## Recommendations, ranked by leverage per hour

| # | Change | Playbook practices closed | Cost | Touches |
|---|---|---|---|---|
| 1 | `intent.md` as input and INIT output | Plan artifact; Maintain → Plan handoff; enables harness composition | Half a day | `commands/sdlc.md`, `sdlc_state.py init`, SPEC dispatch |
| 2 | Test-lock hook for fix tasks | Test stage's hard rule | Two hours | New `hooks/scripts/test-lock.sh`, fix-task type in VERIFY/REVIEW dispatch |
| 3 | Plan-alignment check in REVIEW | Build lagging metric; compliance pass | Two hours | `sdlc-loop` REVIEW step 0 |
| 4 | `--gate plan` / `--gate ship` via BLOCKED | Approved plan; hooks as approval gates | Half a day | `sdlc_state.py init`, PLAN and SHIP dispatch |
| 5 | `sdlc_state.py metrics` | Whole metrics table | Two hours | `sdlc_state.py`, test file |
| 6 | Signs → CLAUDE.md proposal at SHIP | Institutional knowledge | One hour | SHIP dispatch |
| 7 | `test_command` recorded at INIT | Single test target; stack-agnostic builder | Two hours | INIT dispatch, `builder.md`, completion verifier prompt |
| 8 | `--policies` init flag, `REVIEW.md` read | Policy as code; review policy | Half a day | `sdlc_state.py`, SPEC/PLAN/REVIEW dispatch |
| 9 | Protected paths + staged-secret sweep | Build guardrails | Half a day | `auto-approve.sh` or a new PreToolUse hook |
| 10 | `bands.yaml` checker in observability-harness | Maintain stage | One to two days | Other plugin |

Items 1 through 5 are one working day. They fit inside v3.0.0 without conflicting with
the slim-down's scope, except that item 4 adds two init flags to `sdlc_state.py` which
the slim-down also edits. Sequence: land the slim-down first, then these.

## Interaction with the v3.0.0 slim-down

The slim-down removes SPEC and REPAIR as states and retires `bdd-spec`. Nothing in this
audit argues against that. Two constraints to carry into it:

- Keep `spec.md` as its own commit inside the merged PLAN state (the plan already does;
  this is a "do not regress" note).
- The slim-down's "Deliberately out of scope" list excludes `auto-approve.sh` and
  `loop-stop-hook.sh`. Items 2 and 9 above add hooks rather than editing those two, so
  they stay compatible with that boundary.

The slim-down's rationale ("intelligence-compensation that Fable/Opus-class models no
longer need") and the playbook's ("humans remain accountable for every decision that
requires judgment") pull in different directions on exactly one point: whether a human
sees the plan before code exists. The `--gate plan` flag lets both be true.
