# learn-harness (v0.1.0)

Turn a Claude project (or any folder) into a learning harness for one subject. The method is
adapted from [learnharness](https://github.com/amosblomqvist/learnharness), an agent harness
for learning: find where your understanding ends, plan the minimal path to the goal, and teach
one reasoning step at a time until the goal feels obviously true, not merely familiar.

Learnharness is a desktop app with its own UI. This plugin keeps its theory and runs it in
plain conversation: free-recall questions answered as `answer / confidence % / thinking`, a
mermaid plan map, and records kept as markdown and JSONL.

## Skills

- **learn-setup**: bootstraps a subject. Creates the learn root (doctrine copy, `graph/`,
  `sessions/`, `ledger.jsonl`), writes the profile, curriculum, frontier and feedback records,
  and drafts the project instructions header. One project per subject.
- **learn-session**: runs one session under the doctrine.
  - **Lesson** (`learn <goal>`): retrieval opener, binary-search probe per strand, a minimal
    plan map you approve, then predict, teach, check, one step per turn.
  - **Practice** (`practice [topic]`): interleaved retrieval problems from the graph, a
    six-rung hint ladder, plain verdicts, retests of every miss.
  - **Field** (`field <scenario>`): a role-played stakeholder, an artifact you produce (spec,
    rubric, eval, interview notes), graded against a rubric committed before you start. Added
    for judgment-heavy subjects, where comprehension is necessary but not sufficient.

Every session closes out: session log, propositions merged into the graph, ledger appended,
frontier rewritten.

## Where it runs best

In a Claude project, the coordinator opens one thread per session, project memory holds the
four learner records, and `/mnt/project-files/learn/` holds the graph and ledger. In Claude
Code, the learn root is `learn/` in the current folder and the records are files beside it.

## Relationship to understand

`understand:explain-back` grades one explanation of one source. learn-harness runs a subject
over many sessions, with a probe, a plan, practice, and a persistent graph and ledger.
