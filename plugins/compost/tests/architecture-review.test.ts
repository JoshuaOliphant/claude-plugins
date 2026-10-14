// ABOUTME: Engine tests for the architecture-review pane: what the tool keeps and answers, the cards the pane draws, Explore, and /architecture-review.
// ABOUTME: The engine's pane placement and prompt submission are stubbed at the engine boundary.
import { expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'

type World = { opened: string[]; submitted: unknown[] }

const TOOL = 'mcp__compost__architecture_review'
const START = { cwd: '/tmp', surface: 'terminal', isInteractive: true } as const
const PANE = { plugin: 'compost', surface: 'terminal', component: 'Pane', requestId: 'architecture-review' } as const
const PANE_PROPS = { title: 'Architecture review', isFocused: false, bodyColumns: 80, placement: 'dock' }

const REVIEW = {
  candidates: [
    {
      name: 'Rate limiting',
      files: ['api/limits.py'],
      problem: 'Speculative tidy-up.',
      change: 'Fold the two limiters together.',
      gain: 'One place to change limits.',
      dependencies: ['in-process'],
      strength: 'Speculative',
    },
    {
      name: 'Billing sync',
      files: ['billing/stripe.py', 'billing/sync.py'],
      problem: 'Each caller retries Stripe on its own.',
      change: 'One Billing sync module behind a Stripe port.',
      gain: 'Retries in one place; tests use a fake adapter.',
      dependencies: ['truly-external'],
      strength: 'Worth exploring',
    },
    {
      name: 'Order intake',
      files: ['orders/intake.py', 'orders/validate.py', 'orders/persist.py'],
      problem: 'Understanding intake means bouncing between three shallow modules.',
      change: 'Merge them into one Order intake module with one entry point.',
      gain: 'Locality for intake bugs; tests at the interface.',
      dependencies: ['in-process', 'local-substitutable'],
      strength: 'Strong',
    },
  ],
  recommendation: { candidate: 'Order intake', why: 'It changed in 40 commits this quarter.' },
}

function engine(on: On, placement: 'placed' | 'narrow' = 'placed'): World {
  const world: World = { opened: [], submitted: [] }
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('command.register', (_$, e) => ({ value: { command: (e as { name: string }).name } }) as never)
  on('tool.register', (_$, e) => ({ value: { tool: `mcp__compost__${(e as { name: string }).name}` } }) as never)
  on('ui.open', (_$, e) => {
    world.opened.push((e as { id: string }).id)
    const value = placement === 'placed' ? { isPlaced: true } : { isPlaced: false, reason: 'terminal too narrow' }
    return { value } as never
  })
  on('prompt.submit', (_$, e) => {
    world.submitted.push(e)
    return { text: e.text } as never
  })
  return world
}

function callTool($: Parameters<Parameters<typeof test>[1]>[0], args: object) {
  return $.tool.call({ tool: TOOL, tool_use_id: 'toolu_1', ...args } as never) as Promise<{ result?: unknown; deny?: string }>
}

test('the tool keeps the candidates, opens the pane, and tells the model what it shows', async ($, on) => {
  const world = engine(on)
  await $.session.start(START)
  const answer = await callTool($, REVIEW)
  expect(world.opened).toEqual(['architecture-review'])
  expect(answer.result).toBe('3 deepening candidates are in the Architecture review pane, "Order intake" first.')
})

test('the pane draws the recommendation first, then the rest strongest first, each with its fields', async ($, on) => {
  engine(on)
  await $.session.start(START)
  await callTool($, REVIEW)
  const ui = await $.ui.mount({ ...PANE, props: PANE_PROPS as never })
  const cards = (await ui.findAll({ type: 'Markdown' })).map(card => card.text)
  expect(cards.map(card => card.split('\n')[0])).toEqual([
    '### Top recommendation: Order intake · Strong',
    '### Billing sync · Worth exploring',
    '### Rate limiting · Speculative',
  ])
  expect(cards[0]).toContain('*It changed in 40 commits this quarter.*')
  expect(cards[0]).toContain('**Files** `orders/intake.py`, `orders/validate.py`, `orders/persist.py`')
  expect(cards[0]).toContain('**Dependencies** in-process, local-substitutable')
  expect(cards[1]).toContain('**Change** One Billing sync module behind a Stripe port.')
  expect(cards[1]).not.toContain('commits this quarter')
})

test('every surface can draw the cards', async ($, on) => {
  engine(on)
  await $.session.start(START)
  await callTool($, REVIEW)
  for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface, props: PANE_PROPS as never })
    expect(await ui.findAll({ type: 'Button' }), surface).toHaveLength(3)
  }
})

test('Explore submits the pick as the person would type it', async ($, on) => {
  const world = engine(on)
  await $.session.start(START)
  await callTool($, REVIEW)
  const ui = await $.ui.mount({ ...PANE, props: PANE_PROPS as never })
  await ui.press({ key: 'explore-Billing sync' })
  expect(world.submitted).toMatchObject([{ text: 'Explore the deepening candidate "Billing sync".' }])
})

test('a recommendation that names no candidate is refused and nothing is shown', async ($, on) => {
  const world = engine(on)
  await $.session.start(START)
  const answer = await callTool($, { ...REVIEW, recommendation: { candidate: 'Payments', why: 'hot spot' } })
  expect(answer).toEqual({ deny: 'recommendation.candidate "Payments" names none of the candidates' })
  expect(world.opened).toEqual([])
})

test('a pane waiting for room tells the model to give the candidates in the conversation too', async ($, on) => {
  engine(on, 'narrow')
  await $.session.start(START)
  const answer = await callTool($, REVIEW)
  expect(String(answer.result)).toContain('waiting to be placed (terminal too narrow); /architecture-review opens it')
  expect(String(answer.result)).toContain('Give the candidates in the conversation as well.')
})

test('/architecture-review says when there is nothing yet, and reopens the last set otherwise', async ($, on) => {
  const world = engine(on)
  await $.session.start(START)
  const empty = await $.command.run({ name: 'architecture-review', args: '' } as never)
  expect(String((empty as { text: string }).text)).toBe('No deepening candidates yet: compost:deepen fills the pane.')
  expect(world.opened).toEqual([])
  await callTool($, REVIEW)
  const reopened = await $.command.run({ name: 'architecture-review', args: '' } as never)
  expect(String((reopened as { text: string }).text)).toBe('Architecture review pane opened.')
  expect(world.opened).toEqual(['architecture-review', 'architecture-review'])
})

test('an empty pane says compost:deepen fills it', async ($, on) => {
  engine(on)
  await $.session.start(START)
  const ui = await $.ui.mount({ ...PANE, props: PANE_PROPS as never })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('No deepening candidates yet: compost:deepen fills this pane.')
})
