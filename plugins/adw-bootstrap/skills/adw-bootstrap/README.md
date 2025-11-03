# ADW Bootstrap Skill

A Claude skill that intelligently bootstraps **AI Developer Workflows (ADWs)** infrastructure in any codebase, enabling programmatic agent orchestration for automated development.

## What It Does

Transforms a regular project into one where AI agents can be invoked programmatically to plan, implement, test, and deploy features.

**After setup, you can:**
- Execute prompts programmatically: `./adws/adw_prompt.py "implement feature X"`
- Use reusable templates: `./adws/adw_slash_command.py /chore "task"`
- Orchestrate multi-phase workflows: Plan → Implement → Test
- Track agent behavior with structured outputs in `agents/{id}/`
- Scale compute for parallel development

## Installation

### User Skill (Personal Use)

```bash
# Clone or copy this skill to your Claude skills directory
cp -r adw-bootstrap ~/.claude/skills/

# Or create symlink
ln -s /path/to/adw-bootstrap ~/.claude/skills/adw-bootstrap
```

### Verify Installation

The skill should appear when you type `/skills` in Claude Code.

## Usage

### Automatic Trigger

The skill activates when you say:
- "Set up ADWs"
- "Bootstrap agentic workflows"
- "Add AI developer workflows"
- "Enable programmatic agent execution"
- "Initialize ADW infrastructure"

### Manual Invocation

```bash
# In Claude Code
/adw-bootstrap

# Or invoke the skill programmatically
adw-bootstrap
```

### Options

During setup, Claude will:
1. Analyze your project structure
2. Recommend a setup phase (minimal/enhanced/scaled)
3. Ask for confirmation
4. Create adapted infrastructure
5. Validate the setup

## What Gets Created

### Minimal Setup (Always)
```
your-project/
├── adws/
│   ├── adw_modules/
│   │   └── agent.py          # Core subprocess execution
│   └── adw_prompt.py          # CLI wrapper
├── .claude/commands/
│   ├── chore.md              # Planning template
│   └── implement.md          # Implementation template
├── specs/                     # Implementation plans
├── agents/                    # Output observability
└── .env.sample               # Configuration template
```

### Enhanced Setup (Recommended)
Adds:
- `agent_sdk.py` - SDK-based execution
- `adw_slash_command.py` - Command executor
- `adw_chore_implement.py` - Compound workflows
- Additional slash commands (feature.md, prime.md, start.md)

### Scaled Setup (Production)
Adds:
- State management (`state.py`, `adw_state.json`)
- Git operations (`git_ops.py`)
- Worktree isolation (`worktree_ops.py`, `trees/`)
- GitHub integration (`github.py`)
- Workflow orchestration (`workflow_ops.py`)
- Multi-phase workflows (`adw_sdlc_iso.py`, `adw_ship_iso.py`)
- Advanced slash commands (20+ commands)
- Testing infrastructure

## Upgrading Existing ADW Setup

If you already have ADWs in your project, the skill can upgrade to a higher phase:

### Upgrade Triggers

Say:
- "Upgrade my ADWs to enhanced"
- "Add scaled ADW capabilities"
- "Upgrade ADW infrastructure"

### Upgrade Process

The skill will:
1. **Detect** current phase (minimal/enhanced/scaled)
2. **Report** what infrastructure you have
3. **Recommend** available upgrades
4. **Backup** existing setup (`.adw_backups/`)
5. **Add** new capabilities without overwriting customizations
6. **Validate** the upgrade
7. **Report** what was added

**Safety Features:**
- Never overwrites customized files
- Creates timestamped backups
- Shows what will change before upgrading
- Rollback capability if upgrade fails

### Example Upgrade Output

```
🔍 Existing ADW setup detected!

Current Phase: Enhanced

Found infrastructure:
- Core modules: agent.py, agent_sdk.py
- CLI scripts: adw_prompt.py, adw_sdk_prompt.py, adw_slash_command.py
- Slash commands: 7 commands
- Workflows: 2 workflows

Available upgrades:
- Scaled: Adds state management, worktree isolation, GitHub integration,
  multi-phase workflows, and 15+ advanced commands

Would you like to upgrade to Scaled? (y/n)
```

After confirmation:
```
✅ Created backup in .adw_backups/20251103_102530/

Adding Scaled capabilities:
✅ Added adws/adw_modules/state.py
✅ Added adws/adw_modules/git_ops.py
✅ Added adws/adw_modules/worktree_ops.py
✅ Added adws/adw_modules/workflow_ops.py
✅ Added adws/adw_modules/github.py
✅ Added adws/adw_sdlc_iso.py
✅ Added 15 new slash commands
⚠️  Preserved customized: adws/adw_prompt.py

🎉 Upgrade to Scaled completed successfully!

Try the new capabilities:
- ./adws/adw_sdlc_iso.py 123  # Complete SDLC for issue #123
- ./adws/adw_ship_iso.py 123 abc12345  # Ship changes to main
```

## Usage After Bootstrap

### Execute Prompts
```bash
./adws/adw_prompt.py "analyze this code"
./adws/adw_prompt.py "quick syntax check" --model haiku
./adws/adw_prompt.py "refactor for performance" --model opus
```

Three models available:
- `haiku` - Fast & economical (2x speed, 1/3 cost)
- `sonnet` - Balanced excellence (default)
- `opus` - Maximum intelligence

### Use Slash Commands
```bash
# Create a plan
./adws/adw_slash_command.py /chore abc123 "add logging"

# Implement a plan
./adws/adw_slash_command.py /implement specs/chore-abc123-*.md
```

### Compound Workflows
```bash
# Plan + implement in one command
./adws/adw_chore_implement.py "add error handling to API"
```

## Validation

After setup, validate with:

```bash
# Run validation suite
~/.claude/skills/adw-bootstrap/utils/validator.py

# With test execution
~/.claude/skills/adw-bootstrap/utils/validator.py --test
```

## Documentation

- **SKILL.md** - Main skill logic and instructions
- **docs/principles.md** - Core ADW concepts and philosophy
- **docs/architecture.md** - Technical architecture deep dive
- **docs/usage-modes.md** - Subscription vs API modes
- **docs/examples.md** - Real-world bootstrap examples
- **reference/** - Working code examples for adaptation

## Key Features

### 1. Intelligent Adaptation
- Analyzes project structure and conventions
- Adapts reference code to fit the target project
- Handles novel structures without rigid templates

### 2. Progressive Enhancement
- Start minimal, add features as needed
- Clear upgrade path (minimal → enhanced → scaled)
- No over-engineering

### 3. Mode Flexibility
- **Subscription Mode**: No API key needed, perfect for development
- **API Mode**: Headless automation for CI/CD, webhooks, cron jobs
- Same infrastructure supports both

### 4. Project Agnostic
- Works on Python, TypeScript, Go, Rust, polyglot projects
- Adapts to any framework or structure
- Handles monorepos and single packages

### 5. Built-in Observability
- Structured outputs in `agents/{id}/`
- Multiple formats (JSONL, JSON, summaries)
- Debug agent behavior easily

## Architecture

### Two-Layer Model

**Agentic Layer** (`adws/`, `.claude/`, `specs/`)
- Templates engineering patterns
- Teaches agents how to operate
- Orchestrates workflows

**Application Layer** (`apps/`, `src/`, etc.)
- Your actual application code
- What agents read and modify

### Subprocess vs SDK

- **Subprocess** (agent.py): Simple, universal, minimal dependencies
- **SDK** (agent_sdk.py): Type-safe, async/await, interactive sessions

Both work seamlessly in the same infrastructure.

## Requirements

- **Claude Code CLI** installed and accessible
- **Python 3.10+** for ADW scripts
- **ANTHROPIC_API_KEY** (optional, for API mode)
- **uv** (recommended) or other Python package manager

## Troubleshooting

### Skill doesn't trigger
- Check skill is in `~/.claude/skills/adw-bootstrap/`
- Verify SKILL.md has frontmatter with trigger phrases
- Try manual invocation: `/adw-bootstrap`

### Bootstrap fails
- Ensure Claude Code CLI is installed: `claude --version`
- Check project directory is readable
- Look for error messages in Claude's response

### Validation fails
- Run: `~/.claude/skills/adw-bootstrap/utils/validator.py`
- Check specific failures and fix issues
- Ensure scripts are executable: `chmod +x adws/*.py`

### Scripts don't execute
- Make executable: `chmod +x adws/adw_prompt.py`
- Check Python version: `python --version` (need 3.10+)
- For uv scripts, ensure uv is installed: `uv --version`

## Examples

### Bootstrap Python Project
```
"Set up ADWs in this FastAPI project"
→ Analyzes pyproject.toml, detects FastAPI
→ Creates enhanced setup with uv
→ Adapts validation to use pytest, ruff
→ Ready to use!
```

### Bootstrap TypeScript Project
```
"Initialize AI developer workflows"
→ Analyzes package.json, detects Next.js
→ Creates enhanced setup
→ Adapts validation to use npm scripts
→ Python ADWs work on TypeScript code!
```

### Upgrade Existing Setup
```
"Upgrade my ADW setup to enhanced"
→ Detects existing minimal setup
→ Adds SDK support and compound workflows
→ Preserves existing customizations
→ Enhanced features now available!
```

## Development

### Testing the Skill

```bash
# Test on this project (dog-fooding)
cd /path/to/project
# In Claude Code:
"Set up ADWs here"

# Validate
~/.claude/skills/adw-bootstrap/utils/validator.py

# Try it
./adws/adw_prompt.py "test prompt"
```

### Modifying Reference Code

Reference implementations in `reference/` are copied to target projects. To update:

1. Modify files in `reference/`
2. Test changes in a sample project
3. Update SKILL.md instructions if needed
4. Document changes in this README

### Adding New Features

To add new capabilities:

1. **New ADW script**: Add to `reference/enhanced/` or `reference/scaled/`
2. **New slash command**: Add to `reference/*/commands/`
3. **Update SKILL.md**: Add instructions for adaptation
4. **Update docs**: Document the feature

## Philosophy

> "Template your engineering patterns, teach agents how to operate your codebase, scale compute to scale impact."

ADWs represent a paradigm shift from **writing code yourself** to **teaching agents to write code**. This skill makes that paradigm accessible to any project.

## License

This skill is part of the ADW framework project.

## Contributing

Improvements welcome! Key areas:

- Additional reference implementations
- Project type adapters
- Enhanced validation
- More examples
- Better documentation

## Support

- Check documentation in `docs/`
- Review examples in `docs/examples.md`
- Validate setup with `utils/validator.py`
- Read generated CLAUDE.md in target projects

## Version

1.0.0 - Initial release

## Credits

Built from the patterns developed in the tac8_app1__agent_layer_primitives project, extracting universal patterns for any codebase.
