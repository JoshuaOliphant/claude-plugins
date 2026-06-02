# Prompt Design Principles - Deep Dive

This document provides comprehensive background on the cognitive science and research behind effective spaced repetition prompt design, based on Andy Matuschak's research and extensive literature review.

## Table of Contents

- [Core Mechanism: Retrieval Practice](#core-mechanism-retrieval-practice)
- [The Five Properties Explained](#the-five-properties-explained)
- [Knowledge Type Strategies](#knowledge-type-strategies)
- [Cognitive Science Background](#cognitive-science-background)
- [Common Failure Modes](#common-failure-modes)
- [Advanced Techniques](#advanced-techniques)
- [Research References](#research-references)

## Core Mechanism: Retrieval Practice

### What Makes Spaced Repetition Work?

Spaced repetition works through **retrieval practice** - the act of actively recalling information from memory strengthens that memory more effectively than passive review (re-reading).

**Key Research Finding** (Roediger & Karpicke, 2006):
- Students who practiced retrieval remembered 50% more after one week than students who only re-read material
- This effect persisted even when retrieval practice took less total time
- The benefit increased with longer retention intervals

### Why Prompts Matter

When you write a prompt in a spaced repetition system, you are giving your future self a recurring task. **Prompt design is task design.**

A poorly designed prompt creates a recurring task that:
- Doesn't actually strengthen the memory you care about
- Wastes time through false positives (answering without knowing)
- Creates interference through inconsistent retrievals
- Leads to abandonment through boredom

A well-designed prompt creates a recurring task that:
- Precisely targets the knowledge you want to retain
- Builds robust understanding resistant to forgetting
- Takes minimal time (10-30 seconds per year)
- Feels meaningful and connected to your goals

## The Five Properties Explained

### 1. Focused: One Detail at a Time

**Principle**: Each prompt should test exactly one piece of knowledge.

**Why it matters**: When a prompt tests multiple details simultaneously, you may successfully retrieve some but not others. This creates "partial lighting" - some mental "bulbs" light up, others don't. Your brain interprets this as success, but critical knowledge remains unstrengthened.

**The "bulbs" metaphor**: Imagine your full understanding of a concept as a string of light bulbs. Each bulb represents one aspect:
- What it is
- What it does
- When to use it
- How it differs from similar concepts
- Why it matters

An unfocused prompt like "Explain dependency injection" might light some bulbs but leave others dark. You'll feel like you "know" it, but gaps remain.

**Research basis**: Testing effect research (Roediger et al.) shows that retrieval must be specific to be effective. Vague retrievals don't strengthen specific memory traces.

**Practical example**:

❌ Unfocused:
```
Q: What is Redux and how does it work?
A: State management library, uses actions and reducers, maintains single store
```

This tests 3+ concepts:
- What Redux is (category)
- What actions are
- What reducers are
- What the single store principle is

✅ Focused - break into 4 cards:
```
Q: What category of library is Redux?
A: State management library

Q: What two mechanisms does Redux use to update state?
A: Actions (describe changes) and reducers (apply changes)

Q: What is the "single source of truth" principle in Redux?
A: All state lives in one store object

Q: What problem does Redux's unidirectional data flow solve?
A: Makes state changes predictable and debuggable
```

### 2. Precise: Specific Questions, Specific Answers

**Principle**: Questions should be specific about what they're asking for. Answers should be unambiguous.

**Why it matters**: Vague questions elicit vague answers. Vague retrievals are shallow retrievals. Shallow retrievals don't build strong memories.

**The precision spectrum**:
- **Too vague**: "What's important about X?"
- **Better**: "What benefit does X provide?"
- **Best**: "What specific problem does X solve in [context]?"

**Vague language to avoid**:
- "Interesting" - interesting to whom? In what way?
- "Important" - important for what purpose?
- "Good"/"bad" - by what criteria?
- "Tell me about" - what specifically?
- "Describe" - describe which aspect?

**Research basis**: The "transfer appropriate processing" principle (Morris et al., 1977) shows that memory retrieval is most effective when the retrieval context matches the encoding context. Precision in both creates stronger bonds.

**Practical example**:

❌ Vague:
```
Q: What's important about the async/await pattern?
A: Makes asynchronous code easier to read
```

Problems:
- "Important" is subjective
- "Easier to read" compared to what?
- Doesn't test specific understanding

✅ Precise:
```
Q: What syntax does async/await replace for handling promises?
A: Promise.then() chains

Q: What error handling mechanism works with async/await?
A: try/catch blocks (instead of .catch())

Q: What does the 'await' keyword do to promise execution?
A: Pauses function execution until promise resolves
```

### 3. Consistent: Same Answer Each Time

**Principle**: Prompts should produce the same answer on each review (with advanced exceptions for creative prompts).

**Why it matters**: When a prompt can have multiple valid answers, each retrieval strengthens a *different* memory trace. This creates **retrieval-induced forgetting** - recalling one answer actually inhibits other related memories.

**Example of the problem**:

```
Q: Give an example of a design pattern
```

Review 1: "Observer pattern"
Review 2: "Factory pattern"
Review 3: "Singleton pattern"

Each retrieval strengthens a different trace. None becomes reliably accessible. The category "design pattern" becomes associated with whichever example you recalled most recently, inhibiting others.

**Research basis**: Retrieval-induced forgetting (Anderson et al., 1994) shows that retrieving some items from a category inhibits other items in that category.

**How to handle lists and examples**:

For **closed lists** (fixed members):
- Use cloze deletion - one card per missing element
- Keep the same order to build visual "shape" memory

For **open lists** (evolving categories):
- Don't try to memorize the whole list
- Create prompts linking instances to category
- Write prompts about patterns within the category

For **examples**:
- Ask for "the most common example" or "a canonical example"
- Or flip it: "What pattern does Observer implement?" (specific instance → category)

**Creative prompts exception**: Advanced users can write prompts that explicitly ask for novel answers each time. These leverage the "generation effect" but are less well-researched.

### 4. Tractable: ~90% Success Rate

**Principle**: You should be able to answer correctly about 90% of the time.

**Why it matters**:
- Too easy (>95%): Wastes time, no effortful retrieval
- Too hard (<80%): Frustrating, leads to abandonment, creates negative associations

**The Goldilocks zone**: Enough difficulty to require memory retrieval, not so much that you frequently fail.

**How to calibrate**:

If struggling:
1. Break down further into smaller pieces
2. Add mnemonic cues (in parentheses in the answer)
3. Provide more context in the question
4. Link to existing strong memories

If too easy:
1. Remove scaffolding from the question
2. Increase effortfulness (see property 5)
3. Combine with related prompt for slightly broader scope

**Mnemonic cues examples**:

```
Q: What algorithm finds the shortest path in a weighted graph?
A: Dijkstra's algorithm (sounds like "dike-stra" → building dikes along shortest water path)

Q: What design pattern allows object behavior to vary based on internal state?
A: State pattern (literally named for what it does - different states, different behavior)
```

Cues should:
- Appear in parentheses in the answer
- Connect to vivid, memorable associations
- Use visual, emotional, or humorous links
- Relate new knowledge to existing memories

**Research basis**: Desirable difficulties (Bjork, 1994) - optimal learning occurs with moderate challenge. Spaced repetition systems work best when interval scheduling keeps difficulty in the sweet spot.

### 5. Effortful: Requires Actual Retrieval

**Principle**: The prompt must require pulling information from memory, not trivial inference or pattern matching.

**Why it matters**: The retrieval itself is what strengthens memory. If you can answer without retrieving, you're not getting the benefit.

**Common failure modes**:

**Too trivial**:
```
Q: Is Python a programming language?
A: Yes
```
No retrieval required - everyone knows this.

**Pattern-matchable**:
```
Q: In the context of RESTful APIs using HTTP methods with proper authentication headers and JSON payloads, what method is used to create a new resource?
A: POST
```
The question is so specific and long that you can answer by pattern matching ("create" → POST) without actually retrieving understanding of REST principles.

**The right level**:
```
Q: What problem does the POST method solve that GET cannot?
A: Sending data in the request body (GET uses URL parameters)

Q: Why should resource creation use POST instead of PUT?
A: PUT requires knowing the resource ID in advance; POST lets the server assign it
```

These require retrieving actual understanding.

**How to assess effortfulness**:

Ask yourself during review:
- Did I have to think about this?
- Or did I answer automatically/reflexively?

If answering automatically:
- Question might be too easy
- Or you've truly internalized it (good!)
- Check: Can you apply it in a novel context?

**Research basis**: Retrieval effort correlates with learning gains (Bjork & Bjork, 2011). Effort during encoding and retrieval creates stronger, more durable memories.

## Knowledge Type Strategies

### Factual Knowledge

**Definition**: Discrete, well-defined facts - names, dates, definitions, components, ingredients.

**Core strategy**: Break into atomic units. Write more prompts than feels natural.

**Why this works**: Each fact is a separate memory trace. Lumping them together creates the unfocused prompt problem.

**Example transformation**:

❌ One card:
```
Q: What are the SOLID principles?
A: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
```

✅ Five cards:
```
Q: What does the 'S' in SOLID stand for?
A: Single Responsibility

Q: What does the 'O' in SOLID stand for?
A: Open/Closed

Q: What does the 'L' in SOLID stand for?
A: Liskov Substitution

Q: What does the 'I' in SOLID stand for?
A: Interface Segregation

Q: What does the 'D' in SOLID stand for?
A: Dependency Inversion
```

Then create additional cards for what each principle means.

### Conceptual Knowledge

**Definition**: Understanding ideas, principles, theories, mental models.

**Core strategy**: Use multiple "lenses" to trace the edges of a concept.

**The five conceptual lenses**:

1. **Attributes and tendencies**: What's always/sometimes/never true?
2. **Similarities and differences**: How does it relate to adjacent concepts?
3. **Parts and wholes**: What are examples? What are sub-concepts?
4. **Causes and effects**: What does it do? When is it used?
5. **Significance and implications**: Why does it matter to you personally?

**Why this works**: A robust concept is not a single memory - it's a network of related memories. Approaching from multiple angles builds that network.

**Research basis**: Elaborative encoding (Craik & Lockhart, 1972) - deeper, more elaborate processing creates stronger memories. Multiple retrieval routes create redundancy and resilience.

**Example - Understanding "Technical Debt"**:

```
Lens 1 - Attributes:
Q: What's the core attribute of technical debt?
A: Code shortcuts that save time now but cost time later

Lens 2 - Similarities:
Q: How does technical debt differ from bugs?
A: Bugs are unintentional; technical debt is a conscious trade-off

Lens 3 - Parts/Wholes:
Q: Give one concrete example of technical debt
A: Skipping tests to ship faster (will slow down future changes)

Lens 4 - Causes/Effects:
Q: What forces cause teams to accumulate technical debt?
A: Deadline pressure, incomplete understanding, changing requirements

Lens 5 - Significance:
Q: When is taking on technical debt the right choice for your team?
A: When speed to market outweighs future maintenance cost (time-sensitive opportunities)
```

### Procedural Knowledge

**Definition**: How to do things - processes, workflows, algorithms, techniques.

**Core strategy**: Focus on transitions, timing, and rationale. Avoid rote step memorization.

**Why rote steps fail**: Memorizing "step 1, step 2, step 3" encourages mindless recitation without understanding. You can recite the steps but not apply them flexibly.

**Better focuses**:

1. **Transitions**: When do you move from step X to step Y?
2. **Conditions**: How do you know you're ready for the next step?
3. **Rationale**: Why does each step matter?
4. **Timing**: How long do things take? ("heads-up" information)
5. **Heuristics**: Rules of thumb for decision points

**Example - Git Workflow**:

❌ Rote steps:
```
Q: What are the steps to create a feature branch?
A: 1. git checkout main, 2. git pull, 3. git checkout -b feature-name, 4. Make changes, 5. git commit, 6. git push
```

✅ Transitions and rationale:
```
Q: Why pull before creating a feature branch?
A: To start from the latest changes (avoid merge conflicts later)

Q: When is the right time to create a feature branch?
A: Before making any changes (keep main clean)

Q: What's the relationship between commits and pushes?
A: Commit saves locally, push shares with remote (can commit many times before pushing)

Q: How do you know when a feature branch is ready to merge?
A: Tests pass, code reviewed, conflicts resolved
```

## Cognitive Science Background

### Spacing Effect

**Finding**: Distributed practice beats massed practice.

**Application**: Spaced repetition systems automatically schedule reviews at increasing intervals. Your job is to write prompts that make each review meaningful.

**Research**: Ebbinghaus (1885), Cepeda et al. (2006)

### Testing Effect

**Finding**: Retrieval practice is more effective than re-studying.

**Application**: Each prompt review is a retrieval practice session. More prompts = more practice opportunities.

**Research**: Roediger & Karpicke (2006)

### Elaborative Encoding

**Finding**: Deeper processing creates stronger memories.

**Application**: Connect new information to existing knowledge. Use multiple lenses for concepts. Ask "why" not just "what".

**Research**: Craik & Lockhart (1972)

### Generation Effect

**Finding**: You remember better what you generate yourself.

**Application**: Answers should come from your memory, not pattern matching. Creative prompts leverage this explicitly.

**Research**: Slamecka & Graf (1978)

### Retrieval-Induced Forgetting

**Finding**: Retrieving some items from a category inhibits other items.

**Application**: Prompts must produce consistent answers. Variable answers create interference.

**Research**: Anderson et al. (1994)

## Common Failure Modes

### False Positives: Answering Without Knowing

**Problem**: You answer correctly but don't actually have the knowledge.

**Causes**:
1. Pattern matching on question structure
2. Binary questions (50% guess rate)
3. Trivial prompts (no retrieval needed)
4. Recognition instead of recall

**Solutions**:
- Keep questions short and simple
- Use open-ended questions
- Increase effortfulness
- Test application, not just recall

### False Negatives: Knowing But Failing

**Problem**: You have the knowledge but answer incorrectly.

**Causes**:
1. Not enough context to exclude alternative answers
2. Too much provincial context (overfitting to specific examples)
3. Prompt is too hard (needs breaking down)

**Solutions**:
- Include just enough context
- Express general knowledge generally
- Break into smaller pieces
- Add mnemonic cues

### The Sigh: Boredom and Abandonment

**Problem**: Reviewing cards feels like a chore. You abandon the system.

**Causes**:
1. No emotional connection to material
2. Creating cards "because you should"
3. Prompts are trivial or frustrating
4. Material no longer relevant

**Solutions**:
- Only create prompts about things that matter to you
- Connect to actual creative work and goals
- Be alert to internal sighs during review
- Delete liberally when connection fades
- Revise frustrating prompts immediately

## Advanced Techniques

### Salience Prompts

**Purpose**: Keep ideas "top of mind" to drive behavioral change and application.

**How they differ**: Standard prompts build retention. Salience prompts extend the period where knowledge feels salient - where you notice it everywhere.

**Example patterns**:

```
# Context-based
Q: What's one situation this week where you could apply X?
A: (Answer varies based on current context)

# Implication-focused
Q: What's one assumption you're making that X challenges?
A: (Identify specific assumption - varies)

# Creative application
Q: Describe a way to apply X you haven't mentioned before
A: (Novel answer each time)
```

**Warning**: Less well-researched than standard retrieval prompts. Experimental.

**Research basis**: Frequency judgments (Tversky & Kahneman, 1973) - recently encountered concepts feel more common (Baader-Meinhof effect). Salience prompts extend this.

### Interpretation Over Transcription

**Principle**: Don't parrot source material verbatim. Extract transferable principles.

**Why**: Verbatim cards create brittle knowledge that doesn't transfer to new contexts.

**Example**:

❌ Transcription:
```
Q: What does the recipe say about olive oil?
A: "Use 2 tablespoons extra virgin olive oil"
```

✅ Interpretation:
```
Q: What's the typical ratio of olive oil to pasta in aglio e olio?
A: Roughly 2 tablespoons per serving (adjust based on pasta amount)
```

The interpreted version extracts the principle (ratio) rather than the specific quantity.

### Cues and Mnemonics

**When to add cues**: When you're struggling with a prompt that's otherwise well-designed.

**How to add cues**: In parentheses in the answer, using vivid associations.

**Types of associations**:
- Visual (create a mental image)
- Emotional (attach a feeling)
- Humorous (funny sticks)
- Personal (connect to your experience)

**Example**:

```
Q: What algorithm is optimal for finding shortest paths from one source to all other vertices?
A: Dijkstra's algorithm (sounds like "dike-stra" → imagine building dikes along the shortest path to dam flooding from source to all destinations)
```

### Creative Prompts

**Purpose**: Drive application and novel thinking, not just retention.

**Pattern**: Ask for a different answer each time.

**Example**:

```
Q: Explain one way you could apply first principles thinking that you haven't mentioned before
A: (Generate novel answer using current context)
```

**Research status**: Experimental. Leverages generation effect but less proven than standard retrieval prompts.

## Research References

- Anderson, M. C., Bjork, R. A., & Bjork, E. L. (1994). Remembering can cause forgetting: Retrieval dynamics in long-term memory.
- Bjork, R. A. (1994). Memory and metamemory considerations in the training of human beings.
- Bjork, R. A., & Bjork, E. L. (2011). Making things hard on yourself, but in a good way: Creating desirable difficulties to enhance learning.
- Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis.
- Craik, F. I., & Lockhart, R. S. (1972). Levels of processing: A framework for memory research.
- Ebbinghaus, H. (1885). Memory: A contribution to experimental psychology.
- Morris, C. D., Bransford, J. D., & Franks, J. J. (1977). Levels of processing versus transfer appropriate processing.
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning: Taking memory tests improves long-term retention.
- Slamecka, N. J., & Graf, P. (1978). The generation effect: Delineation of a phenomenon.
- Tversky, A., & Kahneman, D. (1973). Availability: A heuristic for judging frequency and probability.

---

For practical application guidance, see the main SKILL.md file and `references/knowledge_type_templates.md`.
