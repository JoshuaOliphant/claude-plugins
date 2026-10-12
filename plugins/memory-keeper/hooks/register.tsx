// ABOUTME: memory-keeper: after each main-thread turn a Haiku gate asks whether memory should change; if so a
// ABOUTME: fork of the session proposes the changes, they are written to the memory folder and listed in a pane.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { MemoryAction, MemoryChange, MemorySnapshot } from '../types'
import {
  GATE,
  INDEX,
  forkRequest,
  frontmatterField,
  gateRequest,
  indexLineFor,
  indexLineOf,
  isYes,
  lastTurn,
  memoryDirOf,
  memoryText,
  parseProposals,
  withIndexLine,
} from './memory'
import type { MemoryFile, Proposal } from './memory'

const PANE = 'memory-changes'
const TITLE = 'Memory changes'
const HISTORY = 100

const changes = atom({ plugin: 'memory-keeper', key: 'changes' } as const, [])
const isReviewing = atom({ plugin: 'memory-keeper', key: 'isReviewing' } as const, false)

const MARK: Record<MemoryAction, string> = { add: '+', update: '~', remove: '-' }
const COLOR: Record<MemoryAction, 'success' | 'warning' | 'error'> = {
  add: 'success',
  update: 'warning',
  remove: 'error',
}
const PAST: Record<MemoryAction, string> = { add: 'added', update: 'changed', remove: 'removed' }

export const register: Register = on => {
  let queue: Promise<void> = Promise.resolve()

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'memory-changes',
      description: 'Show the memories memory-keeper added, changed or removed this session',
    })

    return next(e)
  })

  on('command.run', { command: 'memory-changes' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })

    return { text: 'Memory changes pane opened.' }
  })

  on('classic.Stop', ($, e, next) => {
    if (e.agent_id === undefined && e.transcript_path !== '') {
      const dir = memoryDirOf(e.transcript_path)
      $.clock.after(0, () => {
        queue = queue
          .then(() => review($, dir))
          .catch(error => $.ui.log(`memory-keeper: the review failed: ${String(error)}`))
      })
    }

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const list = await read($, changes)
    const isBusy = await read($, isReviewing)

    return (
      <Box flexDirection="column">
        {isBusy && <Text dimColor>A fork is reviewing the last turn…</Text>}
        {list.length === 0 && !isBusy && <Text dimColor>No memory changes yet.</Text>}
        {[...list].reverse().map(change => (
          <Box key={change.id} flexDirection="column" marginBottom={1}>
            <Text bold color={COLOR[change.action]} strikethrough={change.isUndone}>
              {MARK[change.action]} {change.name}
            </Text>
            <Text dimColor>{change.description}</Text>
            <Text dimColor italic>
              {change.isUndone ? 'undone' : change.reason}
            </Text>
            {!change.isUndone && (
              <Button key={`undo-${change.id}`} label="Undo" onPress={() => undo($, change.id)} />
            )}
          </Box>
        ))}
      </Box>
    )
  })
}

async function review($: EngineInterface, dir: string): Promise<void> {
  const turn = lastTurn(await $.session.messages())
  if (turn === '') return

  const memories = await memoryFiles($, dir)
  const gate = await $.model.complete({
    model: 'haiku',
    prompt: [{ text: GATE, cache: true }, { text: gateRequest(memories, turn) }],
    maxTokens: 8,
    timeoutMs: 30_000,
  })
  if (!gate.isAnswered) {
    $.ui.log(`memory-keeper: the Haiku gate gave no answer (${gate.reason})`, { to: 'debug' })
    return
  }
  if (!isYes(gate.text)) return

  await update($, isReviewing, () => true)
  $.ui.status('memory: fork reviewing')
  try {
    const reply = await $.model.fork({ prompt: forkRequest(memories) })
    if (!reply.isAnswered) {
      $.ui.log(`memory-keeper: the fork gave no answer (${reply.reason})`)
      return
    }

    const { proposals, rejected } = parseProposals(reply.text)
    for (const why of rejected) $.ui.log(`memory-keeper: skipped a proposal: ${why}`)

    const made: MemoryChange[] = []
    for (const proposal of proposals) {
      const change = await apply($, dir, proposal, `${await $.clock.now()}-${made.length}`)
      if (change !== null) made.push(change)
    }
    if (made.length === 0) return

    await update($, changes, list => [...list, ...made].slice(-HISTORY))
    $.ui.toast(`memory: ${made.map(c => `${PAST[c.action]} ${c.name}`).join(', ')}`)
    void $.ui.open({ id: PANE, title: TITLE })
  } finally {
    $.ui.status(undefined)
    await update($, isReviewing, () => false)
  }
}

async function memoryFiles($: EngineInterface, dir: string): Promise<MemoryFile[]> {
  if (!(await $.fs.exists(dir))) return []

  const entries = await $.fs.list(dir)
  const names = entries.filter(one => one.kind === 'file' && one.name.endsWith('.md')).map(one => one.name)

  return Promise.all(names.map(async file => ({ file, text: await $.fs.read(`${dir}/${file}`) })))
}

async function apply(
  $: EngineInterface,
  dir: string,
  proposal: Proposal,
  id: string,
): Promise<MemoryChange | null> {
  const path = `${dir}/${proposal.file}`
  const index = await readIndex($, dir)
  const before: MemorySnapshot | null = (await $.fs.exists(path))
    ? { text: await $.fs.read(path), indexLine: indexLineOf(index, proposal.file) }
    : null

  if (proposal.action === 'remove') {
    if (before === null) {
      $.ui.log(`memory-keeper: skipped removing ${proposal.file}: no such memory`)
      return null
    }
    await removeFile($, path)
    await $.fs.write(`${dir}/${INDEX}`, withIndexLine(index, proposal.file, null))

    return {
      id,
      action: 'remove',
      dir,
      file: proposal.file,
      name: frontmatterField(before.text, 'name') || proposal.file,
      description: frontmatterField(before.text, 'description'),
      reason: proposal.reason,
      before,
      after: null,
      isUndone: false,
    }
  }

  const after: MemorySnapshot = { text: memoryText(proposal), indexLine: indexLineFor(proposal) }
  if (before !== null && before.text === after.text && before.indexLine === after.indexLine) return null

  await $.fs.write(path, after.text)
  await $.fs.write(`${dir}/${INDEX}`, withIndexLine(index, proposal.file, after.indexLine))

  return {
    id,
    action: before === null ? 'add' : 'update',
    dir,
    file: proposal.file,
    name: proposal.name,
    description: proposal.description,
    reason: proposal.reason,
    before,
    after,
    isUndone: false,
  }
}

async function undo($: EngineInterface, id: string): Promise<void> {
  const change = (await read($, changes)).find(one => one.id === id)
  if (change === undefined || change.isUndone) return

  const path = `${change.dir}/${change.file}`
  const index = await readIndex($, change.dir)
  if (change.before === null) await removeFile($, path)
  else await $.fs.write(path, change.before.text)
  await $.fs.write(`${change.dir}/${INDEX}`, withIndexLine(index, change.file, change.before?.indexLine ?? null))

  await update($, changes, list => list.map(one => (one.id === id ? { ...one, isUndone: true } : one)))
}

async function readIndex($: EngineInterface, dir: string): Promise<string> {
  const path = `${dir}/${INDEX}`

  return (await $.fs.exists(path)) ? $.fs.read(path) : ''
}

async function removeFile($: EngineInterface, path: string): Promise<void> {
  const removed = await $.process.run(['rm', '--', path])
  if (removed.exitCode !== 0) throw new Error(`rm ${path} failed: ${removed.stderr.trim()}`)
}
