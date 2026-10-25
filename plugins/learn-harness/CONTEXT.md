# learn-harness glossary

| Term | Meaning |
|---|---|
| learn root | The folder holding the doctrine copy, `graph/`, `sessions/` and `ledger.jsonl`. `/mnt/project-files/learn/` in a Claude project, `learn/` elsewhere. |
| doctrine | `HARNESS.md`: the subject-neutral method every session follows. |
| subject layer | What one subject adds: the instructions header and the curriculum record. Never part of the doctrine. |
| Lesson | A session that moves the learner from current to goal understanding: retrieval opener, probe, plan, predict / teach / check. |
| Practice | A session that makes held propositions come to mind unprompted: interleaved problems, hint ladder, retests. |
| Field | A session where the learner produces an artifact for a role-played stakeholder and is graded against a rubric committed before they start. |
| strand | One dependency of a goal, bracketed by the probe. |
| floor / ceiling | The hardest thing on a strand the learner reliably gets right / the easiest thing they get wrong or don't know. |
| minimal tree | The smallest set of propositions leading from what is held to the goal. |
| proposition | A graph node: one true statement, with `follows` and `supports` edges. Never a judgment about the learner. |
| ledger | `ledger.jsonl`: append-only observations about the learner, one per graded question or proposition moved. |
| level | The closed scale on a ledger line: solid, shaky, accepted, resisted, not-yet-engaged. |
| frontier | The record of edges per strand, open misconceptions, retest queue and suggested next session, rewritten at every close. |
| retest queue | Items missed, hint-heavy or wrong-and-confident, each with a due date, asked again in a fresh surface. |
| close-out | The end-of-session step that writes the session log, graph, ledger and frontier. |
