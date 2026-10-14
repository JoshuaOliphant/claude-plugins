// ABOUTME: Type contract for compost's mods: the deepening candidates the architecture-review pane holds in $.state.
// ABOUTME: Mirrors compost:deepen's step 5 fields: files, problem, change, gain, dependency categories, strength.
export type Strength = 'Strong' | 'Worth exploring' | 'Speculative'

export type DependencyCategory = 'in-process' | 'local-substitutable' | 'remote-but-owned' | 'truly-external'

export type Candidate = {
  name: string
  files: string[]
  problem: string
  change: string
  gain: string
  dependencies: DependencyCategory[]
  strength: Strength
}

export type ArchitectureReview = {
  candidates: Candidate[]
  recommendation: { candidate: string; why: string }
}

declare module 'claude-code' {
  interface PluginState {
    compost: { review: ArchitectureReview | null }
  }
}
