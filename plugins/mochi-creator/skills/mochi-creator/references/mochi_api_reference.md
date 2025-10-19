# Mochi API Reference

This document provides detailed reference information for the Mochi.cards API.

## Authentication

Mochi uses HTTP Basic Auth with your API key as the username (no password needed).

To get your API key:
1. Open Mochi app
2. Go to Account Settings
3. Find the API Keys section

Set the API key as an environment variable:
```bash
export MOCHI_API_KEY="your_api_key_here"
```

## Base URL

```
https://app.mochi.cards/api/
```

## Data Formats

The API supports both JSON and transit+json. This skill uses JSON for simplicity.

## Pagination

List endpoints return paginated results with:
- `docs`: Array of items
- `bookmark`: Cursor for next page (may be present even if no more pages exist)

## Cards

### Card Structure

Cards contain:
- `id`: Unique identifier
- `content`: Markdown content
- `deck-id`: Parent deck ID
- `template-id`: Optional template ID
- `fields`: Map of field IDs to values (when using templates)
- `tags`: Set of tags extracted from content
- `manual-tags`: Set of tags added manually
- `archived?`: Boolean indicating archived status
- `trashed?`: Timestamp if trashed (soft delete)
- `review-reverse?`: Whether to review in reverse
- `pos`: Lexicographic position for sorting
- `created-at`: Creation timestamp
- `updated-at`: Last modification timestamp
- `reviews`: Array of review history
- `references`: Set of references to other cards

### Card Content

Card content is markdown with some special features:
- `---` creates a card side separator (for multi-sided cards)
- `@[title](url)` creates references to other cards or external links
- `![](@media/filename.png)` embeds attachments
- `#tag` adds tags inline
- `<< Field name >>` in templates gets replaced by field values

### Positioning Cards

The `pos` field determines card order within a deck using lexicographic sorting:
- If card A has `pos` of `"6"` and card B has `pos` of `"7"`
- To insert between them, use `pos` of `"6V"` (any string between "6" and "7")
- Common pattern: use letters like `"a"`, `"b"`, `"c"` for initial cards, then insert with decimals or additional letters

### Card Attachments

Attachments can be added to cards using multipart/form-data:
- POST `/cards/{card-id}/attachments/{filename}`
- DELETE `/cards/{card-id}/attachments/{filename}`

Attachments are referenced in card content using `@media/` syntax.

## Decks

### Deck Structure

Decks contain:
- `id`: Unique identifier
- `name`: Deck name
- `parent-id`: Optional parent deck for nesting
- `sort`: Numeric sort order (decks sorted by this number)
- `archived?`: Boolean indicating archived status
- `trashed?`: Timestamp if trashed (soft delete)
- `sort-by`: How cards are sorted in the deck
- `cards-view`: How cards are displayed
- `show-sides?`: Whether to show all card sides
- `sort-by-direction`: Boolean to reverse sort order
- `review-reverse?`: Whether to review cards in reverse

### Sort-by Options

How cards are sorted within the deck:
- `none`: Manual ordering (using `pos` field)
- `lexicographically` or `lexigraphically`: Alphabetically by name
- `created-at`: By creation date
- `updated-at`: By last modification date
- `retention-rate-asc`: By retention rate (ascending)
- `interval-length`: By review interval length

### Cards-view Options

How cards are displayed in the deck:
- `list`: Traditional list view
- `grid`: Grid/tile layout
- `note`: Note-taking view
- `column`: Column layout

### Deck Hierarchy

Decks can be nested using the `parent-id` field to create organizational hierarchies.

## Templates

### Template Structure

Templates define card structure using fields:
- `id`: Unique identifier
- `name`: Template name (1-64 characters)
- `content`: Markdown with field placeholders
- `pos`: Lexicographic position for sorting
- `fields`: Map of field definitions
- `style`: Visual styling options
- `options`: Template behavior options

### Field Placeholders

In template content, use `<< Field name >>` to insert field values.

### Field Types

Available field types:
- `text`: Simple text input
- `boolean`: True/false checkbox
- `number`: Numeric input
- `draw`: Drawing/sketch input
- `ai`: AI-generated content
- `speech`: Speech/audio recording
- `image`: Image upload
- `translate`: Translation field
- `transcription`: Audio transcription
- `dictionary`: Dictionary lookup
- `pinyin`: Chinese pinyin
- `furigana`: Japanese reading aid

### Field Definition Structure

Each field is defined as:
```json
{
  "id": "field-id",
  "name": "Display Name",
  "type": "text",
  "pos": "a",
  "content": "Default or instruction text",
  "options": {
    "multi-line?": true,
    "hide-term": false
  }
}
```

### Common Field Options

- `multi-line?`: Allow multi-line text input
- `hide-term`: Hide the term in certain views
- `ai-task`: Instructions for AI-generated fields
- Various type-specific options

### Template Style Options

```json
{
  "text-alignment": "left"  // or "center", "right"
}
```

### Template Options

```json
{
  "show-sides-separately?": false  // Show template sides separately during review
}
```

### Example Template

Basic flashcard template:
```json
{
  "name": "Basic Flashcard",
  "content": "# << Front >>\\n---\\n<< Back >>",
  "fields": {
    "front": {
      "id": "front",
      "name": "Front",
      "type": "text",
      "pos": "a"
    },
    "back": {
      "id": "back",
      "name": "Back",
      "type": "text",
      "pos": "b",
      "options": {
        "multi-line?": true
      }
    }
  }
}
```

## Common Patterns

### Creating Simple Flashcards

For simple flashcards, use markdown content with `---` separator:
```markdown
# Question here
---
Answer here
```

### Creating Template-Based Cards

1. First retrieve or create a template
2. Get the field IDs from the template
3. Create card with field values matching the template structure

### Batch Operations

To create multiple cards:
1. List existing decks to get deck ID
2. Loop through content items
3. Create cards one at a time (API doesn't support batch creation)

### Organizing with Tags

Tags can be added two ways:
1. Inline in content: `#python #programming`
2. Using `manual-tags` field: `["python", "programming"]` (without # prefix)

Manual tags are useful when you want tags separate from content.

### Soft Delete vs Hard Delete

- **Soft delete**: Set `trashed?` to current ISO 8601 timestamp
- **Hard delete**: Use DELETE endpoint (permanent, cannot be undone)

Soft delete is recommended for safety.

## Error Handling

HTTP Status Codes:
- `2xx`: Success
- `4xx`: Client error (missing parameters, validation failure, not found)
- `5xx`: Server error (rare)

Error responses include:
```json
{
  "errors": {
    "field-name": "Error message for this field"
  }
}
```

Or for general errors:
```json
{
  "errors": ["Error message"]
}
```

## Rate Limiting

The API documentation doesn't specify rate limits, but follow good practices:
- Don't make excessive requests in short periods
- Implement exponential backoff on errors
- Cache deck/template lists when possible

## Best Practices

1. **Use Templates**: For consistent card structure, create templates
2. **Organize with Decks**: Create hierarchical deck structures
3. **Tag Consistently**: Use consistent tag naming conventions
4. **Soft Delete First**: Use trashed? instead of permanent deletion
5. **Position Strategically**: Use the `pos` field for custom ordering
6. **Validate Content**: Check markdown syntax before creating cards
7. **Handle Pagination**: Always check for and handle `bookmark` in list responses
8. **Store IDs**: Keep track of deck and template IDs for reuse
