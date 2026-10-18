# Code Structure

Make dependencies, orchestration and state ownership explicit. Follow the package and artifact layout in [Execution](../design/execution.md#storage).

## Modules and dependencies

Group code by responsibility. Command handlers call the initiation sources and the runner; the runner coordinates agent invocation, context preparation and storage. Research agents own source retrieval and verification beyond the initiation facts. Lower-level modules do not import command handlers or reach into runner internals.

Keep related operations together until a distinct responsibility warrants another module. Put helpers beside the domain they serve, such as final-message reading with the agent adapter. Avoid an unrelated collection of helpers in `utils.py`.

Use direct calls and a simple ordered stage definition for the fixed pipeline. Add an abstraction when real callers share behavior or a boundary needs a test double. Do not prebuild empty modules, a class per stage, plugin registries or a workflow framework.

## Functions and classes

Use a function when arguments fully describe the operation. Use a class when multiple operations share meaningful state or resource ownership. Prefer composition over inheritance.

Make a public operation read as a sequence of meaningful steps. Extract a helper when its name clarifies a responsibility, it is reused, or it isolates an invariant. Avoid arbitrary line-count limits and helpers that merely rename an obvious expression. Put initialization first in a class and helpers near the operations they support.

Pass dependencies explicitly. A small protocol is useful when both a real adapter and a fake need the same interface; a service locator or injection framework is unnecessary.

## State and ownership

Constructors assign validated settings and dependencies and perform inexpensive local setup. Expose retrieval, invocation and persistence as named operations. Module imports must not access the network, start processes, write artifacts or change global logging/warning policy.

Document mutation. Copy caller-owned mutable data when taking a private snapshot, including nested values when necessary. Properties may expose inexpensive derived values or protect owned state. Do not copy large immutable byte strings unnecessarily.

Avoid mutable defaults and shared configuration dictionaries as default arguments. Resolve configuration once and pass it to consumers; see [Context and configuration](../design/execution.md#context-and-configuration).
