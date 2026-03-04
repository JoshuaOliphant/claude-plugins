# Edge Case Checklist

Structured probing questions for discovering edge cases during acceptance criteria authoring. Organized by domain. Use these as conversation prompts — present as questions, not assertions.

## Input Validation

- What should happen when required fields are empty?
- What should happen when input exceeds maximum length?
- What should happen when input contains special characters (unicode, emoji, HTML, SQL)?
- What should happen when numeric input is zero, negative, or extremely large?
- What should happen when date input is in the past? Far future? Feb 29?
- What should happen when the user submits the form twice rapidly (double-click)?
- What should happen when input contains leading/trailing whitespace?
- What should happen when the user pastes formatted text into a plain text field?

## Authentication and Authorization

- What should happen when an unauthenticated user tries this action?
- What should happen when a user's session expires mid-action?
- What should happen when a user's permissions change while they're on the page?
- What should happen when multiple roles exist — who can and can't do this?
- What should happen when a user tries to access another user's resource?
- What should happen when an API key is invalid or revoked?
- What should happen when the user logs in from a new device?

## State Integrity

- What should happen when the resource has been deleted by someone else?
- What should happen when the resource has been modified since the user loaded it?
- What should happen when the operation is performed on a resource in an unexpected state?
- What should happen when a multi-step process is abandoned halfway through?
- What should happen when the user navigates back after completing an action?
- What should happen when the same action is performed twice (idempotency)?

## Concurrency and Timing

- What should happen when two users modify the same resource simultaneously?
- What should happen when a long-running operation times out?
- What should happen when the user refreshes during an async operation?
- What should happen when a webhook or callback arrives before the primary operation completes?
- What should happen when the system receives requests faster than it can process them?

## Boundary Conditions

- What should happen with zero items? One item? Maximum items?
- What should happen at the first and last page of paginated results?
- What should happen when storage or quota limits are reached?
- What should happen at the start and end of a time window (midnight, DST transitions)?
- What should happen when the list/collection is empty vs. populated?

## Error Handling

- What should happen when the database is unreachable?
- What should happen when an external API returns an error?
- What should happen when an external API is slow (> 5s response)?
- What should happen when disk space is exhausted?
- What should happen when an email fails to send?
- What should happen when a payment processor declines the transaction?
- What should the user see vs. what should be logged for each error?

## External Dependencies

- What should happen when a third-party service is down?
- What should happen when a webhook delivery fails?
- What should happen when the CDN is unreachable?
- What should happen when the file storage service returns an error?
- What should happen when DNS resolution fails?
- What should happen when TLS certificate validation fails?

## UX States

- What should happen during loading (spinner, skeleton, progressive)?
- What should happen on the empty state (no data yet)?
- What should happen on the error state (operation failed)?
- What should happen on the success state (operation completed)?
- What should happen on the partial state (some items succeeded, some failed)?
- What should happen when the user is offline or connectivity drops?
- What should happen when the user resizes the browser or rotates their device?
- What should happen when the user uses keyboard navigation or screen reader?
