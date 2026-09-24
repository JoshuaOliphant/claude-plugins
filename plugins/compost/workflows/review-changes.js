// ABOUTME: Compost's review workflow: Standards and Spec reviewers in parallel over a branch diff.
// ABOUTME: Skeptic agents try to refute each blocker and major finding; survivors and refutations come back side by side.
export const meta = {
  name: 'review-changes',
  description: 'Review a branch along two axes, Standards and Spec, then have skeptics try to refute every blocker and major finding',
  whenToUse: 'After verify passes on an issue, or whenever a branch or work-in-progress diff needs review. Pass {base, head, issue}; all are optional, and head defaults to HEAD.',
  phases: [
    { title: 'Scope', detail: 'pin the base, the diff, the spec, and the standards sources' },
    { title: 'Standards', detail: 'reviewer against instructions files, CONTEXT.md, ADRs, and the canon; skeptics refute each blocker and major' },
    { title: 'Spec', detail: 'reviewer against the issue AC-N and interfaces; skeptics refute each blocker and major' },
  ],
}

const input = typeof args === 'object' && args !== null ? args : { base: args }
const skepticsPerFinding = input.skeptics || 1
const head = input.head || 'HEAD'

const SCOPE_SCHEMA = {
  type: 'object',
  required: ['base', 'head', 'diffCommand', 'commits', 'files', 'standardsSources', 'spec'],
  properties: {
    base: { type: 'string', description: 'Resolved commit SHA of the fixed point' },
    head: { type: 'string', description: 'Resolved commit SHA of the head under review' },
    diffCommand: { type: 'string' },
    commits: { type: 'array', items: { type: 'string' } },
    files: { type: 'array', items: { type: 'string' } },
    standardsSources: { type: 'array', items: { type: 'string' } },
    spec: {
      type: 'object',
      required: ['found', 'source', 'text'],
      properties: {
        found: { type: 'boolean' },
        source: { type: 'string', description: 'Issue URL, issue number, or file path; empty when not found' },
        text: { type: 'string', description: 'User stories, AC-N, and interfaces verbatim; empty when not found' },
      },
    },
    problem: { type: 'string', description: 'Why scoping failed; empty on success' },
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
        },
      },
    },
  },
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

const issueHint = input.issue
  ? `The originating issue is #${input.issue}.`
  : 'No issue was given: look for issue references in the commit messages (#123, Closes #45) and in the branch name, then for a spec file under docs/, specs/, or .scratch/ matching the branch.'

const scope = await agent(
  `Scope a code review of the changes up to \`${head}\`. Do not review anything yet.

${baseHint} The head under review is \`${head}\`.
1. Resolve the fixed point and the head with \`git rev-parse\`. Record diffCommand as \`git diff <base-sha>...<head-sha>\` (three dots, against the merge-base), the commits from \`git log --oneline <base-sha>..<head-sha>\`, and the changed files from \`git diff --name-only <base-sha>...<head-sha>\`.
2. ${issueHint} Fetch the issue the way docs/agents/issue-tracker.md says; if that file is missing, use \`gh issue view <n> --comments\`. Copy its user stories, every AC-N, and any interfaces verbatim into spec.text.
3. List the standards sources that exist: CLAUDE.md and AGENTS.md at the root and in directories the diff touches, CONTEXT.md or CONTEXT-MAP.md, docs/adr/*.md, CODING_STANDARDS.md, CONTRIBUTING.md, and linter or formatter configs (so reviewers know what tooling already enforces).

If the fixed point does not resolve or the diff is empty, say so in problem and leave the other fields empty.`,
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA, effort: 'low' },
)

if (!scope || scope.problem || scope.files.length === 0) {
  const problem = scope ? scope.problem || 'The diff is empty.' : 'The scoping agent did not return.'
  log(problem)
  return { problem }
}

log(`Reviewing ${scope.files.length} files across ${scope.commits.length} commits since ${scope.base.slice(0, 8)}`)

const readAtHead = head === 'HEAD'
  ? ''
  : `\nThe working tree may not be at the head under review: read changed files with \`git show ${scope.head}:<path>\`, not from disk.`

const diffContext = `Diff: \`${scope.diffCommand}\`${readAtHead}
Commits:
${scope.commits.join('\n')}
Changed files:
${scope.files.join('\n')}`

const AXES = [
  {
    name: 'Standards',
    active: true,
    prompt: `Review this diff on the Standards axis: does the code follow this repo's documented standards and domain language?

${diffContext}

Standards sources in this repo:
${scope.standardsSources.join('\n') || '(none documented)'}

Check the diff against:
- Every rule in the instructions files and contributing guides above. Cite the file and the rule.
- CONTEXT.md vocabulary: names in the diff that contradict or bypass the glossary's terms.
- ADRs in docs/adr/: changes that go against a recorded decision without a superseding ADR.
- The compost canon essays your agent definition points you to, where one applies.
- The smell baseline below.

${SMELL_BASELINE}

Skip anything a linter, formatter, or type checker configured in this repo already enforces.`,
  },
  {
    name: 'Spec',
    active: scope.spec.found,
    prompt: `Review this diff on the Spec axis: does the code do what the originating issue asked, no more and no less?

${diffContext}

Spec source: ${scope.spec.source}
${scope.spec.text}

Report:
- Each AC-N that is missing or only partly met. Quote the AC-N; point at the test that should prove it, or say none exists.
- Each interface in the spec whose shape in the code differs from what the spec states.
- Behaviour in the diff nobody asked for (scope creep), at file:line.
- Each AC-N that looks implemented but where the implementation looks wrong.`,
  },
]

function skepticPrompt(axis, finding) {
  const location = finding.line === null ? finding.file : `${finding.file}:${finding.line}`
  const specText = axis.name === 'Spec' ? `\nThe spec the finding was judged against:\n${scope.spec.text}\n` : ''
  return `A reviewer made the ${axis.name} finding below about the diff \`${scope.diffCommand}\`. Your job is to refute it.${readAtHead}
${specText}
Finding (${finding.severity}) at ${location}:
Claim: ${finding.claim}
Evidence: ${finding.evidence}

Read the code at that location and whatever it depends on. Check that the quoted rule or AC-N exists and says what the reviewer claims, that the code does what the claim says, and that nothing elsewhere (a test, a caller, a documented exception, a later hunk) already answers it. A finding that is a style nit a configured linter owns, or that asks for something nobody uses (YAGNI), is refuted.

Set refuted to true unless you confirmed the finding yourself against the code. When you are uncertain, it is refuted.`
}

async function survives(axis, finding, index) {
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
  return {
    finding,
    survived: cast.length > 0 && upheld * 2 > cast.length,
    reasons: cast.map(v => v.reason),
  }
}

const results = await pipeline(
  AXES,
  axis => {
    if (!axis.active) return { skipped: true, findings: [] }
    return agent(axis.prompt, {
      label: `${axis.name} reviewer`,
      phase: axis.name,
      schema: FINDINGS_SCHEMA,
      agentType: 'compost:reviewer',
    })
  },
  async (review, axis) => {
    if (review && review.skipped) return { axis: axis.name, status: 'skipped: no spec found', survivors: [], refuted: [] }
    if (!review) return { axis: axis.name, status: 'failed: the reviewer did not return', survivors: [], refuted: [] }
    const serious = review.findings.filter(finding => finding.severity !== 'minor')
    const unverified = review.findings
      .filter(finding => finding.severity === 'minor')
      .map(finding => ({ ...finding, unverified: true }))
    const judged = await pipeline(serious, (finding, _item, index) => survives(axis, finding, index))
    const complete = judged.filter(Boolean)
    const lost = judged.length - complete.length
    if (lost > 0) log(`${axis.name}: ${lost} findings lost their skeptic run and are left out`)
    return {
      axis: axis.name,
      status: `reviewed: ${review.findings.length} findings raised, ${unverified.length} minor left unverified`,
      survivors: [
        ...complete.filter(j => j.survived).map(j => ({ ...j.finding, upheldBecause: j.reasons })),
        ...unverified,
      ],
      refuted: complete.filter(j => !j.survived).map(j => ({ ...j.finding, refutedBecause: j.reasons })),
    }
  },
)

const [standards, spec] = results.map((result, i) =>
  result || { axis: AXES[i].name, status: 'failed: the review stage threw', survivors: [], refuted: [] },
)

function worst(axisResult) {
  const order = ['blocker', 'major', 'minor']
  const sorted = [...axisResult.survivors].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity))
  return sorted.length ? `${sorted[0].severity}: ${sorted[0].claim}` : 'none'
}

return {
  base: scope.base,
  head: scope.head,
  specSource: scope.spec.source,
  standards,
  spec,
  summary: [standards, spec]
    .map(a => `${a.axis}: ${a.status}, ${a.survivors.length} survived, ${a.refuted.length} refuted; worst ${worst(a)}`)
    .join('\n'),
}
