// ABOUTME: Watches each skill the model loads and asks TypeSafe Jev whether the turn deviated from it, lacked its guidance, or drew a correction.
// ABOUTME: Hits go quietly to ~/.claude/skill-drift/<date>-<session>.jsonl for compost:skill-drift to review; /drift lists them.
import type { EngineInterface, Register, SessionMessage } from 'claude-code'

import judgments from './skill-drift-judgments.ts'

const ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
const TYPED_BY_A_PERSON = new Set(['composer', 'bridge'])
const SKILL_CHARS = 8000
const TURN_CHARS = 12000
const EVIDENCE_CHARS = 4000
const { thresholds: THRESHOLDS, turn: TURN_QUESTIONS, next_message: NEXT_MESSAGE_QUESTIONS } = judgments

export type DriftKind = keyof typeof TURN_QUESTIONS | 'corrected'
export type Hit = {
  skill: string
  kind: DriftKind
  p: number
  at: number
  session: string
  turn: string
  skill_hash: string
  prompt: string
  evidence: string
}
type Watched = { skill: string; text: string; trace: string; prompt: string; turn: string }

async function apiKey($: EngineInterface): Promise<string | undefined> {
  const fromEnv = await $.env.get('TYPESAFE_API_KEY')
  if (fromEnv) return fromEnv
  const keychain = await $.process.run(['security', 'find-generic-password', '-s', 'typesafe', '-w'])
  return keychain.exitCode === 0 ? keychain.stdout.trim() || undefined : undefined
}

async function nouls($: EngineInterface, key: string, state: unknown, questions: Record<string, string>) {
  const response = await $.http.fetch(ENDPOINT, {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'jev-latest',
      state,
      questions: Object.fromEntries(Object.entries(questions).map(([id, text]) => [id, { type: 'noul', instructions: text }])),
    }),
  })
  if (!response.ok) throw new Error(`TypeSafe ${response.status}: ${response.text.slice(0, 200)}`)
  const answers = JSON.parse(response.text).answers as Record<string, { noul: number }>
  return Object.fromEntries(Object.entries(answers).map(([id, answer]) => [id, answer.noul]))
}

export function skillHash(text: string): string {
  let hash = 0x811c9dc5
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i)
    hash = Math.imul(hash, 0x01000193) >>> 0
  }
  return hash.toString(16).padStart(8, '0')
}

function isTypedPrompt(message: SessionMessage): boolean {
  return message.role === 'user' && message.text.trim() !== '' && !message.toolResults?.length
}

export function turnTrace(messages: SessionMessage[]): { prompt: string; trace: string } {
  let start = messages.length - 1
  while (start > 0 && !isTypedPrompt(messages[start])) start -= 1
  const lines: string[] = []
  for (const message of messages.slice(start)) {
    if (message.role === 'user' && isTypedPrompt(message)) lines.push(`USER: ${message.text}`)
    if (message.role === 'assistant') {
      if (message.text.trim()) lines.push(`AGENT: ${message.text}`)
      for (const use of message.toolUses) {
        const outcome = use.isError ? `ERROR ${use.text ?? ''}` : (use.text ?? '')
        lines.push(`TOOL ${use.tool} ${JSON.stringify(use.input).slice(0, 300)} -> ${outcome.slice(0, 400)}`)
      }
    }
  }
  const [opening = '', ...rest] = lines
  const body = rest.join('\n')
  const trace = body.length > TURN_CHARS ? `${opening}\n…\n${body.slice(-TURN_CHARS)}` : [opening, body].join('\n')
  return { prompt: messages[start]?.text ?? '', trace }
}

function evidence(trace: string): string {
  return trace.length > EVIDENCE_CHARS ? `${trace.slice(0, EVIDENCE_CHARS / 2)}\n…\n${trace.slice(-EVIDENCE_CHARS / 2)}` : trace
}

async function logDir($: EngineInterface): Promise<string> {
  return `${await $.env.get('HOME')}/.claude/skill-drift`
}

async function record($: EngineInterface, found: Hit[]) {
  if (found.length === 0) return
  const day = new Date(found[0].at).toISOString().slice(0, 10)
  const path = `${await logDir($)}/${day}-${found[0].session}.jsonl`
  const before = (await $.fs.exists(path)) ? String(await $.fs.read(path)) : ''
  await $.fs.write(path, before + found.map(hit => JSON.stringify(hit) + '\n').join(''))
}

export function summarize(log: Hit[]): string {
  if (log.length === 0) return 'skill-drift: no drift recorded yet'
  const bySkill = new Map<string, Hit[]>()
  for (const hit of log) bySkill.set(hit.skill, [...(bySkill.get(hit.skill) ?? []), hit])
  const ranked = [...bySkill.entries()].sort((a, b) => b[1].length - a[1].length)
  const lines: string[] = []
  for (const [skill, hits] of ranked) {
    const kinds = new Map<string, Set<string>>()
    for (const hit of hits) kinds.set(hit.kind, (kinds.get(hit.kind) ?? new Set()).add(hit.session))
    lines.push(`${skill}  ${[...kinds.entries()].map(([kind, sessions]) => `${kind}×${sessions.size} sessions`).join('  ')}`)
    const latest = hits.reduce((a, b) => (b.at > a.at ? b : a))
    lines.push(`  latest: ${latest.kind} p=${latest.p.toFixed(2)} on "${latest.prompt.slice(0, 90)}"`)
  }
  return lines.join('\n')
}

async function readLog($: EngineInterface): Promise<Hit[]> {
  const dir = await logDir($)
  if (!(await $.fs.exists(dir))) return []
  const files = (await $.fs.list(dir)).filter(entry => entry.kind === 'file' && entry.name.endsWith('.jsonl'))
  const texts = await Promise.all(files.map(entry => $.fs.read(`${dir}/${entry.name}`)))
  return texts.flatMap(text => String(text).split('\n').filter(Boolean).map(line => JSON.parse(line) as Hit))
}

export const register: Register = on => {
  const loaded = new Map<string, string>()
  let pending: Watched[] = []

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'drift', description: 'List skill drift the mod has recorded, by skill' })
    return next(e)
  })

  on('skill.prompt', async ($, e, next) => {
    const result = await next(e)
    loaded.set(e.skill, result.text.slice(0, SKILL_CHARS))
    return result
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId || e.isAborted || loaded.size === 0) return result
    const key = await apiKey($)
    if (!key) return result

    const { prompt, trace } = turnTrace(await $.session.messages())
    const watched = [...loaded.entries()].map(([skill, text]) => ({ skill, text, trace, prompt, turn: e.turnId }))
    loaded.clear()
    pending = watched

    const answered = await Promise.all(
      watched.map(w => nouls($, key, { skill: { name: w.skill, text: w.text }, turn: w.trace }, TURN_QUESTIONS)),
    )
    const [session, at] = await Promise.all([$.session.id(), $.clock.now()])
    await record(
      $,
      watched.flatMap((w, i) =>
        Object.entries(answered[i])
          .filter(([kind, p]) => p >= THRESHOLDS[kind as keyof typeof THRESHOLDS])
          .map(([kind, p]) => hitOf(w, kind as DriftKind, p, session, at, w.prompt)),
      ),
    )
    return result
  })

  on('prompt.submit', async ($, e, next) => {
    if (!TYPED_BY_A_PERSON.has(e.origin?.kind)) return next(e)
    const watched = pending
    pending = []
    const result = await next(e)
    if (watched.length === 0 || e.text.trim().startsWith('/')) return result
    const key = await apiKey($)
    if (!key) return result

    const answered = await Promise.all(
      watched.map(w =>
        nouls($, key, { skill: { name: w.skill, text: w.text }, turn: w.trace, next_user_message: e.text }, NEXT_MESSAGE_QUESTIONS),
      ),
    )
    const [session, at] = await Promise.all([$.session.id(), $.clock.now()])
    await record(
      $,
      watched
        .map((w, i) => hitOf(w, 'corrected', answered[i].corrected, session, at, e.text))
        .filter(hit => hit.p >= THRESHOLDS.corrected),
    )
    return result
  })

  on('command.run', { name: 'drift' }, async $ => ({ text: summarize(await readLog($)) }))
}

function hitOf(w: Watched, kind: DriftKind, p: number, session: string, at: number, prompt: string): Hit {
  return { skill: w.skill, kind, p, at, session, turn: w.turn, skill_hash: skillHash(w.text), prompt, evidence: evidence(w.trace) }
}
