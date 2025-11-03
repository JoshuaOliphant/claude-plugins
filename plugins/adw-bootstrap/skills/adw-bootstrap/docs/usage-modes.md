# ADW Usage Modes: Subscription vs API

## Overview

ADW infrastructure supports two distinct usage modes, enabling both interactive development and automated workflows without code changes.

## Mode A: Claude Max Subscription

### What It Is

Run Claude Code through your Claude Max subscription without needing API keys.

### How It Works

```
User with Claude Max subscription
    ↓
Logged in to Claude Code CLI
    ↓
ADW executes: claude -p "prompt"
    ↓
Claude Code uses subscription auth
    ↓
Prompt executed, results returned
```

No API key configuration needed - authentication happens automatically through your subscription.

### Setup

**Zero configuration required:**

```bash
# Just run the ADWs
./adws/adw_prompt.py "analyze this code"

# No .env file needed
# No API key needed
# Works immediately
```

### Requirements

- Active Claude Max subscription
- Claude Code CLI installed and logged in
- User must be authenticated

### Advantages

✅ **Simple** - No configuration, just works
✅ **Secure** - No API keys to manage
✅ **Interactive** - Perfect for development
✅ **Immediate** - No setup friction

### Limitations

❌ **User presence required** - Can't run headless
❌ **Single user** - Tied to your subscription
❌ **Limited automation** - Not ideal for CI/CD
❌ **Session-dependent** - Must be logged in

### Perfect For

- Interactive development
- Local experimentation
- Learning ADWs
- Personal projects
- Quick prototyping

### Example Workflow

```bash
# Morning: Start development
./adws/adw_chore_implement.py "add user authentication"

# Afternoon: Create another feature
./adws/adw_chore_implement.py "implement password reset"

# Evening: Code review
./adws/adw_prompt.py "review security in auth module"

# All executed through your subscription
# No API key management
# Just works
```

## Mode B: API-Based Programmatic Execution

### What It Is

Run Claude Code programmatically using API keys for automated, headless workflows.

### How It Works

```
Environment has ANTHROPIC_API_KEY
    ↓
ADW reads API key from environment
    ↓
ADW executes: claude -p "prompt"
    ↓
Claude Code uses API key for auth
    ↓
Prompt executed, results returned
```

API key is passed through filtered environment to subprocess.

### Setup

**Step 1: Create .env file**

```bash
# Copy template
cp .env.sample .env

# Edit .env
nano .env
```

**Step 2: Add your API key**

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional configurations
CLAUDE_CODE_PATH=claude
CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=true
```

**Step 3: Secure the file**

```bash
# Never commit .env
echo ".env" >> .gitignore

# Restrict permissions
chmod 600 .env
```

### Requirements

- Anthropic API key (from console.anthropic.com)
- API access enabled on account
- Claude Code CLI installed

### Advantages

✅ **Headless** - Runs without user interaction
✅ **Automatable** - Perfect for CI/CD
✅ **Multi-user** - Not tied to single subscription
✅ **Scriptable** - Full programmatic control
✅ **Reliable** - No session dependencies

### Limitations

❌ **Requires API key** - Additional setup
❌ **Costs** - API usage charges
❌ **Key management** - Security consideration
❌ **Environment config** - Must configure .env

### Perfect For

- CI/CD pipelines
- Webhook handlers
- Scheduled tasks (cron jobs)
- Server-side automation
- Team automation workflows
- Production deployments

### Example Workflows

#### CI/CD Integration

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up environment
        run: |
          echo "ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }}" > .env

      - name: Run AI review
        run: |
          ./adws/adw_prompt.py "review this PR for security issues"
```

#### Webhook Handler

```python
# webhook_server.py
from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/webhook/feature-request', methods=['POST'])
def handle_feature_request():
    data = request.json
    description = data['description']

    # Execute ADW with API key from environment
    subprocess.run([
        './adws/adw_chore_implement.py',
        description
    ])

    return {'status': 'processing'}
```

#### Cron Job

```bash
# crontab -e

# Run daily code quality check at 2 AM
0 2 * * * cd /path/to/project && ./adws/adw_prompt.py "analyze code quality and suggest improvements" >> /var/log/adw-daily.log 2>&1
```

## Mode Detection

The ADW infrastructure automatically detects which mode to use:

```python
# In agent.py
def get_safe_subprocess_env():
    env = {
        # System variables
        "HOME": os.getenv("HOME"),
        "PATH": os.getenv("PATH"),
        # ...
    }

    # Only add API key if it exists
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key

    # If no API key, Claude Code uses subscription
    return env
```

**Detection logic:**
1. Check if `ANTHROPIC_API_KEY` exists in environment
2. If yes → API mode (pass key to subprocess)
3. If no → Subscription mode (Claude Code uses logged-in session)

**No code changes needed** - same scripts work in both modes.

## Comparison Matrix

| Feature | Subscription Mode | API Mode |
|---------|------------------|----------|
| **Setup Complexity** | None | Moderate (API key) |
| **User Presence** | Required | Not required |
| **CI/CD Integration** | ❌ Difficult | ✅ Easy |
| **Cost** | Subscription price | API usage charges |
| **Security** | No key to manage | Must secure API key |
| **Automation** | Limited | Full |
| **Interactive Use** | ✅ Excellent | ✅ Works fine |
| **Headless Use** | ❌ Not practical | ✅ Perfect |
| **Multi-user** | Per subscription | Shared key possible |
| **Session Management** | Must stay logged in | None needed |

## Switching Between Modes

### Subscription → API

```bash
# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
EOF

# Secure it
chmod 600 .env

# Now all ADW executions use API
./adws/adw_prompt.py "test"
```

### API → Subscription

```bash
# Remove .env file
rm .env

# Or comment out API key
# ANTHROPIC_API_KEY=sk-ant-...

# Now all ADW executions use subscription
./adws/adw_prompt.py "test"
```

**Same scripts work in both modes** - just change environment.

## Best Practices

### For Subscription Mode

1. **Stay logged in**
   ```bash
   # Check auth status
   claude --version
   ```

2. **Personal projects**
   - Use for local development
   - No .env file needed

3. **Quick iteration**
   - Fast setup
   - Immediate feedback

### For API Mode

1. **Secure your keys**
   ```bash
   # Never commit
   echo ".env" >> .gitignore

   # Restrict permissions
   chmod 600 .env

   # Use secrets management in production
   ```

2. **Rotate regularly**
   ```bash
   # Update API key periodically
   # Revoke old keys
   ```

3. **Monitor usage**
   - Track API consumption
   - Set up billing alerts
   - Monitor costs

4. **Use environment-specific keys**
   ```bash
   # Development
   ANTHROPIC_API_KEY=sk-ant-dev-...

   # Production
   ANTHROPIC_API_KEY=sk-ant-prod-...
   ```

### For Both Modes

1. **Document which mode you're using**
   ```markdown
   # README.md

   ## Setup

   This project uses Claude Max subscription mode by default.
   For CI/CD, configure ANTHROPIC_API_KEY in .env.
   ```

2. **Test in both modes**
   - Ensure portability
   - Validate automation path
   - Document differences

3. **Choose based on use case**
   - Interactive development → Subscription
   - Automation/CI/CD → API
   - Both are valid

## Troubleshooting

### Subscription Mode Issues

**Problem**: "Authentication failed"
```bash
# Solution: Re-login to Claude Code
claude login
```

**Problem**: "Command not found: claude"
```bash
# Solution: Install Claude Code CLI
# [Installation instructions]
```

**Problem**: "Session expired"
```bash
# Solution: Re-authenticate
claude logout
claude login
```

### API Mode Issues

**Problem**: "Invalid API key"
```bash
# Solution: Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Verify key format: sk-ant-api03-...
# Get new key from console.anthropic.com
```

**Problem**: "API key not found"
```bash
# Solution: Ensure .env is loaded
# Check file location
ls -la .env

# Verify environment
echo $ANTHROPIC_API_KEY
```

**Problem**: "Rate limit exceeded"
```bash
# Solution: Implement backoff or use subscription mode
# Reduce parallel executions
# Contact Anthropic for higher limits
```

## Security Considerations

### Subscription Mode

✅ **Secure by default** - No secrets to manage
✅ **Session-based** - Expires automatically
✅ **User-specific** - Can't be shared accidentally

⚠️ **Physical access** - Anyone with terminal access can use
⚠️ **Session hijacking** - Theoretical risk in shared environments

### API Mode

✅ **Revocable** - Can disable keys anytime
✅ **Trackable** - Monitor usage per key
✅ **Rotatable** - Easy to update

⚠️ **Key exposure** - Must protect .env file
⚠️ **Commit risk** - Can accidentally commit
⚠️ **Scope risk** - Key has broad permissions

### Protection Strategies

1. **For .env files**
   ```bash
   # Always in .gitignore
   echo ".env" >> .gitignore

   # Restrict permissions
   chmod 600 .env

   # Use git secrets scanning
   git secrets --scan
   ```

2. **For production**
   ```bash
   # Use secrets managers
   - AWS Secrets Manager
   - HashiCorp Vault
   - GitHub Secrets

   # Not .env files in production
   ```

3. **For CI/CD**
   ```yaml
   # Use repository secrets
   secrets:
     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

   # Never hardcode
   # Never commit
   ```

## Recommendation

**Start with Subscription Mode**
- Simpler setup
- Perfect for learning
- Great for development
- Zero configuration

**Migrate to API Mode when needed**
- Adding CI/CD
- Implementing webhooks
- Scheduling tasks
- Production deployment

**Keep both available**
- Developers use subscription
- Automation uses API
- Best of both worlds

Same ADW infrastructure supports both - choose based on context.
