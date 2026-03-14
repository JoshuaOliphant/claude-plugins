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
  plus an immutable runner script (auto/run.sh) with tiered quality gates and
  structured METRIC output, ready to run with claude --dangerously-skip-permissions.
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Autoloop — Autonomous Experiment Loop Generator

## What This Is

The autoloop pattern turns an LLM coding agent into an autonomous scientist. There is no
orchestration code — a single `program.md` file IS the entire system. The LLM reads it,
then loops forever: edit code → run experiment → parse metric → git commit (keep) or
git reset (revert). The human walks away; the agent runs until interrupted.

Your job as the skill is the **design thinking**: mapping an arbitrary project onto the
seven essential components that make this loop work:

1. **Mutable artifact** — the one file the agent edits
2. **Immutable context** — files the agent reads but never touches
3. **Primary metric** — a single number that says "better" or "worse"
4. **Secondary metrics** — numbers tracked for tradeoff monitoring (not optimized)
5. **Runner script** — an immutable shell script that runs quality gates and emits structured METRIC output
6. **Quality gates** — tiered checks (fast tests → conformance/lint → benchmark) that fail fast
7. **Checkpoint/rollback** — git commit to keep, git reset to revert

Plus a **results ledger** (results.tsv) and an **embedded progress log** (in program.md itself) that give the agent full history every iteration.

Getting these components right is the difference between a loop that runs 126
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

This is where the skill earns its keep. Using the scout results AND the user's stated goal, design all seven components. Think carefully — the wrong choices here waste hours of autonomous runtime.

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

#### Secondary metrics

After identifying the primary metric, identify 1-3 **secondary metrics** to track for tradeoff monitoring. These are NOT optimized — they're guardrails to prevent Goodhart's Law (optimizing one number while something else silently degrades).

Common secondary metrics by domain:

| Primary metric | Good secondary metrics |
|---------------|----------------------|
| Execution time (µs) | Object allocations, memory usage, code complexity |
| Test coverage (%) | Test count, test execution time |
| Lint score | Lines of code, cyclomatic complexity |
| Validation loss | Training time, GPU memory, inference latency |
| Throughput (req/s) | P99 latency, error rate, CPU usage |

If the project's benchmark/test output already emits multiple numbers, capture them all. If not, look for cheap secondary signals that can be extracted from the same run.

Present secondary metrics to the user: "I'll optimize {primary} but also track {secondary1} and {secondary2} so we can spot if improvements come at a hidden cost."

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

### 2e. Define Files in Scope and Off Limits

Explicitly categorize every relevant file into two lists — this is clearer than the vague "immutable context" framing and matches how production autoresearch setups work (see Shopify/liquid).

**Files in Scope** — files the agent reads for context and understanding:
- `README.md` — project context
- `{MUTABLE_FILE}` — the file it edits
- Config files (pyproject.toml, package.json, etc.)
- Architecture docs, type definitions
- The runner script `auto/run.sh` (read for understanding, never modify)

**Off Limits** — files the agent must never modify, listed explicitly:
- Test files and fixtures
- Benchmark scripts and data
- CI/CD configs
- The `auto/` directory (measurement pipeline)
- `results.tsv` (append-only via the logging step, never committed)

Be specific with paths. "Don't touch tests" is vague; `test/**/*.py — test suite, must continue to pass unchanged` is clear.

### 2f. Define Allowed Change Types

What kinds of mutations are fair game? Read the appropriate domain block from `references/domain-examples.md` based on the detected project type and goal.

Map goals to domains:
- ML/training → "ML / Deep Learning Training"
- Test coverage → "Test Coverage Improvement"
- Lint/quality → "Code Quality / Lint Score"
- Performance → "Performance / Benchmarks"
- Prompts → "Prompt Engineering"
- Config → "Configuration Tuning"

### 2g. Design Quality Gates

Quality gates are tiered checks that run before the benchmark, ordered fastest-first. If an early gate fails, the script exits immediately — no wasting time on a benchmark for broken code.

Design 2-3 gates based on what the project has:

| Gate | Purpose | Failure mode | Example |
|------|---------|-------------|---------|
| **Unit tests** (fast) | Correctness check | Hard fail (exit 1) | `bundle exec rake test`, `uv run pytest tests/unit -x` |
| **Conformance/lint** | Style + spec compliance | Soft fail with threshold | `ruff check --statistics`, allow ≤N known issues |
| **Type check** | Type safety | Hard fail | `uv run mypy src/`, `npx tsc --noEmit` |

For each gate, determine:
1. **Command** — what to run
2. **Failure mode** — hard fail (exit 1) or soft fail (allow up to N known issues)
3. **Threshold** — for soft fails, what's the acceptable count (based on current state)

Not every project needs all gates. A project with only unit tests gets one gate. A project with tests + lint + benchmarks gets three. Use what exists — don't add new tooling.

---

### Present the Design

After working through 2a-2g, present the complete design as a single summary:

```
## Autoloop Design

**Goal**: {what we're optimizing}
**Mutable file**: `{path}` — {description}
**Primary metric**: {metric_name} ({units}, {direction} is better)
**Secondary metrics**: {name1} ({units}), {name2} ({units}) — tracked, not optimized
**Quality gates**:
  1. {gate1_name}: `{command}` — {hard/soft fail}
  2. {gate2_name}: `{command}` — {hard/soft fail, threshold if soft}
  3. Benchmark: `{bench_command}`
**Time budget**: ~{budget} per experiment (timeout: {timeout})
**Files in scope**: {list of files the agent reads}
**Off limits**: {list of files the agent must not modify}
**Strategy**: {domain} — {brief description of change types}

Does this look right? I'll adjust anything before generating.
```

One confirmation round. The user says "looks good" or adjusts specifics.

---

## Phase 3 — Generate Runner Script and Verify Baseline

Before generating program.md, create the runner script and verify it works. This catches broken setups before the user walks away for 8 hours.

### 3a. Generate the runner script

Create the `auto/` directory and `auto/run.sh` in the target project:

```bash
mkdir -p auto
```

Read `references/runner-script-template.sh` and fill in the quality gates and metric extraction based on the design from Phase 2g.

The runner script structure:
1. **Shebang + set flags**: `#!/usr/bin/env bash` + `set -euo pipefail`
2. **cd to project root**: `cd "$(dirname "$0")/.."`
3. **Quality gates in order** (fastest first): Each gate prints a header (`=== Gate Name ===`), runs the command, and exits 1 on failure. Soft-fail gates extract a count and compare against a threshold.
4. **Benchmark**: Runs the metric-producing command
5. **METRIC output**: Prints `METRIC key=value` lines for primary and all secondary metrics

Example generated gate (hard fail):
```bash
# ── Gate 1: Unit tests (fast gate) ──────────────────────────────────
echo "=== Unit Tests ==="
if ! uv run pytest tests/unit -x > /dev/null 2>&1; then
  echo "FATAL: unit tests failed"
  exit 1
fi
```

Example generated gate (soft fail with threshold):
```bash
# ── Gate 2: Lint (conformance gate) ─────────────────────────────────
echo "=== Lint ==="
LINT_ISSUES=$(uv run ruff check --statistics 2>&1 | tail -1 | grep -oE '[0-9]+' | head -1)
LINT_ISSUES=${LINT_ISSUES:-0}
if [ "$LINT_ISSUES" -gt 5 ]; then
  echo "FATAL: lint has $LINT_ISSUES issues (threshold: 5)"
  exit 1
fi
```

Example METRIC output section:
```bash
echo "METRIC combined_us=$COMBINED"
echo "METRIC parse_us=$PARSE"
echo "METRIC render_us=$RENDER"
echo "METRIC allocations=$ALLOCS"
```

Make the script executable:
```bash
chmod +x auto/run.sh
```

### 3b. Verify baseline

Run the runner script once:

```bash
./auto/run.sh > run.log 2>&1
echo "Exit code: $?"
grep '^METRIC ' run.log
```

Check:
1. **Did the script succeed?** (exit code 0 — all quality gates passed)
2. **Are METRIC lines present?** (at least the primary metric)
3. **Are the values reasonable?** (not NaN, not 0 when it shouldn't be)

If anything fails, debug it with the user. Common issues:
- Wrong test command (missing `--cov` flag, wrong test directory)
- METRIC grep pattern doesn't match output format
- Missing dependencies (need `uv sync` first)
- Permission issues on run.sh

**Do not proceed to generation until the baseline passes.**

Report the baseline:
> "Baseline verified. All quality gates pass. Primary metric: {metric_name} = {value}. Secondary: {name1} = {value1}, {name2} = {value2}. Ready to generate program.md."

Record the baseline commit hash: `git rev-parse --short HEAD`

---

## Phase 4 — Generate program.md

Now create the program.md by filling in the template. The runner script (`auto/run.sh`) was already created and verified in Phase 3.

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
| `{OBJECTIVE_DESCRIPTION}` | 2-3 sentence description of the optimization goal with project context |
| `{MUTABLE_FILE}` | Design 2a |
| `{MUTABLE_FILE_DESCRIPTION}` | Brief description of the file's contents |
| `{WHAT_IS_FAIR_GAME}` | From domain-examples.md |
| `{IN_SCOPE_FILES_LIST}` | Design 2e — files the agent reads, formatted as `- \`path\` — description` |
| `{OFF_LIMITS_FILES_LIST}` | Design 2e — files the agent must not modify, formatted as `- \`path\` — reason` |
| `{PRECONDITIONS_CHECK}` | Any setup verification needed |
| `{EXECUTION_CONTEXT}` | Environment description (local machine, GPU, etc.) |
| `{METRIC_NAME}` | Design 2b primary metric |
| `{METRIC_KEY}` | Key used in METRIC output (e.g. `combined_us`) |
| `{METRIC_UNITS}` | Units (e.g. `µs`, `%`, `count`) |
| `{METRIC_DIRECTION}` | "lowest" or "highest" |
| `{SECONDARY_METRICS_LIST}` | Formatted as `- **Secondary**: \`name\` — description (units)` per secondary metric |
| `{SECONDARY_METRICS_PARSE_GUIDANCE}` | Instructions for parsing secondary metrics from METRIC lines |
| `{METRIC_OUTPUT_EXAMPLE}` | Example METRIC lines from baseline, e.g. `METRIC combined_us=7374\nMETRIC allocations=62620` |
| `{RESULTS_COLUMN_COUNT}` | Number of columns in results.tsv (4 + number of secondary metrics) |
| `{RESULTS_HEADER}` | TSV header row including secondary metric columns |
| `{SECONDARY_METRIC_COLUMNS}` | Numbered list entries for secondary metric columns in results.tsv |
| `{RESULTS_EXAMPLE_ROWS}` | Example TSV rows showing baseline, keep, discard, crash |
| `{RESOURCE_CONSTRAINTS}` | Memory, CPU, GPU limits if known |
| `{TIME_BUDGET}` | Design 2d |
| `{TIMEOUT_LIMIT}` | Design 2d |
| `{BASELINE_COMMIT}` | Short commit hash from Phase 3b |
| `{BASELINE_METRIC_VALUE}` | From Phase 3b |
| `{BASELINE_SECONDARY_METRICS}` | Formatted as `- **name**: value` per secondary metric |
| `{ADDITIONAL_GOAL_CONTEXT}` | Any extra framing |
| `{STRATEGY_GUIDANCE}` | Full domain block from domain-examples.md |
| `{PROGRESS_LOG_SEED}` | Empty or with just a comment: `<!-- Agent: append kept experiments here -->` |

### Step 4: Preview

Show the user the generated program.md content. Say:
> "Here's the program.md I'll write to your project root. Review it — once you confirm, I'll create the files."

### Step 5: Write files (on confirmation)

1. Write `program.md` to the project root
2. Write `results.tsv` with just the header row:
   ```
   {RESULTS_HEADER}
   ```
3. Check if `.gitignore` exists and whether `results.tsv` and `run.log` are already listed:
   - If `.gitignore` exists → append any missing entries (`results.tsv`, `run.log`)
   - If `.gitignore` doesn't exist → create it with both entries
   - If already listed → do nothing
4. Do **NOT** git commit. Leave that to the user.

---

## Phase 5 — Launch Instructions

After writing the files, print clear instructions:

```
## Ready to Launch

Your autoloop is configured. Generated files:
- `auto/run.sh` — immutable runner script (quality gates + METRIC output)
- `program.md` — the experiment loop instructions (with embedded progress log)
- `results.tsv` — empty ledger (header only)

To start:

1. Review the generated files, especially `auto/run.sh` and `program.md`.

2. Start the loop:
   ```bash
   claude --dangerously-skip-permissions -p "Read program.md and execute the loop protocol. Do not stop until I interrupt you."
   ```

3. Walk away. The agent will:
   - Create a branch (`autoloop/{tag}`)
   - Establish the baseline via `./auto/run.sh`
   - Loop: edit → run → measure → keep/revert
   - Log every experiment to results.tsv
   - Update the Progress Log in program.md for kept experiments

4. When you come back:
   ```bash
   cat results.tsv                    # See full experiment trajectory
   grep '^- ' program.md | tail -20   # See progress log of kept changes
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
The mutable artifact scope may be too broad. Narrow what the agent is allowed to change, or check that the execution environment is stable (dependencies installed, paths correct). Also check that quality gate thresholds in `auto/run.sh` aren't too strict — a threshold of 0 lint issues when the baseline has 3 will fail every time.

**"The agent modified auto/run.sh"**
The program.md explicitly forbids this, but if it happened, restore from git: `git checkout main -- auto/run.sh`. Consider adding stronger language to program.md or making the file read-only: `chmod 444 auto/run.sh`.

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
