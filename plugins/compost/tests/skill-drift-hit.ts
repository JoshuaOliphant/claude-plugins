// ABOUTME: The hit skill-drift.test.ts asserts the mod writes for its first test; test_skill_drift.py feeds it to read_log.
// ABOUTME: Everything after `export default` must stay plain JSON, because the Python suite parses it.
export default {
  "skill": "compost:verify",
  "kind": "deviated",
  "p": 0.92,
  "at": 1000,
  "session": "session-9",
  "turn": "turn-1",
  "skill_hash": "fb810df9",
  "prompt": "run the verify gates",
  "evidence": "USER: run the verify gates\nAGENT: Running the gates.\nTOOL Bash {\"command\":\"uv run pytest\"} -> ERROR no such command\nAGENT: Gates pass."
}
