# Canon

Short essays on the ideas compost's skills lean on. Skills link the ones they use, so each loads
only when relevant.

## Classic ideas

- [Tracer bullets](tracer-bullets.md): build one thin, real path through every layer first, then widen it.
- [Good-enough software](good-enough-software.md): agree the quality bar up front, meet it fully, and stop there.
- [Ubiquitous language](ubiquitous-language.md): one domain vocabulary in talk and code, scoped by bounded contexts, recorded in `CONTEXT.md` and `CONTEXT-MAP.md`.
- [Deep modules](deep-modules.md): much behavior behind a small interface; hide decisions likely to change; design the interface twice.
- [Seams](seams.md): places to change behavior without editing there, where tests get in and where you see them fail.
- [Expand, migrate, contract](expand-contract.md): change a depended-on interface in green steps, and always finish the contract step.

## Working principles

- [Prove it works](prove-it-works.md): observe the real artifact working; proxies and self-reports are not checks.
- [Fix root causes](fix-root-causes.md): reproduce, trace to the cause, fix it there, and find its siblings.
- [Boundary discipline](boundary-discipline.md): parse and validate at the edges, trust types inside, keep logic pure.
- [Type-system discipline](type-system-discipline.md): make illegal states unrepresentable and let the checker enforce every case.
- [Model the domain](model-the-domain.md): give domain rules a structure that fits instead of scattered conditionals.
- [Subtract before you add](subtract-before-you-add.md): remove first, replace instead of deprecating, build for observed usage.
- [Sequence verifiable units](sequence-verifiable-units.md): small units, each checked green before the next, delivered in an order that proves the work.
