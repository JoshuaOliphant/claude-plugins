// ABOUTME: State contract of memory-keeper: the memory changes it made this session
// ABOUTME: and whether a review is running, as the pane reads them.
export type MemoryType = 'user' | 'feedback' | 'project' | 'reference'

export type MemoryAction = 'add' | 'update' | 'remove'

export type MemorySnapshot = { text: string; indexLine: string | null }

export type MemoryChange = {
  id: string
  action: MemoryAction
  dir: string
  file: string
  name: string
  description: string
  reason: string
  before: MemorySnapshot | null
  after: MemorySnapshot | null
  isUndone: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'memory-keeper': { changes: MemoryChange[]; isReviewing: boolean }
  }
}
