// ABOUTME: Engine tests for skill-drift: which turns are judged, the hits written to the session's log file, and /drift.
// ABOUTME: Jev's HTTP answers and skill_drift.py's run are stubbed at the engine boundary; the Python suite reads the hit back.
import { expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'

import writtenHit from './skill-drift-hit.ts'

type Asked = { state: Record<string, unknown>; questions: Record<string, unknown> }
type Ran = { exitCode: number; stdout: string; stderr: string } | 'refused'
type World = { asked: Asked[]; files: Map<string, string>; toasts: string[]; order: string[]; ran: string[][]; drift: Ran }

// compost's folder, the root the engine loads the mod from (this file sits in its tests/).
const PLUGIN_ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '')
const LOG ='/home/me/.claude/skill-drift/1970-01-01-session-9.jsonl'

const TURN = [
  { role: 'user', text: 'run the verify gates', toolUses: [] },
  {
    role: 'assistant',
    text: 'Running the gates.',
    toolUses: [{ tool_use_id: 't1', tool: 'Bash', input: { command: 'uv run pytest' }, text: 'no such command', isError: true }],
  },
  { role: 'user', text: '', toolUses: [], toolResults: [{ tool_use_id: 't1', text: 'no such command', isError: true }] },
  { role: 'assistant', text: 'Gates pass.', toolUses: [] },
]

function engine(
  on: On,
  answers: Record<string, number> | 'outage',
  messages: unknown[] = TURN,
  key: string | null = 'test-key',
): World {
  const world: World = { asked: [], files: new Map(), toasts: [], order: [], ran: [], drift: { exitCode: 0, stdout: '', stderr: '' } }
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('command.register', () => ({ value: { command: 'drift' } }) as never)
  on('skill.prompt', (_$, e) => ({ text: e.text }))
  on('turn.complete', (_$, e) => ({ text: e.answer }) as never)
  on('prompt.submit', (_$, e) => {
    world.order.push('prompt entered')
    return { text: e.text, context: e.context } as never
  })
  on('session.messages', () => ({ value: messages }) as never)
  on('session.id', () => ({ value: 'session-9' }) as never)
  on('env.get', (_$, e) => ({ value: (e as { name: string }).name === 'HOME' ? '/home/me' : (key ?? undefined) }) as never)
  on('process.run', (_$, e) => {
    const { argv } = e as { argv: string[] }
    if (argv[0] !== 'uv') return { value: { exitCode: 44, stdout: '', stderr: 'not found' } } as never
    world.ran.push(argv)
    return (world.drift === 'refused' ? { deny: 'uv is not installed' } : { value: world.drift }) as never
  })
  on('clock.now', () => ({ value: 1000 }) as never)
  on('ui.toast', (_$, e) => {
    world.toasts.push(String((e as { text: string }).text))
    return { value: undefined } as never
  })
  on('fs.exists', (_$, e) => {
    const path = (e as { path: string }).path
    return { value: world.files.has(path) || [...world.files.keys()].some(file => file.startsWith(`${path}/`)) } as never
  })
  on('fs.read', (_$, e) => ({ value: world.files.get((e as { path: string }).path) }) as never)
  on('fs.write', (_$, e) => {
    const { path, text } = e as { path: string; text: string }
    world.files.set(path, text)
    return { value: undefined } as never
  })
  on('fs.list', (_$, e) => {
    const dir = (e as { path: string }).path
    const names = [...world.files.keys()].filter(file => file.startsWith(`${dir}/`)).map(file => file.slice(dir.length + 1))
    return { value: names.map(name => ({ name, kind: 'file', size: 1, mtimeMs: 0, isLink: false })) } as never
  })
  on('http.fetch', (_$, e) => {
    const body = JSON.parse((e as { init: { body: string } }).init.body) as Asked
    world.asked.push(body)
    world.order.push('jev asked')
    if (answers === 'outage') return { value: { status: 503, ok: false, headers: {}, text: 'unavailable' } } as never
    const out = Object.fromEntries(Object.keys(body.questions).map(id => [id, { type: 'noul', noul: answers[id] ?? 0 }]))
    return { value: { status: 200, ok: true, headers: {}, text: JSON.stringify({ answers: out }) } } as never
  })
  return world
}

function logged(world: World): Record<string, unknown>[] {
  return (world.files.get(LOG) ?? '').split('\n').filter(Boolean).map(line => JSON.parse(line))
}

const TYPED = { kind: 'composer' }
const START = { cwd: '/tmp', surface: 'terminal', isInteractive: true } as const
const ENDED = { answer: 'Gates pass.', durationMs: 10, isAborted: false, turnId: 'turn-1', reason: 'answer' } as never

test('a turn that used a skill is judged against it and its drift is logged', async ($, on) => {
  const world = engine(on, { deviated: 0.92, missing_guidance: 0.5 })
  await $.session.start(START)
  await $.skill.prompt({ skill: 'compost:verify', text: 'Run `uv run pytest` for the gates.' })
  await $.turn.complete(ENDED)
  expect(world.asked.length).toBe(1)
  expect(Object.keys(world.asked[0].questions)).toEqual(['deviated', 'missing_guidance'])
  expect(JSON.stringify(world.asked[0].state)).toContain('ERROR no such command')
  expect(logged(world)).toEqual([writtenHit])
  expect(world.toasts).toEqual([])
})

test('a turn that loaded no skill is not judged', async ($, on) => {
  const world = engine(on, { deviated: 0.99 })
  await $.session.start(START)
  await $.turn.complete(ENDED)
  expect(world.asked.length).toBe(0)
})

test('a subagent turn is not judged', async ($, on) => {
  const world = engine(on, { deviated: 0.99 })
  await $.session.start(START)
  await $.skill.prompt({ skill: 'compost:verify', text: 'steps' })
  await $.turn.complete({ ...(ENDED as object), agentId: 'agent-7' } as never)
  expect(world.asked.length).toBe(0)
})

test("the user's next message is checked for a correction of the skill's work", async ($, on) => {
  const world = engine(on, { corrected: 0.88 })
  await $.session.start(START)
  await $.skill.prompt({ skill: 'compost:verify', text: 'steps' })
  await $.turn.complete(ENDED)
  await $.prompt.submit({ text: 'no, the gates never ran, pytest is not on PATH', origin: TYPED } as never)
  expect(world.order.slice(-2)).toEqual(['prompt entered', 'jev asked'])
  expect(world.asked[1].state.next_user_message).toBe('no, the gates never ran, pytest is not on PATH')
  expect(logged(world)).toMatchObject([
    { skill: 'compost:verify', kind: 'corrected', p: 0.88, turn: 'turn-1', prompt: 'no, the gates never ran, pytest is not on PATH' },
  ])
  await $.prompt.submit({ text: 'and another thing', origin: TYPED } as never)
  expect(world.asked.length).toBe(2)
})

test('hits append to the session file without a toast and carry the skill version', async ($, on) => {
  const world = engine(on, { deviated: 0.9 })
  await $.session.start(START)
  for (const [turnId, text] of [['turn-1', 'steps'], ['turn-2', 'steps'], ['turn-3', 'steps, revised']]) {
    await $.skill.prompt({ skill: 'compost:build', text })
    await $.turn.complete({ ...(ENDED as object), turnId } as never)
  }
  const hits = logged(world)
  expect(hits.map(hit => hit.turn)).toEqual(['turn-1', 'turn-2', 'turn-3'])
  expect(hits[0].skill_hash).toMatch(/^[0-9a-f]{8}$/)
  expect(hits[1].skill_hash).toBe(hits[0].skill_hash)
  expect(hits[2].skill_hash).not.toBe(hits[0].skill_hash)
  expect(world.toasts).toEqual([])
})

test("/drift prints skill_drift.py's summary of the log, so it shows the hits compost:skill-drift counts open", async ($, on) => {
  const world = engine(on, {})
  world.drift = { exitCode: 0, stdout: 'compost:build  deviated×2 sessions (pattern)\n', stderr: '' }
  await $.session.start(START)
  const shown = await $.command.run({ name: 'drift', args: '' } as never)
  expect((shown as { text: string }).text).toBe('compost:build  deviated×2 sessions (pattern)')
  expect(world.ran).toHaveLength(1)
  expect(world.ran[0]).toEqual([
    'uv',
    'run',
    '--quiet',
    `${PLUGIN_ROOT}/scripts/skill_drift.py`,
    '--claude-dir',
    '/home/me/.claude',
    'summary',
  ])
})

test('/drift reports a failed or refused run of skill_drift.py instead of throwing', async ($, on) => {
  const world = engine(on, {})
  world.drift = { exitCode: 1, stdout: '', stderr: '\nskill_drift: settings.json is not valid JSON\n' }
  await $.session.start(START)
  const failed = await $.command.run({ name: 'drift', args: '' } as never)
  expect((failed as { text: string }).text).toBe(
    'skill-drift: skill_drift.py summary failed (exit 1): skill_drift: settings.json is not valid JSON',
  )
  world.drift = {
    exitCode: 1,
    stdout: '',
    stderr: 'Traceback (most recent call last):\n  File "skill_drift.py", line 9, in <module>\nKeyError: \'p\'\n\n',
  }
  const crashed = await $.command.run({ name: 'drift', args: '' } as never)
  expect((crashed as { text: string }).text).toBe("skill-drift: skill_drift.py summary failed (exit 1): KeyError: 'p'")
  world.drift = 'refused'
  const refused = await $.command.run({ name: 'drift', args: '' } as never)
  expect((refused as { text: string }).text).toStartWith('skill-drift: could not run skill_drift.py: ')
})

test("a long turn is trimmed from the middle, so Jev still reads the user's request", async ($, on) => {
  const long = [
    { role: 'user', text: 'slice spec #12 into issues', toolUses: [] },
    ...Array.from({ length: 80 }, (_, i) => ({ role: 'assistant', text: `step ${i} ${'x'.repeat(300)}`, toolUses: [] })),
  ]
  const world = engine(on, {}, long)
  await $.session.start(START)
  await $.skill.prompt({ skill: 'compost:slice', text: 'steps' })
  await $.turn.complete(ENDED)
  const turn = (world.asked[0].state.turn as string)
  expect(turn.startsWith('USER: slice spec #12 into issues\n…\n')).toBe(true)
  expect(turn).toContain('step 79')
  expect(turn).not.toContain('step 0 ')
})

test("an agent's message neither counts as a correction nor uses up the pending check", async ($, on) => {
  const world = engine(on, { corrected: 0.9 })
  await $.session.start(START)
  await $.skill.prompt({ skill: 'compost:verify', text: 'steps' })
  await $.turn.complete(ENDED)
  await $.prompt.submit({ text: 'no, that is wrong: labels say otherwise', origin: { kind: 'peer-send-message' } } as never)
  expect(world.asked.length).toBe(1)
  await $.prompt.submit({ text: 'no, the gates never ran', origin: TYPED } as never)
  expect(world.asked.length).toBe(2)
  expect(logged(world).map(hit => hit.kind)).toEqual(['corrected'])
})

test('without a TypeSafe key nothing is asked and nothing is written', async ($, on) => {
  const world = engine(on, { deviated: 0.99, corrected: 0.99 }, TURN, null)
  await $.session.start(START)
  await $.skill.prompt({ skill: 'compost:verify', text: 'steps' })
  await $.turn.complete(ENDED)
  await $.prompt.submit({ text: 'no, that is wrong', origin: TYPED } as never)
  expect(world.asked).toEqual([])
  expect([...world.files.keys()]).toEqual([])
  expect(world.toasts).toEqual([])
})

test('a TypeSafe outage leaves the turn and the next prompt untouched and writes nothing', async ($, on) => {
  const world = engine(on, 'outage')
  await $.session.start(START)
  await $.skill.prompt({ skill: 'compost:verify', text: 'steps' })
  const ended = await $.turn.complete(ENDED)
  const entered = await $.prompt.submit({ text: 'no, that is wrong', origin: TYPED } as never)
  expect(world.asked.length).toBe(2)
  expect(ended).toMatchObject({ text: 'Gates pass.' })
  expect(entered).toMatchObject({ text: 'no, that is wrong' })
  expect([...world.files.keys()]).toEqual([])
  expect(world.toasts).toEqual([])
})
