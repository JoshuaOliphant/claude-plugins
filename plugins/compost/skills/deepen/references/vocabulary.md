# Vocabulary

Use these terms exactly, in conversation, issues, commit messages, and reports. Consistent words are
the point: a reader who knows the glossary knows what each sentence claims.

| Term | Meaning | Avoid |
|---|---|---|
| **Module** | Anything with an interface and an implementation: a function, class, package, or a slice across tiers. Deliberately scale-agnostic. | unit, component, service |
| **Interface** | Everything a caller must know to use the module correctly: the type signature, and also invariants, ordering constraints, error modes, required configuration, and performance characteristics. | API, signature (both mean only the type-level surface) |
| **Implementation** | The code inside a module. Distinct from adapter: a Postgres repository is a small adapter with a large implementation; an in-memory fake is the reverse. Say "adapter" when the seam is the topic, "implementation" otherwise. | |
| **Depth** | Leverage at the interface: how much behaviour a caller or test can exercise per unit of interface it has to learn. **Deep**: a lot behind a small interface. **Shallow**: the interface is nearly as complex as the implementation. | |
| **Seam** | A place where behaviour can change without editing in that place (Feathers, *Working Effectively with Legacy Code*); the location where a module's interface lives. Where the seam goes is its own decision, separate from what goes behind it. | boundary (overloaded with DDD's bounded context) |
| **Adapter** | A concrete thing that satisfies an interface at a seam. Names a role, the slot it fills, not what is inside it. | |
| **Port** | An interface at a seam that more than one adapter satisfies. Only remote-but-owned and truly external dependencies get one. | |
| **Leverage** | What callers get from depth: more capability per unit of interface learned. One implementation pays back across every call site and test. | |
| **Locality** | What maintainers get from depth: change, bugs, knowledge, and verification concentrate in one place. Fix once, fixed everywhere. | |

## How they relate

- A module has exactly one interface, the surface it presents to callers and tests.
- Depth is a property of a module, measured against its interface.
- A seam is where a module's interface lives.
- An adapter sits at a seam and satisfies the interface.
- Depth produces leverage for callers and locality for maintainers.

## Principles

- **Depth belongs to the interface, not the implementation.** A deep module can be built from small,
  swappable parts inside; they just aren't part of its interface. A module can have internal seams,
  used by its own tests, as well as the external seam at its interface. Don't expose an internal seam
  through the interface because a test uses it.
- **The deletion test.** Imagine deleting the module. If complexity vanishes, it was a pass-through.
  If complexity reappears across its callers, it was earning its keep.
- **The interface is the test surface.** Callers and tests cross the same seam. Wanting to test past
  the interface means the module is the wrong shape.
- **One adapter is a hypothetical seam; two is a real one.** Don't introduce a seam unless something
  actually varies across it.
- **A deep module is not a deep call chain.** A chain of thin layers scatters understanding across
  files. A deep module concentrates it behind one interface.

## Designing for testability

- **Accept dependencies; don't create them.** `process_order(order, payment_gateway)` can be tested;
  a function that builds its own `StripeGateway()` inside cannot, short of patching.
- **Return results; don't produce side effects.** `calculate_discount(cart) -> Discount` is checked
  with one assertion; `apply_discount(cart)` that mutates `cart.total` needs the whole cart inspected.
- **Keep the surface small.** Fewer entry points need fewer tests; fewer parameters need less setup.

When shaping an interface, ask: can it have fewer entry points, simpler parameters, more hidden
inside?

## Rejected framings

- **Depth as the ratio of implementation lines to interface lines.** It rewards padding the
  implementation. Depth here is leverage.
- **Interface as a language's `interface` keyword or a class's public methods.** Too narrow: the
  interface includes every fact a caller must know.
- **"Boundary".** Overloaded with bounded contexts. Say seam or interface.

## Phrasings that fit

- "The Order intake module is shallow: its interface nearly matches its implementation."
- "Pricing leaks across the seam."
- "Deepen: one interface, one place to test."
- "Two adapters justify the seam: HTTP in production, in-memory in tests."

State gains in these terms ("locality: bugs concentrate in one module", "leverage: one interface,
six call sites"), not as "easier to maintain" or "cleaner".
