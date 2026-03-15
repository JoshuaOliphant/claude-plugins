# GitHub Profile README Conventions

## Tone

GitHub profiles serve a dual audience: **hiring managers** clicking through from a resume link, and **open-source community** discovering you through repos. The tone should be:

- Casual and personality-forward (not a resume dump)
- Confident without being boastful
- Specific about what you build (not vague "passionate about technology")
- Show, don't tell — link to repos, not just list skills

### Tone Calibration

Read the existing README for the author's natural voice. Preserve:
- Humor and personal anecdotes (e.g., sourdough baking)
- Narrative style if present (career-as-journey framing)
- First-person perspective

Adjust away from:
- Resume-speak ("Architected...", "Spearheaded...")
- Bullet-point lists of achievements
- Formal third-person language

## Structure (Structured Approach)

### Section Order

```markdown
# Hey, I'm [Name] 👋

[2-3 sentence casual bio]

## What I'm Building

[Current projects — each with repo link, 1-line description, and language badge]

## Tech I Work With

[Skills organized with shields.io badges, grouped by domain]

## The Arc

[2-3 casual sentences about career journey — origin story, not CV]

## Get in Touch

[Contact links as badges or clean icons]
```

### Shields.io Badge Format

Skills badges use this format:
```markdown
![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
```

Common badge colors by category:
- **Languages**: Use official brand colors (Python=#3776AB, Java=#ED8B00, TypeScript=#3178C6)
- **Cloud/Infra**: Use provider colors (AWS=#232F3E, Kubernetes=#326CE5, Docker=#2496ED)
- **Databases**: Neutral tones (PostgreSQL=#4169E1, Kafka=#231F20, Redis=#DC382D)
- **AI/ML**: Purple/violet tones (OpenAI=#412991, Anthropic=#D4A574)
- **Tools**: Gray/neutral (Git=#F05032, GitHub=#181717, GitLab=#FC6D26)

### Project Cards

For the "What I'm Building" section, use this format:
```markdown
### [Project Name](repo-url)
> One-line description in the author's casual voice

![Language](badge) ![Stars](https://img.shields.io/github/stars/username/repo?style=flat-square)
```

Only include projects that are:
1. Actively maintained (pushed within last 6 months)
2. Have meaningful code (not just config or forks)
3. Align with the resume's project list OR represent current interests

### Contact Section

Use badge-style links:
```markdown
[![Email](https://img.shields.io/badge/-Email-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:email)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](url)
[![Blog](https://img.shields.io/badge/-Blog-FF5722?style=flat-square&logo=hashnode&logoColor=white)](url)
```

## Content Guidelines

### What to Include
- Projects that demonstrate current skills and interests
- Technology you actively use (not historical knowledge)
- Personality — hobbies, fun facts, what makes you human
- Links to blog, talks, or other public work

### What to Exclude
- Full work history (that's what the resume is for)
- Every technology you've ever touched
- Certifications or education details
- Anything that reads like a job application

### Keeping It Fresh
- Feature repos pushed within the last 6 months
- Update "What I'm Building" to reflect actual current work
- Rotate featured projects as interests evolve
- The profile should feel like a living document, not a static page

## LLM Tell Avoidance

Apply the same rules from `llm-tells.md`:
- No "passionate about", "leverage", "utilize", "cutting-edge"
- No generic filler ("I love building things that make a difference")
- Specific > generic ("I build MCP servers" > "I build AI tools")
- If it sounds like every other GitHub profile, rewrite it
