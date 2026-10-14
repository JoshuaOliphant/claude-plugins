// ABOUTME: compost's one hooks module (the engine loads one per plugin, with one session.start): registers each mod's commands and tools, then its hooks.
// ABOUTME: skill-drift judges skill-using turns; architecture-review draws compost:deepen's candidates in a pane.
import type { Register } from 'claude-code'

import {
  ARCHITECTURE_REVIEW_COMMAND,
  ARCHITECTURE_REVIEW_TOOL,
  register as registerArchitectureReview,
} from './architecture-review.tsx'
import { DRIFT_COMMAND, register as registerSkillDrift } from './skill-drift.ts'

export const register: Register = (on, options) => {
  on('session.start', async ($, e, next) => {
    await Promise.all([
      $.command.register(DRIFT_COMMAND),
      $.command.register(ARCHITECTURE_REVIEW_COMMAND),
      $.tool.register(ARCHITECTURE_REVIEW_TOOL),
    ])
    return next(e)
  })
  registerSkillDrift(on, options)
  registerArchitectureReview(on, options)
}
