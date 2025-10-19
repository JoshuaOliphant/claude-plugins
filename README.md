# Claude Code Plugin Marketplace

A collection of Claude Code plugins for productivity and learning workflows.

## Available Plugins

### mochi-creator

Create and manage Mochi.cards flashcards, decks, and templates via API.

**Features:**
- Create simple flashcards from markdown content
- Build template-based cards with custom fields
- Manage deck hierarchies and organization
- Batch operations from documents and conversations
- Interactive card creation workflows

**Requirements:**
- Mochi.cards account and API key
- Python with `requests` library

**Installation:**

```bash
# Add this marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install the plugin
/plugin install mochi-creator@oliphant-plugins
```

**Setup:**

Set your Mochi API key as an environment variable:
```bash
export MOCHI_API_KEY="your_api_key_here"
```

To get your API key:
1. Open Mochi.cards application
2. Navigate to Account Settings
3. Find the API Keys section
4. Generate a new API key

**Usage Examples:**

- "Create a Mochi card about Python decorators"
- "Turn this conversation into flashcards"
- "Create a deck for studying Spanish vocabulary"
- "Make template-based cards with word, definition, and example"

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

MIT
