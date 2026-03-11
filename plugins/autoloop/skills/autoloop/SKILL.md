---
name: autoloop
description: >
  Design and generate autonomous experiment loops that iteratively improve code by
  editing, running, measuring a scalar metric, and keeping improvements via git
  commit/reset. Based on Karpathy's autoresearch pattern. Use this skill whenever
  the user mentions "autoloop", "autoresearch", "experiment loop", "hill-climbing",
  "optimize overnight", "program.md", "karpathy loop", "autonomous optimization",
  "self-improving loop", or wants to set up any kind of iterative improvement
  process where an LLM agent runs experiments autonomously. Also trigger when the
  user says things like "I want to let Claude optimize this while I sleep", "can we
  automate trying different approaches", "set up a loop to improve this", or
  "I want to run experiments overnight". This skill explores the current project,
  designs loop parameters, and generates a complete self-contained program.md
  ready to run with claude --dangerously-skip-permissions.
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Autoloop — Autonomous Experiment Loop Generator

## What This Is

The autoloop pattern turns an LLM coding agent into an autonomous scientist. There is no
orchestration code — a single `program.md` file IS the entire system. The LLM reads it,
then loops forever: edit code → run experiment → parse metric → git commit (keep) or
git reset (revert). The human walks away; the agent runs until interrupted.

Your job as the skill is the **design thinking**: mapping an arbitrary project onto the
five essential components that make this loop work:

1. **Mutable artifact** — the one file the agent edits
2. **Immutable context** — files the agent reads but never touches
3. **Scalar metric** — a single number that says "better" or "worse"
4. **Execution step** — a bounded command that tests the change
5. **Checkpoint/rollback** — git commit to keep, git reset to revert

Plus a **results ledger** (results.tsv) that survives rollbacks because it's untracked.

Getting these five components right is the difference between a loop that runs 126
experiments overnight and one that crashes after 3.

---

## Phase 1 — Scout the Project

First, explore the project to understand what we're working with.

Delegate to the codebase-scout agent:

```
Agent(
  subagent_type="autoloop:codebase-scout",
  model="haiku",
  prompt="Explore {cwd} and return a structured summary of: project type, language, build/test/bench commands, source files, config files, candidate metrics, and immutable files. See your instructions for the full output format.",
  description="Scout project for autoloop"
)
```

While the scout runs, tell the user: "I'm exploring your project to understand the build system, test infrastructure, and what metrics we can optimize. This takes about 15 seconds."

When results come back, summarize what was found in 3-5 bullet points. Don't dump the raw output.

---

## Phase 2 — Design the Loop

This is where the skill earns its keep. Using the scout results AND the user's stated goal, design all five components. Think carefully — the wrong choices here waste hours of autonomous runtime.

### 2a. Infer the Mutable Artifact

What file should the agent edit? This depends on the optimization goal:

| Goal | Likely mutable file |
|------|-------------------|
| ML training improvement | The training script (train.py, train.rs) |
| Test coverage | The source files being tested (may be multiple — pick the lowest-coverage one) |
| Performance | The module containing the hot path |
| Lint score | Source files with the most violations |
| Prompt engineering | The prompt template file |
| Config tuning | The config file being tuned |

If the answer isn't obvious, present 2-3 options with trade-offs:
- "Option A: `src/model.py` — the core model. Changes here have the biggest impact but also the most risk."
- "Option B: `src/data.py` — the data pipeline. Safer to experiment with, but impact ceiling is lower."

**Important**: The mutable file should be small enough that the agent can read and understand it in one pass. If a candidate file is >500 lines, suggest a more focused subset or ask the user to extract the relevant section.

### 2b. Infer the Metric

What number tells us if things got better? Check what the project already has:

- **Has tests** → test count (`pytest -v 2>&1 | tail -1`), coverage % (`pytest --cov --cov-report=term 2>&1 | grep TOTAL`), pass rate
- **Has benchmarks** → execution time, throughput, ops/sec
- **Has linting** → ruff/pylint issue count (lower is better)
- **Has ML training** → validation loss, accuracy, perplexity
- **Has eval suite** → accuracy, F1, score

**If no metric can be inferred: ASK THE USER.** This is the one case where you must not guess. Say:
> "I can see how to run experiments, but I can't determine what metric to optimize. What number should I be trying to improve? It needs to be something I can parse from command output."

Also determine the **direction**: "lowest" (minimize) or "highest" (maximize). Make this explicit.

### 2c. Infer the Execution Command

How to run an experiment. Usually comes directly from the scout results:
- Python: `uv run pytest ...`, `uv run python train.py ...`
- JS/TS: `npm test`, `npx jest ...`
- Rust: `cargo test`, `cargo bench`
- Go: `go test ./...`, `go test -bench .`

The command should redirect output to a log file: `{cmd} > run.log 2>&1`

This prevents stdout from flooding the agent's context window.

### 2d. Design the Time Budget

Estimate how long each experiment takes. If unsure, ask: "How long does `{test_cmd}` typically take to run?"

Guidelines:
- Fast tests (<30s): set budget to 1 minute, timeout to 3 minutes
- Medium tests (1-5 min): set budget to match, timeout to 2x
- Slow training (>5 min): set budget to match, timeout to 3x
- Very slow (>30 min): warn the user that fewer experiments will run overnight

### 2e. Choose Immutable Context

Everything the agent should read but not edit:
- README.md (project context)
- Config files (pyproject.toml, package.json, etc.)
- Type definitions and interfaces
- Test fixtures and eval harnesses
- The metric extraction command itself

### 2f. Define Allowed Change Types

What kinds of mutations are fair game? Read the appropriate domain block from `references/domain-examples.md` based on the detected project type and goal.

Map goals to domains:
- ML/training → "ML / Deep Learning Training"
- Test coverage → "Test Coverage Improvement"
- Lint/quality → "Code Quality / Lint Score"
- Performance → "Performance / Benchmarks"
- Prompts → "Prompt Engineering"
- Config → "Configuration Tuning"

---

### Present the Design

After working through 2a-2f, present the complete design as a single summary:

```
## Autoloop Design

**Goal**: {what we're optimizing}
**Mutable file**: `{path}` — {description}
**Metric**: {metric_name} ({direction} is better)
**Execution**: `{command} > run.log 2>&1`
**Metric extraction**: `{extraction_command}`
**Time budget**: ~{budget} per experiment (timeout: {timeout})
**Immutable context**: {list of files}
**Strategy**: {domain} — {brief description of change types}

Does this look right? I'll adjust anything before generating.
```

One confirmation round. The user says "looks good" or adjusts specifics.

---

## Phase 3 — Verify Baseline

Before generating the program.md, run the metric extraction once to catch problems early.

```bash
{execution_command}
```

Then:
```bash
{metric_extraction_command}
```

Check:
1. **Did the command succeed?** (exit code 0)
2. **Is the metric parseable?** (can you extract a number?)
3. **Is the metric reasonable?** (not NaN, not 0 when it shouldn't be)

If anything fails, debug it with the user. Common issues:
- Wrong test command (missing `--cov` flag, wrong test directory)
- Metric grep pattern doesn't match output format
- Missing dependencies (need `uv sync` first)
- Permission issues

**Do not proceed to generation until the baseline passes.** This catches broken setups before the user walks away for 8 hours.

Report the baseline:
> "Baseline verified: {metric_name} = {value}. The extraction command works. Ready to generate."

---

## Phase 4 — Generate

Now create the program.md by filling in the template.

### Step 1: Read the template
Read `references/program-md-template.md` to get the structure.

### Step 2: Read domain strategy
Read the appropriate section from `references/domain-examples.md`.

### Step 3: Fill variables

Replace all `{VARIABLE}` placeholders with values from the design phase:

| Variable | Source |
|----------|--------|
| `{PROJECT_NAME}` | Scout: project name |
| `{WHAT_IS_BEING_OPTIMIZED}` | User's stated goal |
| `{MUTABLE_FILE}` | Design 2a |
| `{MUTABLE_FILE_DESCRIPTION}` | Brief description of the file's contents |
| `{WHAT_IS_FAIR_GAME}` | From domain-examples.md |
| `{IMMUTABLE_FILES_LIST}` | Design 2e, formatted as bullet list |
| `{PRECONDITIONS_CHECK}` | Any setup verification needed |
| `{EXECUTION_CONTEXT}` | Environment description (local machine, GPU, etc.) |
| `{EXECUTION_COMMAND}` | Design 2c (with output redirect) |
| `{LOG_FILE}` | Usually `run.log` |
| `{METRIC_NAME}` | Design 2b |
| `{METRIC_DIRECTION}` | "lowest" or "highest" |
| `{METRIC_EXTRACTION_COMMAND}` | Design 2b |
| `{METRIC_OUTPUT_EXAMPLE}` | From baseline verification |
| `{RESOURCE_CONSTRAINTS}` | Memory, CPU, GPU limits if known |
| `{TIME_BUDGET}` | Design 2d |
| `{TIMEOUT_LIMIT}` | Design 2d |
| `{BASELINE_METRIC_VALUE}` | From Phase 3 |
| `{ADDITIONAL_GOAL_CONTEXT}` | Any extra framing |
| `{STRATEGY_GUIDANCE}` | Full domain block from domain-examples.md |
| `{IMPROVED_METRIC_EXAMPLE}` | Slightly better than baseline |
| `{WORSE_METRIC_EXAMPLE}` | Slightly worse than baseline |
| `{EXAMPLE_IMPROVEMENT_DESC}` | Plausible improvement description |
| `{EXAMPLE_DISCARD_DESC}` | Plausible failed experiment |
| `{EXAMPLE_CRASH_DESC}` | Plausible crash scenario |

### Step 4: Preview

Show the user the generated program.md content. Say:
> "Here's the program.md I'll write to your project root. Review it — once you confirm, I'll create the file."

### Step 5: Write files (on confirmation)

1. Write `program.md` to the project root
2. Write `results.tsv` with just the header row:
   ```
   commit\t{METRIC_NAME}\tstatus\tdescription
   ```
3. Check if `.gitignore` exists and whether `results.tsv` is already listed:
   - If `.gitignore` exists and `results.tsv` is NOT listed → append `results.tsv` to it
   - If `.gitignore` doesn't exist → create it with `results.tsv`
   - If already listed → do nothing
4. Do **NOT** git commit. Leave that to the user.

---

## Phase 5 — Launch Instructions

After writing the files, print clear instructions:

```
## Ready to Launch

Your autoloop is configured. To start:

1. Review the generated files:
   - `program.md` — the experiment loop instructions
   - `results.tsv` — empty ledger (header only)

2. Start the loop:
   ```bash
   claude --dangerously-skip-permissions -p "Read program.md and execute the loop protocol. Do not stop until I interrupt you."
   ```

3. Walk away. The agent will:
   - Create a branch (`autoloop/{tag}`)
   - Establish the baseline
   - Loop: edit → run → measure → keep/revert
   - Log every experiment to results.tsv

4. When you come back:
   ```bash
   cat results.tsv                    # See experiment trajectory
   git log --oneline                  # See which iterations were kept
   git diff main..HEAD               # See cumulative changes
   ```

5. If you like the results:
   ```bash
   git checkout main
   git merge autoloop/{tag}           # Or cherry-pick specific commits
   ```
```

---

## Troubleshooting

If the user reports issues after running the loop, help diagnose:

**"The agent stopped after a few iterations"**
The NEVER STOP directive may not be strong enough for the model being used. Options:
- Add more emphatic language to program.md
- Check if the agent hit a context limit (very long output flooding context)
- Ensure output is redirected to run.log, not printed to stdout

**"Every experiment crashes"**
The mutable artifact scope may be too broad. Narrow what the agent is allowed to change, or check that the execution environment is stable (dependencies installed, paths correct).

**"Metric isn't improving"**
The metric may not be responsive to the kinds of changes being made. Check:
- Is the metric actually affected by the mutable file?
- Is the change space too narrow? (e.g., tuning one hyperparameter that's already optimal)
- Is the metric noisy? (random seed variation exceeding improvement signal)

**"Agent makes the same change repeatedly"**
The agent isn't learning from results.tsv. Check:
- Is results.tsv being read between iterations?
- Are descriptions specific enough to distinguish experiments?
- Try adding: "Before each experiment, read results.tsv and explicitly state what you learned from past attempts."

**"Git state got messy"**
If the branch is in a bad state:
```bash
git stash                    # Save any uncommitted work
git log --oneline -20        # See recent history
git reset --hard {good_commit}  # Reset to last known good state
```
