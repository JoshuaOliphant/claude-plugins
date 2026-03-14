# LLM Tells — Banned Words and Patterns

Words, phrases, and patterns that signal AI-generated content to recruiters, hiring managers, and AI detection algorithms. Section optimizers and cover letter writers MUST avoid these.

## Banned Words

These words are statistically overrepresented in LLM output compared to human writing. Replace with natural alternatives.

### High-Risk (Almost Never Used by Humans in Resumes)

| Banned | Use Instead |
|--------|-------------|
| leverage / leveraged / leveraging | used, applied, built with |
| utilize / utilized / utilizing | used |
| delve / delved / delving | explored, investigated, dug into |
| foster / fostered / fostering | built, created, grew |
| pivotal | important, key, critical |
| multifaceted | complex, varied |
| holistic | comprehensive, full, complete |
| synergy / synergize | collaboration, teamwork |
| paradigm | approach, model, pattern |
| tapestry | (just don't) |
| landscape | space, field, area, domain |
| realm | area, domain, field |
| cornerstone | foundation, basis, core |
| underscores | shows, highlights, demonstrates |
| embark / embarked | started, began, launched |
| endeavor | effort, project, work |
| commendable | strong, impressive, notable |
| noteworthy | notable, significant, worth mentioning |
| intricate | complex, detailed |
| nuanced | subtle, detailed |
| comprehensive | thorough, complete, full |
| meticulous | careful, thorough, precise |
| elucidate | explain, clarify |
| illuminate | show, reveal, clarify |
| testament | proof, evidence, sign |
| aligns | matches, fits, supports |

### Medium-Risk (Overused by LLMs, OK Sparingly)

| Cautious Use | Notes |
|--------------|-------|
| robust | OK once per document max; prefer "reliable", "resilient", "solid" |
| scalable | OK in technical context, overused in general descriptions |
| cutting-edge | prefer "modern", "current", specific technology names |
| innovative | show don't tell — describe the innovation instead |
| passionate | OK once, but "driven by" or specific enthusiasm is stronger |
| adept | prefer "skilled in", "experienced with" |
| proficient | OK for skills lists, overused in prose |
| spearheaded | OK once per resume; don't use for every bullet |
| orchestrated | OK once per resume; same warning |
| championed | OK once per resume; same warning |
| harnessing | prefer "using", "applying", "building with" |
| bolster | prefer "strengthen", "improve", "support" |
| moreover | just say the next thing |
| furthermore | just say the next thing |
| in conclusion | don't — just state your conclusion |

## Banned Phrases

### Resume Phrases

| Banned | Use Instead |
|--------|-------------|
| "demonstrated a proven track record" | state the track record directly |
| "results-driven professional" | describe actual results |
| "passionate about [X]" (in summary) | show passion through project choices |
| "leveraging cutting-edge technologies" | name the specific technologies |
| "in today's fast-paced environment" | (delete entirely) |
| "a keen eye for detail" | show detail through specific metrics |
| "adept at navigating complex challenges" | describe a specific challenge you solved |
| "committed to continuous learning" | list recent learning (certs, courses) |
| "thrive in dynamic environments" | (delete entirely) |
| "strategic thinker" | describe a strategic decision you made |
| "with a focus on delivering value" | (delete entirely — assumed) |
| "poised to make an impact" | (delete entirely) |
| "well-versed in" | "experienced with", "skilled in" |

### Cover Letter Phrases

| Banned | Use Instead |
|--------|-------------|
| "I am writing to express my interest" | lead with an achievement or hook |
| "I believe I would be a great fit" | explain specifically why you fit |
| "I am excited about the opportunity" | say what specifically excites you |
| "Please don't hesitate to contact me" | "I'm available to discuss" |
| "Thank you for your time and consideration" | confident close with call to action |
| "I look forward to the possibility" | "I'd welcome the chance to discuss" |
| "As evidenced by my resume" | the cover letter should stand alone |
| "In my current role, I have gained" | describe what you did, not what you gained |
| "This role deeply resonates with" | say why, specifically |
| "I am confident that my skills" | show confidence through specific examples |
| "I would welcome the opportunity to contribute" | state what you'd do, not that you'd like to |

## Banned Patterns

### Structural Tells

- **Triple adjective stacking**: "a dynamic, innovative, and results-oriented engineer" → pick one, prove it
- **Vague quantification**: "significantly improved" → use actual numbers or don't quantify
- **Passive hedging**: "was responsible for" → use active verbs
- **Em-dash overuse (—)**: LLMs insert em-dashes constantly. Humans rarely use them in resumes. Prefer commas, periods, or parentheses. Maximum 1-2 across the entire document. Never use in bullet points.
- **En-dash confusion (–)**: LLMs sometimes use en-dashes where hyphens belong. Use hyphens (-) for compound words, en-dashes only for date ranges (2020–2024).
- **Semicolons in bullets**: LLMs overuse these. Prefer separate bullets or commas. Most resume bullets shouldn't contain semicolons at all.
- **Colon-heavy bullets**: "Achieved the following: reduced costs by..." — just say "Reduced costs by..."
- **Ellipsis abuse (...)**: LLMs sometimes trail off. Never use ellipses in resumes.
- **Every bullet starts the same way**: Vary sentence structure. Not every line should be "Verb + object + result."
- **Excessive parallelism**: LLMs make every bullet grammatically identical. Mix it up.
- **Oxford comma consistency flip**: Pick one style and stick with it throughout.
- **Parenthetical asides**: LLMs overuse parentheses for clarification. Use them sparingly — one or two per page.

### Tone Tells

- **Overly formal for tech**: "I am pleased to present" → too formal for a startup
- **Overly enthusiastic**: multiple exclamation points, "thrilled", "elated"
- **Corporate buzzword density**: if a sentence has 3+ buzzwords, a human didn't write it
- **Perfect grammar throughout**: real humans occasionally start sentences with "And" or "But"
- **No contractions**: humans use contractions in cover letters. "I've" not "I have" every time.
- **Uniform bullet length**: LLMs produce bullets of nearly identical length. Humans vary.

### Content Tells

- **Restating the job description back**: "Your posting mentions X, and I have X" — too mechanical
- **Claiming every listed skill**: humans skip things they're weak on
- **Generic company praise**: "Your company's innovative approach to technology" — be specific or don't praise
- **Symmetric structure**: every section has exactly the same number of bullets
- **No personality**: the text could be about anyone — add something specific to YOU

## How Agents Should Use This

1. **Section optimizers**: After generating output, scan for banned words/phrases. Replace any found.
2. **Cover letter writer**: Read this reference before writing. Avoid all banned phrases. Use contractions. Vary sentence length.
3. **Truthfulness verifier**: Flag any banned words/phrases found in optimized text as a yellow flag.

## Natural Alternatives Cheat Sheet

Instead of LLM-sounding prose, aim for:
- **Specific over general**: "Kafka" not "messaging systems"
- **Numbers over adjectives**: "reduced by 40%" not "significantly improved"
- **Active over passive**: "built" not "was responsible for building"
- **Short over long**: "fixed" not "identified and subsequently resolved"
- **Concrete over abstract**: "Python CLI tool" not "automation solution"
- **Casual confidence over formal hedging**: "I built X" not "I had the opportunity to contribute to X"
