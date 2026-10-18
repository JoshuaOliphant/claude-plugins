// ABOUTME: Runs workflows/review-changes.js against stub agent/parallel/pipeline hooks that follow the Workflow
// ABOUTME: tool's contract (a failed agent returns null, parallel and pipeline turn throws into null) to pin its verdicts.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const source = readFileSync(new URL('../workflows/review-changes.js', import.meta.url), 'utf8')
const AsyncFunction = (async () => {}).constructor
const script = new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'phase', 'log', source.replace('export const meta', 'const meta'))

const SCOPE = {
  base: 'b'.repeat(40),
  head: 'h'.repeat(40),
  diffCommand: 'git diff bbb...hhh',
  commits: ['abc1234 add export'],
  files: ['app/export.py'],
  standardsSources: ['CLAUDE.md'],
  spec: { found: true, source: '#7', number: 7, text: 'AC-1: Given a list, When exported, Then a CSV downloads' },
}
const BLOCKER = { file: 'app/export.py', line: 12, severity: 'blocker', claim: 'CSV is not escaped', evidence: 'AC-1 at #7; app/export.py:12' }
const MINOR = { file: 'app/export.py', line: 3, severity: 'minor', claim: 'name drifts from CONTEXT.md', evidence: 'CONTEXT.md: Reading list' }

async function run(args, answer) {
  const prompts = {}
  const agent = async (prompt, opts) => {
    prompts[opts.label] = prompt
    return answer(opts.label, prompt)
  }
  const parallel = thunks => Promise.all(thunks.map(thunk => thunk().catch(() => null)))
  const pipeline = (items, ...stages) =>
    Promise.all(items.map(async (item, index) => {
      try {
        let previous = item
        for (const stage of stages) previous = await stage(previous, item, index)
        return previous
      } catch {
        return null
      }
    }))
  const result = await script(args, agent, parallel, pipeline, () => {}, () => {})
  return { result, prompts }
}

function reviewers({ standards = { findings: [BLOCKER, MINOR] }, spec = { findings: [] }, light = { findings: [] }, skeptic = { refuted: false, reason: 'confirmed' }, scope = SCOPE } = {}) {
  return label => {
    if (label === 'scope') return scope
    if (label === 'Standards reviewer') return typeof standards === 'function' ? standards() : standards
    if (label === 'Spec reviewer') return spec
    if (label === 'Light reviewer') return light
    return typeof skeptic === 'function' ? skeptic(label) : skeptic
  }
}

test('a confirmed blocker survives and a minor finding is kept unverified without a skeptic', async () => {
  const { result, prompts } = await run({ issue: 7 }, reviewers())
  assert.equal(result.complete, true)
  assert.deepEqual(result.standards.survivors.map(f => f.severity), ['blocker', 'minor'])
  assert.equal(result.standards.survivors[1].unverified, true)
  assert.deepEqual(Object.keys(prompts).filter(label => label.includes('skeptic')), ['Standards skeptic 1.1'])
  assert.match(result.summary, /Standards: reviewed: 2 findings raised, 1 left unverified, 2 survived, 0 refuted, 0 unjudged; worst blocker/)
})

test('with Jev triage, the skeptic flag decides who gets a skeptic, whatever the severity', async () => {
  const confidentMajor = { ...BLOCKER, severity: 'major', line: 20, skeptic: false }
  const unsureMinor = { ...MINOR, skeptic: true }
  const { result, prompts } = await run({}, reviewers({ standards: { findings: [confidentMajor, unsureMinor] } }))
  assert.deepEqual(Object.keys(prompts).filter(label => label.includes('skeptic')), ['Standards skeptic 1.1'])
  assert.match(prompts['Standards skeptic 1.1'], /name drifts from CONTEXT\.md/)
  assert.deepEqual(result.standards.survivors.map(f => [f.line, f.unverified === true]), [[3, false], [20, true]])
})

test('given a jev path, scope ranks files by structural risk and reviewers read the riskiest first', async () => {
  const risk = {
    ranked: true,
    structural: true,
    files: [{ file: 'app/cache.py', score: 3.4, structural: true }, { file: 'app/export.py', score: 1.2, structural: false }],
  }
  const { result, prompts } = await run({ jev: '/plugin/scripts/jev.py' }, reviewers({ scope: { ...SCOPE, risk } }))
  assert.match(prompts.scope, /uv run \/plugin\/scripts\/jev\.py review-risk --input/)
  assert.match(prompts['Standards reviewer'], /riskiest first[^\n]*\napp\/cache\.py \(3\.40, structural\)\napp\/export\.py \(1\.20\)/)
  assert.deepEqual(result.risk, risk)
})

test('without a jev path, or when review-risk fails, files keep scope order and structural risk is unknown', async () => {
  const plain = await run({}, reviewers())
  assert.doesNotMatch(plain.prompts.scope, /review-risk/)
  assert.match(plain.prompts['Standards reviewer'], /Changed files:\napp\/export\.py/)
  assert.deepEqual(plain.result.risk, { ranked: false, structural: null, files: [], problem: 'no jev path given' })
  const failedRisk = { ranked: false, structural: false, files: [], problem: 'jev unavailable: no key' }
  const failed = await run({ jev: '/plugin/scripts/jev.py' }, reviewers({ scope: { ...SCOPE, risk: failedRisk } }))
  assert.equal(failed.result.risk.structural, null)
  assert.equal(failed.result.risk.problem, 'jev unavailable: no key')
  const silent = await run({ jev: '/plugin/scripts/jev.py' }, reviewers({ scope: { ...SCOPE, risk: { ...failedRisk, problem: undefined } } }))
  assert.equal(silent.result.risk.problem, 'review-risk failed')
})

test('a blocker whose every skeptic failed is unjudged, not refuted', async () => {
  const { result } = await run({}, reviewers({ skeptic: null }))
  assert.deepEqual(result.standards.refuted, [])
  assert.equal(result.standards.unjudged.length, 1)
  assert.equal(result.standards.unjudged[0].failedVotes, 1)
  assert.equal(result.complete, true)
})

test('with three skeptics, a failed vote does not count and a split among the rest refutes', async () => {
  const votes = { '1': null, '2': { refuted: false, reason: 'holds' }, '3': { refuted: true, reason: 'tested elsewhere' } }
  const skeptic = label => votes[label.split('.').pop()]
  const { result } = await run({ skeptics: 3 }, reviewers({ skeptic }))
  assert.equal(result.standards.refuted.length, 1)
  assert.equal(result.standards.refuted[0].failedVotes, 1)
  assert.deepEqual(result.standards.refuted[0].refutedBecause, ['holds', 'tested elsewhere'])
})

test('a reviewer that returns nothing or throws marks its axis and the review incomplete', async () => {
  const silent = await run({}, reviewers({ standards: null }))
  assert.equal(silent.result.standards.status, 'failed: the reviewer did not return')
  assert.equal(silent.result.complete, false)
  const thrown = await run({}, reviewers({ standards: () => { throw new Error('boom') } }))
  assert.equal(thrown.result.standards.status, 'failed: the review stage threw')
  assert.equal(thrown.result.complete, false)
})

test('an issue that cannot be fetched fails the Spec axis instead of skipping it', async () => {
  const scope = { ...SCOPE, spec: { found: false, source: '', number: null, text: '', problem: 'gh: not authenticated' } }
  const { result, prompts } = await run({ issue: 42 }, reviewers({ scope }))
  assert.equal(result.spec.status, 'failed: issue #42 could not be fetched: gh: not authenticated')
  assert.equal(result.complete, false)
  assert.equal(prompts['Spec reviewer'], undefined)
})

test('a given issue is the only spec source, whatever issue the scoping agent picked from the conversation', async () => {
  const relayed = { ...SCOPE, spec: { ...SCOPE.spec, source: '#53' } }
  const graded = await run({ issue: 7 }, reviewers({ scope: relayed, spec: { findings: [BLOCKER] } }))
  assert.equal(graded.result.specSource, '#7')
  assert.match(graded.prompts['Spec reviewer'], /Spec source: #7\n/)
  for (const label of ['Spec reviewer', 'Spec skeptic 1.1']) {
    const prompt = graded.prompts[label]
    assert.ok(prompt.includes(SCOPE.spec.text), `${label} carries the spec text`)
    assert.match(prompt, /Grade only against the spec text in this prompt\. Do not fetch any issue or spec file yourself/)
  }

  const swapped = { ...SCOPE, spec: { found: true, source: '#53', number: 53, text: 'AC-1: Given issue 53' } }
  const refused = await run({ issue: 7 }, reviewers({ scope: swapped }))
  assert.equal(refused.result.specSource, '#7')
  assert.equal(refused.result.spec.status, 'failed: issue #7 could not be fetched: the scoping agent fetched #53 instead')
  assert.equal(refused.result.complete, false)
  assert.equal(refused.prompts['Spec reviewer'], undefined)
})

test('without an issue, the spec source is what scope found, and a missing spec skips the Spec axis', async () => {
  const specFile = { ...SCOPE, spec: { found: true, source: 'docs/specs/export.md', number: null, text: 'AC-1: Given a list' } }
  const found = await run({}, reviewers({ scope: specFile }))
  assert.equal(found.result.specSource, 'docs/specs/export.md')
  assert.match(found.prompts['Spec reviewer'], /Spec source: docs\/specs\/export\.md\n/)

  const scope = { ...SCOPE, spec: { found: false, source: '', number: null, text: '' } }
  const { result } = await run({}, reviewers({ scope }))
  assert.equal(result.spec.status, 'skipped: no spec found')
  assert.equal(result.specSource, '')
  assert.equal(result.complete, true)
})

test('a failed scope or an empty diff returns the problem and spawns no reviewers', async () => {
  for (const [scope, problem] of [[null, 'The scoping agent did not return.'], [{ ...SCOPE, files: [] }, 'The diff is empty.']]) {
    const { result, prompts } = await run({}, reviewers({ scope }))
    assert.deepEqual(result, { complete: false, problem })
    assert.deepEqual(Object.keys(prompts), ['scope'])
  }
})

test('a bare string is the base, and a head other than HEAD tells every agent to read files at that commit', async () => {
  const bare = await run('release-1.2', reviewers())
  assert.match(bare.prompts.scope, /release-1\.2/)
  const pinned = await run({ base: 'abc^1', head: 'abc^2' }, reviewers())
  assert.match(pinned.prompts['Standards reviewer'], /git show h{40}:<path>/)
  assert.match(pinned.prompts['Standards skeptic 1.1'], /git show h{40}:<path>/)
})

const SMALL = { ...SCOPE, changedLines: 50 }
const reviewerLabels = prompts => Object.keys(prompts).filter(label => label.endsWith('reviewer'))

test('a diff of 50 changed lines or fewer gets one reviewer on both axes, split back by axis tag', async () => {
  const specBlocker = { ...BLOCKER, line: 30, claim: 'AC-1 has no test', axis: 'Spec' }
  const light = { findings: [{ ...BLOCKER, axis: 'Standards' }, { ...MINOR, axis: 'Standards' }, specBlocker] }
  const { result, prompts } = await run({ issue: 7 }, reviewers({ scope: SMALL, light }))
  assert.equal(result.path, 'light')
  assert.deepEqual(reviewerLabels(prompts), ['Light reviewer'])
  assert.match(prompts['Light reviewer'], /Standards axis/)
  assert.match(prompts['Light reviewer'], /Spec axis/)
  assert.ok(prompts['Light reviewer'].includes(SCOPE.spec.text))
  assert.match(prompts['Light reviewer'], /Grade only against the spec text in this prompt/)
  assert.deepEqual(result.standards.survivors.map(f => f.claim), ['CSV is not escaped', 'name drifts from CONTEXT.md'])
  assert.deepEqual(result.spec.survivors.map(f => f.claim), ['AC-1 has no test'])
  assert.deepEqual(Object.keys(prompts).filter(label => label.includes('skeptic')).sort(), ['Spec skeptic 1.1', 'Standards skeptic 1.1'])
  assert.equal(result.complete, true)
  assert.match(result.summary, /Standards: reviewed \(light\): 2 findings raised, 1 left unverified/)
})

test('over 50 changed lines, a structural file, no line count, or full: true runs the two-reviewer path', async () => {
  const structural = { ranked: true, structural: true, files: [{ file: 'app/export.py', score: 3.1, structural: true }] }
  const cases = [
    [{}, { ...SCOPE, changedLines: 51 }],
    [{ jev: '/plugin/scripts/jev.py' }, { ...SMALL, risk: structural }],
    [{}, SCOPE],
    [{}, { ...SCOPE, changedLines: null }],
    [{ full: true }, SMALL],
  ]
  for (const [args, scope] of cases) {
    const { result, prompts } = await run(args, reviewers({ scope }))
    assert.equal(result.path, 'full', JSON.stringify(args) + JSON.stringify(scope.changedLines))
    assert.deepEqual(reviewerLabels(prompts), ['Standards reviewer', 'Spec reviewer'])
  }
})

test('a scope prompt asks for the changed line count from git diff --shortstat', async () => {
  const { prompts } = await run({}, reviewers())
  assert.match(prompts.scope, /--shortstat/)
  assert.match(prompts.scope, /changedLines/)
})

test('on the light path, a reviewer that returns nothing fails every active axis', async () => {
  const { result } = await run({ issue: 7 }, reviewers({ scope: SMALL, light: null }))
  assert.equal(result.standards.status, 'failed: the reviewer did not return')
  assert.equal(result.spec.status, 'failed: the reviewer did not return')
  assert.equal(result.complete, false)
})

test('on the light path, an unfetchable issue fails the Spec axis and a missing spec skips it', async () => {
  const unfetched = { ...SMALL, spec: { found: false, source: '', number: null, text: '', problem: 'gh: not authenticated' } }
  const failed = await run({ issue: 42 }, reviewers({ scope: unfetched, light: { findings: [{ ...MINOR, axis: 'Standards' }] } }))
  assert.equal(failed.result.spec.status, 'failed: issue #42 could not be fetched: gh: not authenticated')
  assert.equal(failed.result.standards.survivors.length, 1)
  assert.doesNotMatch(failed.prompts['Light reviewer'], /Spec axis/)
  assert.equal(failed.result.complete, false)

  const missing = { ...SMALL, spec: { found: false, source: '', number: null, text: '' } }
  const skipped = await run({}, reviewers({ scope: missing, light: { findings: [{ ...MINOR, axis: 'Spec' }] } }))
  assert.equal(skipped.result.spec.status, 'skipped: no spec found')
  assert.equal(skipped.result.standards.survivors.length, 1, 'a Spec-tagged finding with no spec axis is kept under Standards')
  assert.equal(skipped.result.complete, true)
})

test('meta is a pure literal naming every phase the script uses', () => {
  const literal = source.match(/export const meta = (\{[\s\S]*?\n\})/)[1]
  const meta = Function(`return ${literal}`)()
  assert.equal(meta.name, 'review-changes')
  assert.deepEqual(meta.phases.map(phase => phase.title), ['Scope', 'Standards', 'Spec'])
})
