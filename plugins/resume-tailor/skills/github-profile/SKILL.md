---
name: github-profile
description: >
  Update your GitHub profile README and API fields using master resume data.
  Generates a structured, badge-rich README with casual tone, proposes API field
  updates (bio, hireable, company, location), and interactively discusses pinned
  repo selection based on resume alignment and recent activity. Use when the user
  wants to update their GitHub profile, refresh their README, update their bio,
  change pinned repos, or sync their GitHub presence with their resume. Trigger
  phrases include "update GitHub profile", "refresh my GitHub", "update my GitHub
  README", "sync GitHub with resume", "change my GitHub bio", "update pinned repos",
  "GitHub profile", and "make my GitHub current".
args:
  - name: section
    description: "Optional: update only a specific part — readme, api-fields, or pinned-repos (default: all)"
    required: false
user-invokable: true
---

# GitHub Profile Updater

Update your GitHub profile README, API fields, and pinned repos from your master resume data.

## Overview

This skill reads your master resume (the same source of truth used by `/resume-tailor`) and your current GitHub state, then generates an updated profile that's casual, structured, and badge-rich — while staying aligned with your professional narrative.

## Constants

```
GITHUB_USERNAME=JoshuaOliphant
PROFILE_REPO_PATH=/Users/joshuaoliphant/Dropbox/python_workspace/JoshuaOliphant
MASTER_RESUME_YAML=~/.claude/resume-tailor/master-resume.yaml
MASTER_RESUME_MD=~/.claude/resume-tailor/master-resume.md
```

## Phase 0: Gather State

### Load Master Resume

Read the structured resume data:

```bash
cat ~/.claude/resume-tailor/master-resume.yaml
```

This provides: summary, experience, skills (by category), projects, education, contact info.

### Fetch Current GitHub State

Run the state-gathering script to get current profile data:

```bash
python ${SKILL_DIR}/scripts/github_profile_state.py --username JoshuaOliphant
```

This returns:
- **api_fields**: Current bio, company, location, hireable, blog, email
- **current_readme**: Full text of the existing README.md
- **repos**: All non-fork repos sorted by recent push (name, description, language, stars, pushed_at)
- **pinned_repos**: Currently pinned repos (up to 6)
- **profile_repo_path**: Local path to the profile repo

### Load Stored Feedback

Check for GitHub-profile-specific feedback:

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py load
```

Look for feedback entries with `category: github_profile` and apply them.

### Check Section Filter

If the `section` argument is provided:
- `readme` → Skip to Phase 1, skip Phases 2-3
- `api-fields` → Skip to Phase 2, skip Phases 1 and 3
- `pinned-repos` → Skip to Phase 3, skip Phases 1-2

If no argument, run all phases.

## Phase 1: Generate README

### Read Conventions

Read the reference guide for tone and structure:
- `${PLUGIN_ROOT}/skills/resume-tailor/references/github-profile-conventions.md`
- `${PLUGIN_ROOT}/skills/resume-tailor/references/llm-tells.md`

### Analyze Existing Tone

Read the current README from the state data. Note:
- The author's natural voice and humor style
- Personal anecdotes worth preserving (e.g., sourdough baking)
- Narrative patterns (career-as-journey framing)

Preserve these personality elements in the new version.

### Build the README

Generate a structured README using this skeleton. Fill each section from resume data + repo data:

#### Section 1: Header & Bio

```markdown
# Hey, I'm Joshua 👋

[2-3 sentences: casual version of resume summary + current focus area.
Draw from resume summary but warm it up. Mention what you're building RIGHT NOW.
Reference the career arc briefly — not as resume bullets, but as context.]
```

**Source data**: `summary` from resume YAML + `experience[0]` (current role) + recent repo activity.

#### Section 2: What I'm Building

```markdown
## What I'm Building

[For each featured project, create a card with repo link, casual description, and badges.
Prioritize:
1. Projects from the resume's projects list that have matching repos
2. Repos pushed within the last 3 months with meaningful descriptions
3. Maximum 5-6 projects to avoid clutter]
```

**Format per project:**
```markdown
### [Project Name](https://github.com/JoshuaOliphant/repo-name)
> Casual one-line description (NOT the resume bullet — rewrite for GitHub audience)

![Language](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Stars](https://img.shields.io/github/stars/JoshuaOliphant/repo-name?style=flat-square)
```

**Source data**: `projects` from resume YAML cross-referenced with `repos` from GitHub state. Use actual repo descriptions as a starting point, then rewrite casually.

#### Section 3: Tech I Work With

```markdown
## Tech I Work With

[Group skills into 3-4 visual rows using shields.io badges.
Use the resume's skill categories but simplify grouping for visual layout.
Only include tech you actively use — trim historical-only skills.]
```

**Badge format**: `![Name](https://img.shields.io/badge/-Name-COLOR?style=flat-square&logo=LOGO&logoColor=white)`

**Suggested groupings** (adapt based on resume data):
- **Languages & Frameworks**: Python, Java, FastAPI, Spring Boot, Django
- **Infrastructure**: Kubernetes, Docker, Helm, AWS, Terraform, Ansible
- **Data & Messaging**: Kafka, PostgreSQL, DynamoDB, Redis
- **AI & Developer Tools**: Claude, MCP, OpenAI, Anthropic SDK

See `github-profile-conventions.md` for badge colors by category.

**Source data**: `skills` from resume YAML. Filter to actively-used tech (check against recent repos' languages).

#### Section 4: The Arc

```markdown
## The Arc

[2-3 casual sentences about the career journey. This is the human story,
not the resume. Mention the hill-climbing metaphor if it still resonates.
Reference the transition from backend → DevOps → platform → AI.
Keep it brief — the detail is on LinkedIn.]
```

**Source data**: `experience` dates/companies from resume YAML + existing README's narrative voice.

#### Section 5: Get in Touch

```markdown
## Get in Touch

[![Email](badge)](mailto:joshua.oliphant@hey.com)
[![LinkedIn](badge)](https://linkedin.com/in/joshuaoliphant)
[![Blog](badge)](https://anoliphantneverforgets.com)
```

**Source data**: `contact` from resume YAML.

#### Section 6: Fun Fact (Optional)

Preserve the sourdough baking fun fact (or whatever personal detail exists). Fix any typos from the original.

### Present README for Review

Show the user the complete generated README in a code block. Ask:
- "Does this capture your voice? Anything feel off?"
- "Any projects to add or remove?"
- "Happy with the badge groupings?"

### Write README

After user approval, write the README to the profile repo:

```
Write to: /Users/joshuaoliphant/Dropbox/python_workspace/JoshuaOliphant/README.md
```

## Phase 2: Update API Fields

### Compare Current vs Proposed

Build proposed API field updates from resume data:

| Field | Current | Proposed | Source |
|-------|---------|----------|--------|
| bio | (from state) | (casual 1-liner from resume summary) | resume summary |
| company | (from state) | (current employer) | experience[0].company |
| location | (from state) | (keep current or update) | user input |
| hireable | (from state) | (based on career context) | user input |
| blog | (from state) | (blog URL) | resume contact |

### Present Changes

Show the comparison table. For each field that would change, explain why.

**Important**: The `hireable` field is sensitive — always ask the user explicitly:
- "Your hireable flag is currently [value]. Given your career transition, would you like to set it to true?"

### Apply API Updates

After user confirms each change, apply via `gh` CLI:

```bash
gh api -X PATCH /user -f bio="<new bio>" -f company="<company>" -f hireable=<bool> -f blog="<url>"
```

**Note**: Only include fields the user approved changing. Do NOT update fields the user didn't confirm.

## Phase 3: Discuss Pinned Repos

### Build Candidate List

Score repos for pin-worthiness using these criteria:

1. **Resume alignment** (high weight): Does this repo appear in the resume's projects list?
2. **Recency** (medium weight): Pushed within last 3 months? 6 months?
3. **Stars** (low weight): Social proof, but not the primary signal
4. **Description quality**: Does it have a clear, compelling description?
5. **Language diversity**: Showing range is good — avoid pinning 6 Python repos if possible

### Present Recommendations

Show a ranked table of candidates:

```markdown
## Pinned Repo Recommendations

| Rank | Repo | Why | Stars | Last Push | On Resume? |
|------|------|-----|-------|-----------|------------|
| 1 | ... | ... | ... | ... | ✅/❌ |
```

Currently pinned: [list current pins]

Recommend: "Here are my top 6 picks. [Explain reasoning for each — especially tradeoffs like recency vs stars, or showing breadth vs depth.] What do you think?"

### Apply Pins

**Note**: GitHub does not expose a public API for pinning repos. After the user confirms their 6 picks, provide instructions:

```markdown
To update your pinned repos:
1. Go to https://github.com/JoshuaOliphant
2. Click "Customize your pins"
3. Select these 6 repos: [list]
4. Save
```

If `gh` CLI adds pinning support in the future, use that instead.

## Phase 4: Commit & Push (Optional)

### Stage and Review

```bash
cd /Users/joshuaoliphant/Dropbox/python_workspace/JoshuaOliphant
git diff README.md
```

Show the diff to the user.

### Commit

If the user approves:

```bash
cd /Users/joshuaoliphant/Dropbox/python_workspace/JoshuaOliphant
git add README.md
git commit -m "Update profile README from master resume data

Synced with resume-tailor master resume. Updated projects,
skills badges, bio, and career arc."
```

### Push

Ask the user: "Push to GitHub now?"

If yes:
```bash
cd /Users/joshuaoliphant/Dropbox/python_workspace/JoshuaOliphant
git push origin main
```

## Feedback Capture

After the user reviews the output, capture any preferences:

```bash
echo '{"category": "github_profile", "feedback": "<user feedback>", "context": "profile update"}' | \
  python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py save-feedback
```

**Examples**:
- "Always lead with AI projects" → category: github_profile
- "Keep the sourdough fact" → category: github_profile
- "Don't mention ServiceNow by name" → category: github_profile

## Edge Cases

### Master Resume Not Found
If `master-resume.yaml` doesn't exist, run sync first:
```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/master_sync.py sync
```

### Profile Repo Not Found
If the profile repo path doesn't exist, ask the user where it is or offer to clone:
```bash
gh repo clone JoshuaOliphant/JoshuaOliphant /Users/joshuaoliphant/Dropbox/python_workspace/JoshuaOliphant
```

### No Recent Repos
If no repos have been pushed in the last 6 months, widen the window to 12 months and note this in the output.

### API Rate Limiting
If `gh api` calls fail, fall back to the cached enrichment data at `~/.claude/resume-tailor/enrichment/github.yaml`.

## Related Skills

| Skill | When to use instead |
|-------|-------------------|
| `/resume-tailor` | Tailoring resume for a specific job |
| `/resume-tailor:sync` | Syncing master resume markdown ↔ YAML |
| `/resume-tailor:evaluate` | Checking resume-job fit without optimizing |
