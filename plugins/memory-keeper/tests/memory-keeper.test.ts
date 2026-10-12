// ABOUTME: Tests for memory-keeper: the Haiku gate, the fork's proposals written to an in-memory
// ABOUTME: memory folder, Undo from the pane, and the parsing and index edits in memory.ts.
import { describe, expect, mock, test } from 'claude-code/testing'
import type { On, SessionMessage } from 'claude-code'

import { lastTurn, parseProposals, withIndexLine } from '../hooks/memory'

const DIR = '/home/me/.claude/projects/-work/memory'
const TRANSCRIPT = '/home/me/.claude/projects/-work/session.jsonl'
const PANE = {
  plugin: 'memory-keeper',
  component: 'Pane',
  requestId: 'memory-changes',
  props: { title: 'Memory changes', isFocused: false, bodyColumns: 60, placement: 'dock' } as never,
} as const

const OLD_FACT = [
  '---',
  'name: old-fact',
  'description: A fact that no longer holds',
  'metadata:',
  '  type: project',
  '---',
  '',
  'The build uses make.',
  '',
].join('\n')

const TURN: SessionMessage[] = [
  { role: 'user', text: 'Stop using make, we moved to just. And always use uv.', toolUses: [] },
  { role: 'assistant', text: 'Noted.', toolUses: [] },
]

const FORK_REPLY = JSON.stringify({
  changes: [
    {
      action: 'add',
      file: 'uses-uv.md',
      name: 'uses-uv',
      description: 'Python work always goes through uv',
      type: 'feedback',
      title: 'Always uv',
      body: 'Use uv for Python.\n**Why:** the user said so.\n**How to apply:** uv run, uv add.',
      reason: 'the user said always use uv',
    },
    { action: 'remove', file: 'old-fact.md', reason: 'the build moved to just' },
  ],
})

type World = {
  files: Map<string, string>
  gateAnswer: string
  forkReply: string
  forkCalls: number
  logs: string[]
}

function world(on: On, gateAnswer: string): World {
  const w: World = {
    files: new Map([
      [`${DIR}/MEMORY.md`, '- [Old fact](old-fact.md) — A fact that no longer holds\n'],
      [`${DIR}/old-fact.md`, OLD_FACT],
    ]),
    gateAnswer,
    forkReply: FORK_REPLY,
    forkCalls: 0,
    logs: [],
  }
  const usage = { input_tokens: 1, output_tokens: 1, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 }

  on('classic.Stop', () => ({}))
  on('session.messages', () => ({ value: TURN }))
  on('fs.exists', ($, e) => ({ value: e.path === DIR || w.files.has(e.path) }))
  on('fs.list', () => ({
    value: [...w.files.keys()].map(path => ({
      name: path.slice(DIR.length + 1),
      kind: 'file' as const,
      size: 1,
      mtimeMs: 0,
      isLink: false,
    })),
  }))
  on('fs.read', ($, e) => ({ value: w.files.get(e.path) ?? '' }))
  on('fs.write', ($, e) => {
    w.files.set(e.path, e.text)
    return { value: undefined }
  })
  on('process.run', ($, e) => {
    w.files.delete(String(e.argv.at(-1)))
    return { value: { exitCode: 0, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('model.complete', () => ({ value: { isAnswered: true, text: w.gateAnswer, usage } }))
  on('model.fork', () => {
    w.forkCalls += 1
    return { value: { isAnswered: true, text: w.forkReply, usage } }
  })
  on('ui.log', ($, e) => {
    w.logs.push(e.text)
    return { value: undefined }
  })
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))

  return w
}

describe('after a main-thread turn', () => {
  test('a "no" from the Haiku gate leaves memory alone and forks nothing', async ($, on) => {
    const clock = mock.clock(on)
    const w = world(on, 'no')

    await $.classic.Stop({ stop_hook_active: false, transcript_path: TRANSCRIPT })
    await clock.settle()

    expect(w.forkCalls).toBe(0)
    expect(w.files.get(`${DIR}/old-fact.md`)).toBe(OLD_FACT)
    const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
    expect(await ui.find({ text: 'No memory changes yet.' })).toBeDefined()
    await ui.unmount()
  })

  test('a "yes" forks the session and writes what the fork proposes', async ($, on) => {
    const clock = mock.clock(on)
    const w = world(on, 'Yes.')

    await $.classic.Stop({ stop_hook_active: false, transcript_path: TRANSCRIPT })
    await clock.settle()

    expect(w.forkCalls).toBe(1)
    expect(w.files.get(`${DIR}/uses-uv.md`)).toContain('type: feedback')
    expect(w.files.has(`${DIR}/old-fact.md`)).toBe(false)
    expect(w.files.get(`${DIR}/MEMORY.md`)).toBe(
      '- [Always uv](uses-uv.md) — Python work always goes through uv\n',
    )
  })

  test('a subagent stopping starts no review', async ($, on) => {
    const clock = mock.clock(on)
    const w = world(on, 'yes')

    await $.classic.Stop({ stop_hook_active: false, transcript_path: TRANSCRIPT, agent_id: 'a1' })
    await clock.settle()

    expect(w.forkCalls).toBe(0)
  })

  test('a fork proposal with a bad file name is skipped and said', async ($, on) => {
    const clock = mock.clock(on)
    const w = world(on, 'yes')
    w.forkReply = JSON.stringify({ changes: [{ action: 'remove', file: '../../etc/passwd', reason: 'x' }] })

    await $.classic.Stop({ stop_hook_active: false, transcript_path: TRANSCRIPT })
    await clock.settle()

    expect(w.logs).toEqual(['memory-keeper: skipped a proposal: "../../etc/passwd" is not a memory file name'])
    expect(w.files.has(`${DIR}/old-fact.md`)).toBe(true)
  })
})

describe('the pane', () => {
  test('lists each change and Undo puts the folder back', async ($, on) => {
    const clock = mock.clock(on)
    const w = world(on, 'yes')
    const before = new Map(w.files)

    await $.classic.Stop({ stop_hook_active: false, transcript_path: TRANSCRIPT })
    await clock.settle()

    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ ...PANE, surface })
      expect(await ui.find({ text: /\+ uses-uv/ })).toBeDefined()
      expect(await ui.find({ text: /- old-fact/ })).toBeDefined()
      await ui.unmount()
    }

    const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
    const undos = await ui.findAll({ type: 'Button' })
    expect(undos).toHaveLength(2)
    for (const undo of undos) await ui.press({ key: String(undo.key) })

    expect(w.files).toEqual(before)
    expect(await ui.findAll({ type: 'Button' })).toHaveLength(0)
    await ui.unmount()
  })
})

describe('memory.ts', () => {
  test('lastTurn starts at the latest prompt, not at a tool result', () => {
    const messages: SessionMessage[] = [
      { role: 'user', text: 'first', toolUses: [] },
      { role: 'user', text: 'second', toolUses: [] },
      { role: 'assistant', text: '', toolUses: [{ tool_use_id: 't', tool: 'Bash', input: { command: 'ls' } }] },
      { role: 'user', text: '', toolUses: [], toolResults: [{ tool_use_id: 't', text: 'x' } as never] },
    ]

    expect(lastTurn(messages)).toBe('User: second\n[Bash] {"command":"ls"}')
    expect(lastTurn([])).toBe('')
  })

  test('parseProposals says why it drops what it cannot use', () => {
    expect(parseProposals('no json here').rejected).toEqual(['the reply held no JSON object'])
    expect(parseProposals('{"changes": 3}').rejected).toEqual(['the reply had no "changes" list'])
    expect(parseProposals('{bad}').rejected[0]).toMatch(/did not parse/)

    const { proposals, rejected } = parseProposals(
      JSON.stringify({
        changes: [
          { action: 'rename', file: 'a.md' },
          { action: 'add', file: 'a.md', type: 'mood', description: 'd', body: 'b' },
          { action: 'add', file: 'a.md', type: 'user', description: '', body: 'b' },
          { action: 'update', file: 'a.md', type: 'user', description: 'd\n e', body: ' b ' },
        ],
      }),
    )
    expect(rejected).toEqual([
      'a.md: unknown action "rename"',
      'a.md: unknown memory type "mood"',
      'a.md: a description and a body are required',
    ])
    expect(proposals).toEqual([
      { action: 'write', file: 'a.md', name: 'a', description: 'd e', type: 'user', title: 'a', body: 'b', reason: '' },
    ])
  })

  test('withIndexLine adds, replaces and drops one line', () => {
    const one = withIndexLine('', 'a.md', '- [A](a.md) — a')
    expect(one).toBe('- [A](a.md) — a\n')
    expect(withIndexLine(one, 'a.md', '- [A](a.md) — b')).toBe('- [A](a.md) — b\n')
    expect(withIndexLine(one, 'a.md', null)).toBe('')
    expect(withIndexLine(one, 'z.md', null)).toBe(one)
  })
})
