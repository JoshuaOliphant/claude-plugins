// ABOUTME: The Jev questions and thresholds the skill-drift mod asks; tests/test_evals_skill_drift.py replays them live.
// ABOUTME: Everything after `export default` must stay plain JSON, because the Python eval parses it.
export default {
  "thresholds": { "deviated": 0.7, "missing_guidance": 0.6, "corrected": 0.55 },
  "turn": {
    "deviated": "The agent loaded the skill in `skill.text` during the turn in `turn`. Did the agent skip, reorder, or contradict a step or rule that the skill states, in a way that matters for this turn?",
    "missing_guidance": "During `turn`, did the agent have to work out, guess, or look up something that the skill in `skill.text` is about and should have told it, but does not?"
  },
  "next_message": {
    "corrected": "The user's message in `next_user_message` follows the agent's turn in `turn`, where the agent used the skill in `skill.text`. Is the user correcting or pushing back on how the agent handled something that skill covers?"
  }
}
