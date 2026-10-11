# Coding Style

Write direct Python: small domain modules, ordinary functions and classes, descriptive intermediate values, and concise rST docstrings. Read the guide relevant to the change.

| When working on | Guide |
| --- | --- |
| Formatting, naming, annotations, comments or docstrings | [Python conventions](python.md) |
| Module boundaries, functions, classes or state ownership | [Code structure](structure.md) |
| Configuration, external calls, files or failure handling | [External boundaries](boundaries.md) |

## Project contracts

Use the [design overview](../design/README.md) for scope, [Workflow](../design/workflow.md) for commands and stage contracts, [Execution](../design/execution.md) for runtime and persistence requirements, [Valuation](../design/valuation.md) for financial responsibilities. Keep those requirements in their existing home.

## Maintaining the directory

1. Question whether a proposed rule addresses a recurring, project-specific decision.
2. Delete obsolete guidance and duplication; link to the authoritative section.
3. Simplify within an existing guide. Add a file only for a distinct task that needs independent reference; keep the directory flat while it remains small.
4. Accelerate lookup with descriptive names and a task-based entry in the table above.
5. Automate stable mechanical checks after the structure settles. Run `pwsh -NoProfile -File scripts/check-design.ps1` from the project root to check document structure and local links. Editorial judgment remains a review task.
