// ABOUTME: Compost's review workflow: Standards and Spec reviewers in parallel over a branch diff, or one reviewer on both for a small one.
// ABOUTME: Skeptics try to refute each finding worth one (Jev's triage, else every blocker and major); survivors, refutations, and unjudged findings come back side by side.
export const meta = {
  name: 'review-changes',
  description: 'Review a branch along two axes, Standards and Spec (one reviewer on both for a small, non-structural diff), then have skeptics try to refute every finding worth one (by Jev triage, else every blocker and major)',
  whenToUse: 'After verify passes on an issue, or whenever a branch or work-in-progress diff needs review, whatever its size. Pass {base, head, issue, skeptics, jev, full}, all optional: base defaults to the merge-base with the default branch, head to HEAD, issue to one found in the commits or branch name, skeptics (votes per finding worth a skeptic) to 1, jev (the path to compost scripts/jev.py, which ranks files by structural risk) to none, full (force separate Standards and Spec reviewers on a small diff) to false. A diff of 50 changed lines or fewer that Jev ranks and finds not structural gets one reviewer covering both axes. A bare string is treated as base.',
  phases: [
    { title: 'Scope', detail: 'pin the base, the diff, the spec, and the standards sources; rank files by structural risk' },
    { title: 'Standards', detail: 'reviewer against instructions files, CONTEXT.md, ADRs, and the canon (on a small diff, one light reviewer covers both axes here); skeptics refute each finding worth one' },
    { title: 'Spec', detail: 'reviewer against the issue AC-N and interfaces; skeptics refute each finding worth one' },
  ],
}

const input = typeof args === 'object' && args !== null ? args : { base: args }
const skepticsPerFinding = input.skeptics || 1
const head = input.head || 'HEAD'
const jevScript = input.jev || ''
const forceFull = Boolean(input.full)
// At or under this many changed lines, with Jev finding no structural file, one reviewer covers both axes.
const LIGHT_MAX_CHANGED_LINES = 50

const SCOPE_SCHEMA = {
  type: 'object',
  required: ['base', 'head', 'diffCommand', 'shortstat', 'commits', 'files', 'standardsSources', 'spec'],
  properties: {
    base: { type: 'string', description: 'Resolved commit SHA of the fixed point' },
    head: { type: 'string', description: 'Resolved commit SHA of the head under review' },
    diffCommand: { type: 'string' },
    shortstat: { type: 'string', description: 'The line git diff --shortstat prints, verbatim; empty when it could not be read' },
    commits: { type: 'array', items: { type: 'string' } },
    files: { type: 'array', items: { type: 'string' } },
    standardsSources: { type: 'array', items: { type: 'string' } },
    spec: {
      type: 'object',
      required: ['found', 'source', 'id', 'text'],
      properties: {
        found: { type: 'boolean' },
        source: { type: 'string', description: 'Issue URL, issue id, or file path; empty when not found' },
        id: { type: 'string', description: 'The id of the issue fetched, exactly as the tracker writes it (42, bd-a1b2.3, group/project#12); empty for a spec file or when not found' },
        text: { type: 'string', description: 'User stories, AC-N, and interfaces verbatim; empty when not found' },
        problem: { type: 'string', description: 'Why a given issue could not be fetched; empty otherwise' },
      },
    },
    problem: { type: 'string', description: 'Why scoping failed; empty on success' },
    risk: {
      type: 'object',
      description: 'Copied from jev.py review-risk; omit when no jev path was given',
      required: ['ranked', 'structural', 'files'],
      properties: {
        ranked: { type: 'boolean', description: 'false when review-risk exited non-zero' },
        structural: { type: 'boolean' },
        files: {
          type: 'array',
          items: {
            type: 'object',
            required: ['file', 'score', 'structural'],
            properties: { file: { type: 'string' }, score: { type: 'number' }, structural: { type: 'boolean' } },
          },
        },
        problem: { type: 'string', description: 'The first line of stderr when review-risk failed' },
      },
    },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'line', 'severity', 'claim', 'evidence'],
        properties: {
          file: { type: 'string' },
          line: { type: ['integer', 'null'], description: 'null when the finding is about something absent from the diff' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'The rule or AC-N quoted with its file, plus the code quoted at file:line' },
          skeptic: { type: 'boolean', description: 'worth_skeptic from jev.py triage-finding; omit when Jev was unavailable' },
        },
      },
    },
  },
}

function lightFindingsSchema(axisNames) {
  const item = FINDINGS_SCHEMA.properties.findings.items
  return {
    type: 'object',
    required: ['findings', 'checked'],
    properties: {
      findings: {
        type: 'array',
        items: {
          ...item,
          required: [...item.required, 'axis'],
          properties: { ...item.properties, axis: { type: 'string', enum: axisNames } },
        },
      },
      checked: {
        type: 'object',
        description: 'For each axis, what you checked: the rules read against the diff, and for Spec each AC-N with its verdict',
        required: axisNames,
        properties: Object.fromEntries(axisNames.map(name => [name, { type: 'string' }])),
      },
    },
  }
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['refuted', 'reason'],
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string', description: 'What you checked, with file:line, and what it showed' },
  },
}

const SMELL_BASELINE = `Smell baseline (Fowler, Refactoring ch. 3). Each is a judgement call, never a hard violation, and a documented repo standard overrides it:
- Mysterious Name: a name that does not reveal what it does or holds.
- Duplicated Code: the same logic shape in more than one hunk or file of the change.
- Feature Envy: a function reaching into another object's data more than its own.
- Data Clumps: the same few fields or params travelling together.
- Primitive Obsession: a primitive standing in for a domain concept that deserves a type.
- Repeated Switches: the same switch or if-cascade on the same type recurring.
- Shotgun Surgery: one logical change forcing scattered edits across many files.
- Divergent Change: one module edited for several unrelated reasons.
- Speculative Generality: abstraction, parameters, or hooks the spec does not need.
- Message Chains: long a.b().c().d() navigation the caller should not depend on.
- Middle Man: a class or function that mostly delegates onward.
- Refused Bequest: an implementer that ignores or overrides most of what it inherits.`

phase('Scope')

const baseHint = input.base
  ? `The fixed point is \`${input.base}\`.`
  : `No fixed point was given: use the merge-base of \`${head}\` with the default branch (\`git merge-base ${head} origin/HEAD\`, falling back to \`main\` then \`master\`).`

// Tracker ids are strings: a bare number reads as #42, while bd-a1b2.3 or group/project#12 stand as written.
function issueRef(id) {
  const bare = String(id).replace(/^#/, '')
  return /^\d+$/.test(bare) ? `#${bare}` : bare
}
const issueId = input.issue ? String(input.issue).replace(/^#/, '') : ''

const issueHint = input.issue
  ? `The originating issue is \`${issueId}\` and no other: fetch it even if the conversation names a different one.`
  : 'No issue was given: look for issue references in the commit messages (#123, Closes #45) and in the branch name, then for a spec file under docs/, specs/, or .scratch/ matching the branch.'

const riskStep = jevScript
  ? `\n4. Rank the changed files by structural risk: write \`{"base": "<base-sha>", "head": "<head-sha>"}\` to a temp file and run \`uv run ${jevScript} review-risk --input <file>\`. Set risk to \`{ranked: true, structural, files}\` from its output, keeping each file's file, score, and structural. If it exits non-zero, set risk to \`{ranked: false, structural: false, files: [], problem: "<first line of stderr>"}\`.`
  : ''

const scope = await agent(
  `Scope a code review of the changes up to \`${head}\`. Do not review anything yet.

${baseHint} The head under review is \`${head}\`.
1. Resolve the fixed point and the head with \`git rev-parse\`. Record diffCommand as \`git diff <base-sha>...<head-sha>\` (three dots, against the merge-base), shortstat as the line \`git diff --shortstat <base-sha>...<head-sha>\` prints, verbatim, the commits from \`git log --oneline <base-sha>..<head-sha>\`, and the changed files from \`git diff --name-only <base-sha>...<head-sha>\`.
2. ${issueHint} Fetch it, with its comments, using the read command docs/agents/issue-tracker.md gives for this repo's tracker, and pass the id to it exactly as written: it may be dotted (bd-a1b2.3) or name another project (group/project#12), so never turn it into a number or drop its project. Only if that file is missing, use \`gh api repos/{owner}/{repo}/issues/<n>\` and \`gh api repos/{owner}/{repo}/issues/<n>/comments --paginate\`. Wherever the read goes through \`gh\`, use \`gh api\` (REST): \`gh issue view\` goes through GraphQL, which cloud sessions block. Copy its user stories, every AC-N, and any interfaces verbatim into spec.text. If an issue was given and fetching it fails, set spec to \`{found: false, source: "", id: "", text: "", problem: "<the error you got>"}\` and carry on with the rest. Set spec.id to the id of the issue you fetched, as the tracker writes it, or "" for a spec file.
3. List the standards sources that exist: CLAUDE.md and AGENTS.md at the root and in directories the diff touches, CONTEXT.md or CONTEXT-MAP.md, docs/adr/*.md, CODING_STANDARDS.md, CONTRIBUTING.md, and linter or formatter configs (so reviewers know what tooling already enforces).${riskStep}

If the fixed point does not resolve or the diff is empty, say so in problem and return every other field empty: base, head, diffCommand, and shortstat as "", commits, files, and standardsSources as [], and spec as \`{found: false, source: "", id: "", text: ""}\`.`,
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA, effort: 'low' },
)

if (!scope || scope.problem || scope.files.length === 0) {
  const problem = scope ? scope.problem || 'The diff is empty.' : 'The scoping agent did not return.'
  log(problem)
  return { complete: false, problem }
}

const specSource = input.issue ? issueRef(issueId) : scope.spec.source

function issueFetchProblem() {
  if (!input.issue) return ''
  if (!scope.spec.found) return scope.spec.problem || 'the scoping agent returned no spec'
  if (issueRef(scope.spec.id) !== specSource) return `the scoping agent fetched ${issueRef(scope.spec.id)} instead`
  return ''
}

const fetchProblem = issueFetchProblem()
const specProblem = fetchProblem ? `issue ${specSource} could not be fetched: ${fetchProblem}` : ''
if (specProblem) log(specProblem)

log(`Reviewing ${scope.files.length} files across ${scope.commits.length} commits since ${scope.base.slice(0, 8)}`)

const readAtHead = head === 'HEAD'
  ? ''
  : `\nThe working tree may not be at the head under review: read changed files with \`git show ${scope.head}:<path>\`, not from disk.`

const risk = jevScript && scope.risk && scope.risk.ranked
  ? { ranked: true, structural: scope.risk.structural, files: scope.risk.files }
  : { ranked: false, structural: null, files: [], problem: riskProblem() }

function riskProblem() {
  if (!jevScript) return 'no jev path given'
  if (!scope.risk) return 'the scoping agent returned no risk ranking'
  return scope.risk.problem || 'review-risk failed'
}

const fileList = risk.ranked
  ? `Changed files, riskiest first (structural risk 0-4 from Jev; read the top ones first):
${risk.files.map(f => `${f.file} (${f.score.toFixed(2)}${f.structural ? ', structural' : ''})`).join('\n')}`
  : `Changed files:
${scope.files.join('\n')}`

const diffContext = `Diff: \`${scope.diffCommand}\`${readAtHead}
Commits:
${scope.commits.join('\n')}
${fileList}`

const SPEC_ONLY = `Grade only against the spec text in this prompt. Do not fetch any issue or spec file yourself (no \`gh issue view\`, no \`gh api\` on issues), even when the diff, the commits, or the conversation name a different one.`

const AXES = [
  {
    name: 'Standards',
    question: "does the code follow this repo's documented standards and domain language?",
    active: true,
    checks: `Standards sources in this repo:
${scope.standardsSources.join('\n') || '(none documented)'}

Check the diff against:
- Every rule in the instructions files and contributing guides above. Cite the file and the rule.
- CONTEXT.md vocabulary: names in the diff that contradict or bypass the glossary's terms.
- ADRs in docs/adr/: changes that go against a recorded decision without a superseding ADR.
- Doc drift: a line in an instructions file, README, or other doc that describes the changed code and no longer matches it after this diff. Cite the doc's file and line.
- The compost canon essays your agent definition points you to, where one applies.
- The smell baseline below.

${SMELL_BASELINE}

Skip anything a linter, formatter, or type checker configured in this repo already enforces.`,
  },
  {
    name: 'Spec',
    question: 'does the code do what the originating issue asked, no more and no less?',
    active: scope.spec.found && !specProblem,
    problem: specProblem,
    checks: `Spec source: ${specSource}
${scope.spec.text}

${SPEC_ONLY}

Report:
- Each AC-N that is missing or only partly met. Quote the AC-N; point at the test that should prove it, or say none exists.
- Each interface in the spec whose shape in the code differs from what the spec states.
- Behaviour in the diff nobody asked for (scope creep), at file:line.
- Each AC-N that looks implemented but where the implementation looks wrong.`,
  },
]

function axisPrompt(axis) {
  return `Review this diff on the ${axis.name} axis: ${axis.question}

${diffContext}

${axis.checks}`
}

function lightPrompt(axes) {
  const names = axes.map(axis => axis.name)
  const sections = axes.map(axis => `## ${axis.name} axis: ${axis.question}\n\n${axis.checks}`).join('\n\n')
  return `This diff is small, so you review it alone on ${names.length === 1 ? 'one axis' : 'both axes'}: ${names.join(' and ')}. Keep the axes apart as two reviewers would: set each finding's axis to ${names.map(name => `"${name}"`).join(' or ')}, and under checked say for each axis what you checked, so an axis with no findings reads as looked at, not skipped. Small is no reason to look less hard; it is a reason one reviewer can hold the whole diff.

${diffContext}

${sections}`
}

function skepticPrompt(axis, finding) {
  const location = finding.line === null ? finding.file : `${finding.file}:${finding.line}`
  const specText = axis.name === 'Spec' ? `\nThe spec the finding was judged against:\n${scope.spec.text}\n${SPEC_ONLY}\n` : ''
  return `A reviewer made the ${axis.name} finding below about the diff \`${scope.diffCommand}\`. Your job is to refute it.${readAtHead}
${specText}
Finding (${finding.severity}) at ${location}:
Claim: ${finding.claim}
Evidence: ${finding.evidence}

Read the code at that location and whatever it depends on. Check that the quoted rule or AC-N exists and says what the reviewer claims, that the code does what the claim says, and that nothing elsewhere (a test, a caller, a documented exception, a later hunk) already answers it. A finding that is a style nit a configured linter owns, or that asks for something nobody uses (YAGNI), is refuted.

Set refuted to true unless you confirmed the finding yourself against the code. When you are uncertain, it is refuted.`
}

async function judge(axis, finding, index) {
  const votes = await parallel(
    Array.from({ length: skepticsPerFinding }, (_, vote) => () =>
      agent(skepticPrompt(axis, finding), {
        label: `${axis.name} skeptic ${index + 1}.${vote + 1}`,
        phase: axis.name,
        schema: VERDICT_SCHEMA,
      }),
    ),
  )
  const cast = votes.filter(Boolean)
  const upheld = cast.filter(v => !v.refuted).length
  let verdict = 'refuted'
  if (cast.length === 0) verdict = 'unjudged'
  else if (upheld * 2 > cast.length) verdict = 'survived'
  return {
    finding,
    verdict,
    failed: votes.length - cast.length,
    reasons: cast.map(v => v.reason),
  }
}

function worthSkeptic(finding) {
  return typeof finding.skeptic === 'boolean' ? finding.skeptic : finding.severity !== 'minor'
}

function unjudgedAfterThrow(finding) {
  return { finding, verdict: 'unjudged', failed: skepticsPerFinding, reasons: ['the skeptic stage threw'] }
}

function failedAxis(name, status) {
  return { axis: name, status: `failed: ${status}`, complete: false, survivors: [], refuted: [], unjudged: [] }
}

function changedLines(shortstat) {
  const count = kind => Number((String(shortstat || '').match(new RegExp(`(\\d+) ${kind}`)) || [0, 0])[1])
  return /\d+ files? changed/.test(shortstat || '') ? count('insertion') + count('deletion') : null
}

// A light review has to prove the diff small and not structural; an unreadable line count, or structural risk
// nobody ranked, runs it in full.
const lineCount = changedLines(scope.shortstat)
const light = !forceFull
  && lineCount !== null
  && lineCount <= LIGHT_MAX_CHANGED_LINES
  && risk.structural === false

async function settleAxis(review, axis) {
  if (review && review.skipped && axis.problem) return failedAxis(axis.name, axis.problem)
  if (review && review.skipped) {
    return { axis: axis.name, status: 'skipped: no spec found', complete: true, survivors: [], refuted: [], unjudged: [] }
  }
  if (!review) return failedAxis(axis.name, 'the reviewer did not return')
  if (light && !String(review.checked || '').trim()) return failedAxis(axis.name, 'the reviewer did not say what it checked on this axis')
  const serious = review.findings.filter(worthSkeptic)
  const unverified = review.findings
    .filter(finding => !worthSkeptic(finding))
    .map(finding => ({ ...finding, unverified: true }))
  const judged = (await pipeline(serious, (finding, _item, index) => judge(axis, finding, index)))
    .map((j, i) => j || unjudgedAfterThrow(serious[i]))
  const withVerdict = verdict => judged.filter(j => j.verdict === verdict)
  const unjudged = withVerdict('unjudged')
  if (unjudged.length > 0) log(`${axis.name}: ${unjudged.length} findings have no skeptic verdict`)
  return {
    axis: axis.name,
    status: `${light ? 'reviewed (light)' : 'reviewed'}: ${review.findings.length} findings raised, ${unverified.length} left unverified`,
    complete: true,
    ...(light ? { checked: review.checked } : {}),
    survivors: [
      ...withVerdict('survived').map(j => ({ ...j.finding, upheldBecause: j.reasons, failedVotes: j.failed })),
      ...unverified,
    ],
    refuted: withVerdict('refuted').map(j => ({ ...j.finding, refutedBecause: j.reasons, failedVotes: j.failed })),
    unjudged: unjudged.map(j => ({ ...j.finding, reasons: j.reasons, failedVotes: j.failed })),
  }
}

function reviewOne(axis) {
  if (!axis.active) return { skipped: true, findings: [] }
  return agent(axisPrompt(axis), {
    label: `${axis.name} reviewer`,
    phase: axis.name,
    schema: FINDINGS_SCHEMA,
    agentType: 'compost:reviewer',
  })
}

async function reviewLight() {
  const active = AXES.filter(axis => axis.active)
  const review = await agent(lightPrompt(active), {
    label: 'Light reviewer',
    phase: 'Standards',
    schema: lightFindingsSchema(active.map(axis => axis.name)),
    agentType: 'compost:reviewer',
  }).catch(() => null)
  // The schema allows only active axes; a finding that slips through untagged stays under Standards, never dropped.
  const axisOf = finding => (active.some(axis => axis.name === finding.axis) ? finding.axis : 'Standards')
  const share = axis => review && {
    findings: review.findings.filter(finding => axisOf(finding) === axis.name),
    checked: (review.checked || {})[axis.name],
  }
  return pipeline(AXES, axis => (axis.active ? share(axis) : { skipped: true, findings: [] }), settleAxis)
}

const results = light ? await reviewLight() : await pipeline(AXES, reviewOne, settleAxis)

const [standards, spec] = results.map((result, i) => result || failedAxis(AXES[i].name, 'the review stage threw'))

function worst(axisResult) {
  const order = ['blocker', 'major', 'minor']
  const sorted = [...axisResult.survivors].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity))
  return sorted.length ? `${sorted[0].severity}: ${sorted[0].claim}` : 'none'
}

return {
  base: scope.base,
  head: scope.head,
  specSource,
  risk,
  path: light ? 'light' : 'full',
  complete: standards.complete && spec.complete,
  standards,
  spec,
  summary: [standards, spec]
    .map(a => `${a.axis}: ${a.status}, ${a.survivors.length} survived, ${a.refuted.length} refuted, ${a.unjudged.length} unjudged; worst ${worst(a)}`)
    .join('\n'),
}
