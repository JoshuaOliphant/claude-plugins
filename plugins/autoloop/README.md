# autoloop

Generate self-improving experiment loops driven by `program.md` files.

## What It Does

Autoloop takes Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) pattern
and generalizes it to any domain. You describe what you want to optimize, the skill explores
your codebase, designs the loop parameters, and generates a ready-to-run `program.md`.

The pattern: an LLM agent loops autonomously — edit code, run experiment, parse a scalar
metric, git commit (keep) or git reset (revert). No orchestration code. The `program.md`
IS the entire system. The LLM's own tool-use loop IS the experiment loop.

## Usage

```
/autoloop
```

Or trigger naturally:
- "Set up an autoloop for this project"
- "I want to improve test coverage overnight"
- "Can we automate trying different approaches?"
- "Optimize this while I sleep"

The skill walks through 5 phases:

1. **Scout** — Haiku agent explores your project (build system, tests, metrics)
2. **Design** — Maps your goal onto the 5 essential loop components
3. **Verify** — Runs the metric extraction once to confirm it works
4. **Generate** — Creates `program.md` and `results.tsv`
5. **Launch** — Prints the exact command to start the autonomous loop

## Supported Domains

- **ML/DL training** — hyperparameters, architecture, optimizer tuning
- **Test coverage** — edge cases, parameterized tests, untested branches
- **Code quality** — lint score, refactoring, complexity reduction
- **Performance** — algorithmic improvements, caching, benchmarks
- **Prompt engineering** — few-shot examples, structure, sampling parameters
- **Configuration tuning** — parameter sweeps, load testing

## The Five Essential Components

Every autoloop needs these mapped correctly:

| # | Component | Example |
|---|-----------|---------|
| 1 | Mutable artifact | `train.py`, `src/model.py` |
| 2 | Immutable context | `README.md`, config files, eval harness |
| 3 | Scalar metric | `val_bpb`, coverage %, lint errors |
| 4 | Execution step | `uv run pytest --cov`, `cargo bench` |
| 5 | Checkpoint/rollback | `git commit` / `git reset` |

## Running the Loop

After generation:

```bash
claude --dangerously-skip-permissions -p "Read program.md and execute the loop protocol. Do not stop until I interrupt you."
```

The agent creates a branch, establishes a baseline, then loops indefinitely.

## Background

- [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — 126 experiments overnight
- [Agentic Experiment Loop Pattern](../../resources/learning/agentic-experiment-loop-pattern.md) — full analysis
- [Program.md Template](../../resources/learning/agentic-experiment-loop-template.md) — generic template

## License

MIT
