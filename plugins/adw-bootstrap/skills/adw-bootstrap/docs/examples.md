# ADW Bootstrap Examples

This document shows real-world examples of bootstrapping ADW infrastructure in different project types.

## Example 1: Python FastAPI Project

### Before Bootstrap
```
my-api/
├── src/
│   ├── main.py
│   └── routes/
├── tests/
├── pyproject.toml
└── README.md
```

### After Bootstrap (Enhanced)
```
my-api/
├── adws/
│   ├── adw_modules/
│   │   ├── agent.py
│   │   └── agent_sdk.py
│   ├── adw_prompt.py
│   ├── adw_slash_command.py
│   └── adw_chore_implement.py
├── .claude/commands/
│   ├── chore.md         # Adapted to FastAPI
│   ├── implement.md
│   ├── feature.md
│   └── prime.md
├── specs/
├── agents/
├── .env.sample
└── CLAUDE.md            # Updated
```

### Usage
```bash
# Fast exploration with Haiku
./adws/adw_prompt.py "what authentication methods are used?" --model haiku

# Implementation with Sonnet (default)
./adws/adw_chore_implement.py "add JWT authentication"

# Security review with Opus
./adws/adw_prompt.py "review security in auth module" --model opus
```

## Example 2: Next.js TypeScript Project

### Key Adaptations
- ADW scripts remain Python (work on any project)
- Validation commands use `npm run type-check`, `npm run build`
- start.md uses `npm run dev`

### Usage
```bash
./adws/adw_chore_implement.py "add dark mode toggle"
./adws/adw_prompt.py "analyze component architecture"
```

## Example 3: Minimal Setup

Small projects get minimal setup only:
- Just agent.py and adw_prompt.py
- Basic slash commands
- Can upgrade later if needed

## Testing Your Setup

Run validation:
```bash
~/.claude/skills/adw-bootstrap/utils/validator.py
```

Try a simple prompt:
```bash
./adws/adw_prompt.py "what does this project do?"
```
