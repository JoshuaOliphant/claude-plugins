---
type: llm
weight: 2
---
The response drafts flashcards for CAP theorem, eventual consistency, and partition
tolerance, and those cards show the 5 properties of effective prompts:

- **Focused**: each card asks about exactly one idea. A card that bundles "what is CAP
  and what are its tradeoffs and when do you pick AP" fails.
- **Precise**: the question admits one specific answer. "Tell me about consistency" fails.
- **Consistent**: the same question would pull the same answer on every review, not a
  different fragment each time.
- **Tractable**: answerable in a few seconds by someone who has read the chapter.
- **Effortful**: requires actual retrieval. A card whose answer is given away by the
  question, or that can be answered by recognition alone, fails.

Pass only if most drafted cards clear all five. A response that produces one long
summary card, or a list of topics rather than question/answer pairs, fails.
