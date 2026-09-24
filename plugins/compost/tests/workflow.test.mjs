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
  spec: { found: true, source: '#7', text: 'AC-1: Given a list, When exported, Then a CSV downloads' },
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

function reviewers({ standards = { findings: [BLOCKER, MINOR] }, spec = { findings: [] }, skeptic = { refuted: false, reason: 'confirmed' }, scope = SCOPE } = {}) {
  return label => {
    if (label === 'scope') return scope
    if (label === 'Standards reviewer') return typeof standards === 'function' ? standards() : standards
    if (label === 'Spec reviewer') return spec
    return typeof skeptic === 'function' ? skeptic(label) : skeptic
  }
}

test('a confirmed blocker survives and a minor finding is kept unverified without a skeptic', async () => {
  const { result, prompts } = await run({ issue: 7 }, reviewers())
  assert.equal(result.complete, true)
  assert.deepEqual(result.standards.survivors.map(f => f.severity), ['blocker', 'minor'])
  assert.equal(result.standards.survivors[1].unverified, true)
  assert.deepEqual(Object.keys(prompts).filter(label => label.includes('skeptic')), ['Standards skeptic 1.1'])
  assert.match(result.summary, /Standards: reviewed: 2 findings raised, 1 minor left unverified, 2 survived, 0 refuted, 0 unjudged; worst blocker/)
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
  const scope = { ...SCOPE, spec: { found: false, source: '', text: '', problem: 'gh: not authenticated' } }
  const { result, prompts } = await run({ issue: 42 }, reviewers({ scope }))
  assert.equal(result.spec.status, 'failed: issue #42 could not be fetched: gh: not authenticated')
  assert.equal(result.complete, false)
  assert.equal(prompts['Spec reviewer'], undefined)
})

test('without an issue, a missing spec skips the Spec axis and the review can still complete', async () => {
  const scope = { ...SCOPE, spec: { found: false, source: '', text: '' } }
  const { result } = await run({}, reviewers({ scope }))
  assert.equal(result.spec.status, 'skipped: no spec found')
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

test('meta is a pure literal naming every phase the script uses', () => {
  const literal = source.match(/export const meta = (\{[\s\S]*?\n\})/)[1]
  const meta = Function(`return ${literal}`)()
  assert.equal(meta.name, 'review-changes')
  assert.deepEqual(meta.phases.map(phase => phase.title), ['Scope', 'Standards', 'Spec'])
})
