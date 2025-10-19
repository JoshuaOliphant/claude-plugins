# Knowledge Type Templates

This document provides ready-to-use templates for different types of knowledge. Each template includes example code and guidance on when to use it.

## Table of Contents

- [Factual Knowledge Templates](#factual-knowledge-templates)
- [Conceptual Knowledge Templates](#conceptual-knowledge-templates)
- [Procedural Knowledge Templates](#procedural-knowledge-templates)
- [List Templates](#list-templates)
- [Salience Templates](#salience-templates)

## Factual Knowledge Templates

Use when learning: names, dates, definitions, components, ingredients, vocabulary, formulas.

### Template 1: Simple Fact

```python
def create_simple_fact(api, deck_id, question, answer, tags=None):
    """Create a focused factual card."""
    return api.create_card(
        content=f"# {question}\n---\n{answer}",
        deck_id=deck_id,
        manual_tags=tags or []
    )

# Example usage
create_simple_fact(
    api, deck_id,
    question="What is the capital of France?",
    answer="Paris",
    tags=["geography", "europe", "capitals"]
)
```

### Template 2: Definition

```python
def create_definition_card(api, deck_id, term, definition, example=None, tags=None):
    """Create a definition card, optionally with example."""
    answer = definition
    if example:
        answer += f"\n\nExample: {example}"

    return api.create_card(
        content=f"# What is {term}?\n---\n{answer}",
        deck_id=deck_id,
        manual_tags=tags or [term.lower().replace(" ", "-")]
    )

# Example usage
create_definition_card(
    api, deck_id,
    term="technical debt",
    definition="Code shortcuts that save time now but cost time later",
    example="Skipping tests to ship faster",
    tags=["software-engineering", "concepts"]
)
```

### Template 3: Component/Ingredient Lists (Atomic)

```python
def create_component_cards(api, deck_id, whole_name, components, tags=None):
    """
    Break a list of components into individual atomic cards.
    Returns list of created cards.
    """
    cards = []
    for component in components:
        card = api.create_card(
            content=f"# Name one component of {whole_name}\n---\n{component}",
            deck_id=deck_id,
            manual_tags=(tags or []) + [whole_name.lower().replace(" ", "-")]
        )
        cards.append(card)
    return cards

# Example usage
create_component_cards(
    api, deck_id,
    whole_name="chocolate chip cookies",
    components=[
        "Flour (primary dry ingredient)",
        "Butter (fat)",
        "White sugar and brown sugar (sweeteners)",
        "Eggs (structure)",
        "Vanilla (flavoring)",
        "Baking soda (leavening)",
        "Salt (balances sweetness)"
    ],
    tags=["baking", "recipes"]
)
```

### Template 4: Comparison/Contrast

```python
def create_comparison_card(api, deck_id, item_a, item_b, difference, tags=None):
    """Create a card comparing two similar things."""
    return api.create_card(
        content=f"# How does {item_a} differ from {item_b}?\n---\n{difference}",
        deck_id=deck_id,
        manual_tags=tags or []
    )

# Example usage
create_comparison_card(
    api, deck_id,
    item_a="list",
    item_b="tuple",
    difference="Lists are mutable (can be changed), tuples are immutable (cannot be changed)",
    tags=["python", "data-structures"]
)
```

## Conceptual Knowledge Templates

Use when learning: principles, theories, mental models, frameworks, design patterns.

### Template 1: Five Lenses Approach

```python
def create_concept_cards_five_lenses(
    api,
    deck_id,
    concept,
    attributes,
    similarities,
    parts_examples,
    causes_effects,
    significance,
    tags=None
):
    """
    Create 5 cards covering a concept from multiple angles.
    Returns list of created cards.
    """
    base_tags = (tags or []) + [concept.lower().replace(" ", "-")]
    cards = []

    # Lens 1: Attributes
    cards.append(api.create_card(
        content=f"# What is the core attribute of {concept}?\n---\n{attributes}",
        deck_id=deck_id,
        manual_tags=base_tags + ["attributes"]
    ))

    # Lens 2: Similarities/Differences
    cards.append(api.create_card(
        content=f"# How does {concept} differ from similar concepts?\n---\n{similarities}",
        deck_id=deck_id,
        manual_tags=base_tags + ["comparison"]
    ))

    # Lens 3: Parts/Wholes/Examples
    cards.append(api.create_card(
        content=f"# Give a concrete example of {concept}\n---\n{parts_examples}",
        deck_id=deck_id,
        manual_tags=base_tags + ["examples"]
    ))

    # Lens 4: Causes/Effects
    cards.append(api.create_card(
        content=f"# What problem does {concept} solve?\n---\n{causes_effects}",
        deck_id=deck_id,
        manual_tags=base_tags + ["benefits"]
    ))

    # Lens 5: Significance
    cards.append(api.create_card(
        content=f"# When would you use {concept} in your work?\n---\n{significance}",
        deck_id=deck_id,
        manual_tags=base_tags + ["application"]
    ))

    return cards

# Example usage
create_concept_cards_five_lenses(
    api, deck_id,
    concept="dependency injection",
    attributes="Dependencies are provided from outside rather than created internally",
    similarities="Different from service locator (DI pushes dependencies in, service locator pulls them out)",
    parts_examples="Passing a database connection to a class constructor instead of creating it inside",
    causes_effects="Makes code testable by allowing mock dependencies to be injected",
    significance="Essential when writing testable FastAPI endpoints that need to swap database implementations",
    tags=["design-patterns", "software-architecture"]
)
```

### Template 2: Core Principle

```python
def create_principle_card(api, deck_id, principle_name, explanation, violation_example=None, tags=None):
    """Create a card explaining a principle, optionally with a violation example."""
    answer = explanation
    if violation_example:
        answer += f"\n\nViolation example: {violation_example}"

    return api.create_card(
        content=f"# What is the {principle_name} principle?\n---\n{answer}",
        deck_id=deck_id,
        manual_tags=tags or []
    )

# Example usage
create_principle_card(
    api, deck_id,
    principle_name="Single Responsibility",
    explanation="A class should have only one reason to change (one responsibility)",
    violation_example="A User class that handles both data storage AND email sending",
    tags=["solid-principles", "oop"]
)
```

### Template 3: Mental Model

```python
def create_mental_model_card(api, deck_id, model_name, analogy, application, tags=None):
    """Create a card for a mental model using analogy."""
    return api.create_card(
        content=f"# How does the '{model_name}' mental model work?\n---\n{analogy}\n\nApplication: {application}",
        deck_id=deck_id,
        manual_tags=tags or []
    )

# Example usage
create_mental_model_card(
    api, deck_id,
    model_name="Second-order thinking",
    analogy="Don't just ask 'What happens next?' Ask 'What happens after that?'",
    application="Before making a decision, consider not just immediate effects but downstream consequences",
    tags=["mental-models", "decision-making"]
)
```

## Procedural Knowledge Templates

Use when learning: processes, workflows, algorithms, techniques, recipes.

### Template 1: Transition Card

```python
def create_transition_card(api, deck_id, procedure, condition, next_step, tags=None):
    """Create a card about when to transition between steps."""
    return api.create_card(
        content=f"# When do you know it's time to {next_step} in {procedure}?\n---\n{condition}",
        deck_id=deck_id,
        manual_tags=(tags or []) + [procedure.lower().replace(" ", "-"), "transitions"]
    )

# Example usage
create_transition_card(
    api, deck_id,
    procedure="sourdough bread making",
    condition="After 30-60 minutes when flour is fully hydrated",
    next_step="add salt",
    tags=["baking", "sourdough"]
)
```

### Template 2: Rationale Card

```python
def create_rationale_card(api, deck_id, procedure, action, reason, tags=None):
    """Create a card about WHY a step is done."""
    return api.create_card(
        content=f"# Why do you {action} in {procedure}?\n---\n{reason}",
        deck_id=deck_id,
        manual_tags=(tags or []) + [procedure.lower().replace(" ", "-"), "rationale"]
    )

# Example usage
create_rationale_card(
    api, deck_id,
    procedure="git workflow",
    action="pull before creating a feature branch",
    reason="To start from the latest changes and avoid merge conflicts later",
    tags=["git", "version-control"]
)
```

### Template 3: Timing/Duration Card

```python
def create_timing_card(api, deck_id, procedure, phase, duration, tags=None):
    """Create a card about how long something takes (heads-up information)."""
    return api.create_card(
        content=f"# How long does {phase} take in {procedure}?\n---\n{duration}",
        deck_id=deck_id,
        manual_tags=(tags or []) + [procedure.lower().replace(" ", "-"), "timing"]
    )

# Example usage
create_timing_card(
    api, deck_id,
    procedure="sourdough bread making",
    phase="bulk fermentation",
    duration="4-6 hours at room temperature (temperature-dependent)",
    tags=["baking", "sourdough"]
)
```

### Template 4: Condition Recognition

```python
def create_condition_card(api, deck_id, procedure, goal, indicators, tags=None):
    """Create a card about recognizing when a condition is met."""
    return api.create_card(
        content=f"# What indicates {goal} in {procedure}?\n---\n{indicators}",
        deck_id=deck_id,
        manual_tags=(tags or []) + [procedure.lower().replace(" ", "-"), "conditions"]
    )

# Example usage
create_condition_card(
    api, deck_id,
    procedure="sourdough bread making",
    goal="dough is ready for shaping",
    indicators="50-100% volume increase, jiggly texture, small bubbles on surface",
    tags=["baking", "sourdough"]
)
```

### Template 5: Complete Procedural Set

```python
def create_procedure_cards(
    api,
    deck_id,
    procedure_name,
    transitions,
    rationales,
    timings,
    conditions=None,
    tags=None
):
    """
    Create a complete set of procedural knowledge cards.

    Args:
        transitions: List of {"condition": str, "next_step": str}
        rationales: List of {"action": str, "reason": str}
        timings: List of {"phase": str, "duration": str}
        conditions: Optional list of {"goal": str, "indicators": str}

    Returns:
        List of created cards
    """
    cards = []
    base_tags = tags or []

    for trans in transitions:
        cards.append(create_transition_card(
            api, deck_id, procedure_name,
            trans["condition"], trans["next_step"], base_tags
        ))

    for rat in rationales:
        cards.append(create_rationale_card(
            api, deck_id, procedure_name,
            rat["action"], rat["reason"], base_tags
        ))

    for timing in timings:
        cards.append(create_timing_card(
            api, deck_id, procedure_name,
            timing["phase"], timing["duration"], base_tags
        ))

    if conditions:
        for cond in conditions:
            cards.append(create_condition_card(
                api, deck_id, procedure_name,
                cond["goal"], cond["indicators"], base_tags
            ))

    return cards

# Example usage
create_procedure_cards(
    api, deck_id,
    procedure_name="deploying to production",
    transitions=[
        {"condition": "All tests pass and code is reviewed", "next_step": "merge to main"},
        {"condition": "CI/CD pipeline completes successfully", "next_step": "deploy to staging"},
    ],
    rationales=[
        {"action": "deploy to staging before production", "reason": "Catch environment-specific issues in a safe environment"},
        {"action": "run database migrations before deploying code", "reason": "Ensure schema changes are in place before code expects them"},
    ],
    timings=[
        {"phase": "CI/CD pipeline", "duration": "5-10 minutes"},
        {"phase": "staging deployment", "duration": "2-3 minutes"},
    ],
    conditions=[
        {"goal": "staging is ready for production deployment", "indicators": "Smoke tests pass, no errors in logs, performance is acceptable"},
    ],
    tags=["devops", "deployment"]
)
```

## List Templates

Use when learning: lists of items (continents, design patterns, HTTP methods, etc.)

### Template 1: Closed List (Cloze Deletion)

```python
def create_closed_list_cards(api, deck_id, list_name, items, tags=None):
    """
    Create cloze deletion cards for a closed list (fixed members).
    One card per item, each showing all others.
    """
    cards = []
    for i, item in enumerate(items):
        others = ", ".join([it for j, it in enumerate(items) if j != i])
        cards.append(api.create_card(
            content=f"# Name all {len(items)} {list_name}\n---\n{others}, __{item}__",
            deck_id=deck_id,
            pos=chr(97 + i),  # 'a', 'b', 'c'... for consistent ordering
            manual_tags=(tags or []) + [list_name.lower().replace(" ", "-")]
        ))
    return cards

# Example usage
create_closed_list_cards(
    api, deck_id,
    list_name="HTTP methods",
    items=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["http", "rest-api"]
)
```

### Template 2: Open List (Instance → Category)

```python
def create_open_list_cards(api, deck_id, category, instances, tags=None):
    """
    Create cards linking instances to an open category.
    Don't try to memorize all members - focus on classification.
    """
    cards = []
    for instance, details in instances.items():
        cards.append(api.create_card(
            content=f"# What {category} category does {instance} belong to?\n---\n{details}",
            deck_id=deck_id,
            manual_tags=(tags or []) + [category.lower().replace(" ", "-")]
        ))
    return cards

# Example usage
create_open_list_cards(
    api, deck_id,
    category="design pattern",
    instances={
        "Observer": "Behavioral (defines communication between objects)",
        "Factory": "Creational (handles object creation)",
        "Adapter": "Structural (adapts interfaces)",
    },
    tags=["design-patterns"]
)
```

## Salience Templates

Use when: You want to apply knowledge, not just remember it. Keep ideas top-of-mind.

**Warning**: Experimental. Less research backing than standard retrieval prompts.

### Template 1: Context Application

```python
def create_context_application_card(api, deck_id, concept, context_question, tags=None):
    """
    Create a card prompting application in current context.
    Answer will vary based on what you're working on.
    """
    return api.create_card(
        content=f"# {context_question}\n---\n(Give an answer specific to your current work context - answer may vary)",
        deck_id=deck_id,
        manual_tags=(tags or []) + [concept.lower().replace(" ", "-"), "application"],
        review_reverse=False
    )

# Example usage
create_context_application_card(
    api, deck_id,
    concept="first principles thinking",
    context_question="What's one situation this week where you could apply first principles thinking?",
    tags=["mental-models"]
)
```

### Template 2: Implication Prompt

```python
def create_implication_card(api, deck_id, concept, implication_question, tags=None):
    """
    Create a card about implications or assumptions.
    Drives deeper thinking about the concept's relevance.
    """
    return api.create_card(
        content=f"# {implication_question}\n---\n(Identify specific implications or assumptions - answer will vary)",
        deck_id=deck_id,
        manual_tags=(tags or []) + [concept.lower().replace(" ", "-"), "reflection"]
    )

# Example usage
create_implication_card(
    api, deck_id,
    concept="technical debt",
    implication_question="What's one assumption you're making in your current project that might be creating technical debt?",
    tags=["software-engineering"]
)
```

### Template 3: Creative Generation

```python
def create_creative_generation_card(api, deck_id, concept, generation_prompt, tags=None):
    """
    Create a card that asks for a novel answer each time.
    Leverages the generation effect.
    """
    return api.create_card(
        content=f"# {generation_prompt}\n---\n(Novel answer each time - give an answer you haven't given before)",
        deck_id=deck_id,
        manual_tags=(tags or []) + [concept.lower().replace(" ", "-"), "creative"]
    )

# Example usage
create_creative_generation_card(
    api, deck_id,
    concept="dependency injection",
    generation_prompt="Describe a way to apply dependency injection that you haven't mentioned before",
    tags=["design-patterns"]
)
```

## Quick Reference: When to Use Which Template

| Knowledge Type | Template | Best For |
|---------------|----------|----------|
| **Facts** | Simple Fact | Names, dates, single facts |
| **Facts** | Definition | Terms and their meanings |
| **Facts** | Component Cards | Lists of ingredients, parts, components |
| **Facts** | Comparison | Distinguishing similar concepts |
| **Concepts** | Five Lenses | Deep understanding of ideas |
| **Concepts** | Core Principle | Design principles, rules |
| **Concepts** | Mental Model | Frameworks for thinking |
| **Procedures** | Transition | When to move between steps |
| **Procedures** | Rationale | Why steps are done |
| **Procedures** | Timing | How long things take |
| **Procedures** | Condition | Recognizing states/readiness |
| **Lists** | Closed List | Fixed members (continents, HTTP methods) |
| **Lists** | Open List | Evolving categories (design patterns) |
| **Application** | Context Application | Applying concepts to work |
| **Application** | Implication | Deeper thinking about relevance |
| **Application** | Creative Generation | Novel applications |

## Validation Workflow

Before creating any card from these templates:

1. **Check focus**: Does it test exactly one detail?
2. **Check precision**: Is the question specific?
3. **Check consistency**: Will it produce the same answer each time? (Unless it's a creative prompt)
4. **Check tractability**: Can you answer correctly ~90% of the time?
5. **Check effort**: Does it require actual memory retrieval?
6. **Check emotion**: Do you actually care about this?

Use the `validate_prompt_quality()` function from mochi_api.py:

```python
from scripts.mochi_api import validate_prompt_quality

result = validate_prompt_quality(
    question="What is dependency injection?",
    answer="A design pattern where dependencies are provided from outside"
)

if not result["valid"]:
    print("Issues found:")
    for issue in result["issues"]:
        print(f"  - {issue}")
    print("\nSuggestions:")
    for suggestion in result["suggestions"]:
        print(f"  - {suggestion}")
```

---

For deeper understanding of the principles behind these templates, see:
- SKILL.md - Main skill documentation with workflows
- references/prompt_design_principles.md - Research and cognitive science background
