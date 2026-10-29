# Check: the subagent brief

Give each subagent this brief, its docs' paths, and their entries from the `doc_refs.py` scan. When you check the docs yourself, follow the same brief.

````markdown
Check these docs against the code in this repo. The code is the likely source of truth.

Docs: <paths>
Scan leads (paths named that don't exist, and files changed since the doc last did): <entries>

For each doc, split it into claims: one statement of fact, instruction, or intent per claim. A
heading or a sentence of framing is not a claim. Sort each claim into exactly one kind:

- drifted: the code says otherwise. Cite the file:line that contradicts it.
- restated: true, and the code already says it (a signature, a config file, a test, a CLI's
  --help). Cite where.
- keeper: true or still intended, and nothing in the code says it: why something is this way, an
  alternative that was rejected, a domain term, an operational step, a constraint from outside the
  repo (a vendor limit, a regulation, an SLA). Name the file:line it is about, if any.
- plan: future work, a design never built, or a plan already carried out. Say which.

For a drifted claim that reads as a requirement ("must", "never", "always"), look for backing: a
test asserting the doc's version, an issue, an ADR. If you find one, mark it backed and cite it.

Read the code, not other docs, to settle a claim. Follow scan leads first, but don't stop at them:
a doc that names no paths can still describe behaviour the code dropped. When you can't settle a
claim from the code in a few minutes, mark it unsettled and say what you checked.

Return, per doc:

doc: <path>
claims:
  - text: <the claim, quoted or closely paraphrased>
    kind: drifted | restated | keeper | plan | unsettled
    evidence: <file:line, or what you checked>
    backed: <file:line or issue, for a drifted requirement with backing; else omit>
verdict: delete | shrink | fix | keep
````

`delete` when nothing but drifted, restated, and finished-plan claims remain; `shrink` when keepers
remain in a doc that is otherwise redundant; `fix` for a core doc with drifted claims; `keep` when
every claim is a keeper and the doc reads well as it stands, which is rare outside the core docs.
