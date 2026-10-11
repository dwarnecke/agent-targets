# External Boundaries

Keep external effects explicit and localized, with named save/load operations. Follow the [execution and storage requirements](../design/execution.md).

## Files and configuration

Use `pathlib.Path` internally and convert CLI strings at the boundary. Resolve paths from configuration and the run context rather than a developer's machine or the current working directory. Constrain artifact paths to runner-owned locations after normalization.

Use explicit UTF-8 at text boundaries and preserve exact report bytes when saving.

Keep versioned prompts in their designated files. Pass settings explicitly instead of relying on scattered fallback values. Omit credentials from saved output and diagnostics.

Use UTC-aware timestamps for run records while retaining source-specific dates and time zones. Supply historical dates through explicit inputs.

## Processes and data

Construct subprocess argument lists with `shell=False`. Keep invocation details in the adapter. Never interpolate external values into shell commands or execute source/report code as application logic. Follow the [adapter contract](../design/execution.md#codex-adapter) for output capture and acceptance.

Keep source research and financial calculations with the agents, following [Valuation](../design/valuation.md). The runner saves agent responses as written; it must not retrieve replacement research, judge or repair financial values, or reject a response for its content.

## Failures and diagnostics

Catch specific failures where code can retry, add context or classify them. Preserve the original exception with `raise ... from error` when translating it. Broad catches belong at outer boundaries that record failures and clean up; they must not disguise failure as success or replace a missing report with empty content.

Keep human progress reporting in command/orchestration code and adapter diagnostics in captured logs. Include run, stage and attempt identifiers when relevant. Avoid global suppression of provider errors and unnecessary logging of sensitive bodies. Reusable helpers return results or raise errors; command handlers map outcomes to the [specified exit codes](../design/workflow.md#commands).

Use the relevant offline fixtures in `tests/` when changing these boundaries. Keep live agent capability checks separate from default tests.
