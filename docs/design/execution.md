# DCF Pipeline Execution

## Problem Statement

Unattended research calls must preserve their output and pass it forward, and a failed call must never leave a plausible partial result that looks accepted.

## Proposed Solution

A small local Python runner builds each stage's prompt, invokes the Codex CLI, retries a call that returns nothing, and saves each response. It has no source retrieval, financial calculation, response validation or database.

## Technical Details

### Components

One Python package, `agent_targets`, with one console entry point, `research`. It dispatches into the runner and the Codex adapter and uses only the standard library: argument parsing, subprocesses and file handling. No workflow framework is needed for six fixed stages.

### Run lifecycle

1. `research <ticker> [--model <model-id>]` locates the Codex executable and creates a new run directory.
2. For each of the six stages in order, the runner builds the prompt from the common policy, the stage template, the ticker and the saved responses of earlier stages, then invokes the CLI in a fresh attempt directory.
3. The CLI's final message is the stage response. An empty or missing final message, or a timeout, is no response.
4. A response is saved as `<stage>.md` and passed to later stages unchanged. The report stage's response is `report.md`.
5. A call with no response uses one of the stage's attempts. When they are exhausted the run fails and later stages do not run.

The stages are `initiation`, `research`, `modeling`, `refutation`, `comparison` and `report`, each a fresh call using the same model. No prompt relies on account memory or a previous conversation.

### Context and configuration

One common policy and six stage templates live in `prompts/`, found by stage name. Earlier responses arrive as labeled text blocks after the ticker. The model is `gpt-6-astra` unless `--model` overrides it; there is no configuration file.

Evidence cannot override trusted prompts or request credentials, broader tool access or execution of source-provided code. A source URL, ticker or model response is never turned into a shell command.

One execution profile applies: read-only model shell access, non-interactive approvals and live search. Agents calculate with the shell's PowerShell arithmetic. Credentials are not copied into the run, and organizational policy is not disabled to make a run succeed.

### Codex adapter

The documented CLI exposes JSONL events, a final-output file, ephemeral sessions and saved authentication. [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

The argument layout, confirmed against local CLI 0.154.0:

```text
codex --ask-for-approval never --search exec
  --ignore-user-config -c windows.sandbox="elevated" --ephemeral
  --sandbox read-only
  --skip-git-repo-check --cd <attempt-directory> --model <model-id>
  --json --output-last-message <attempt-candidate.md> -
```

`--ignore-user-config` avoids dependence on ordinary user config while retaining the CLI's authentication; it does not prove that every instruction or integration has been excluded. It also drops the Windows sandbox setting, and without a configured sandbox the CLI rejects every shell command as blocked by policy, leaving the agent no calculator. The explicit `windows.sandbox="elevated"` override restores command execution inside the read-only sandbox: PowerShell arithmetic runs and file creation is denied. The sandbox has no `python`, and PowerShell runs in constrained language mode, so method calls such as `[math]::Pow` are rejected. Live search must be explicit because the documented default is cached. `--skip-git-repo-check` supports a run directory that is not a repository. Never use sandbox or approval bypass flags. [CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

The adapter builds an argument list with `shell=False`, sends UTF-8 prompt bytes on stdin and writes the event stream and stderr straight to files in the attempt directory, so a full pipe cannot stall the child.

### Storage

```text
pyproject.toml
src/agent_targets/          CLI, runner, Codex adapter
prompts/                    common policy and six stage templates
tests/                      offline tests
runs/<run-id>/
  <stage>-attempt-<n>/      stdout.jsonl, stderr.log, attempt-candidate.md
  initiation.md             one saved response per stage
  research.md
  modeling.md
  refutation.md
  comparison.md
  report.md                 the report stage's response, saved byte for byte
```

Responses are saved as UTF-8 bytes that preserve whitespace and line endings. Runs and credentials stay out of version control; templates, code and tests are committed. Licensed source content stays local where permitted.

## Failure Handling

### Retries and limits

Each stage gets up to three model invocations including the first. A call that times out after ten minutes or leaves an empty final message uses one and is retried with the same input. Exhausting them fails the run with exit code 3 and later stages never run. Anything an agent reports about its own analysis is content, not a failure.

Source-tool requests happen inside the agent invocation and share its timeout. A timeout kills the direct Codex process only; containing descendants, for example with a Windows Job Object, is deferred. Invocation limits do not cap internal searches or tokens, and no stage waits for user input.

A failed run keeps its attempt directories and saved responses for diagnosis; the next try is a new run.

## Validation

Use a fake adapter to verify stage order, handoff, retries and report persistence. Use a short-lived real child process to verify the adapter's stdin delivery, diagnostics files, final-message reading and timeout.

## Not Implemented

- Supervisors for other operating systems, cross-run caching, distributed execution and alternative research backends.

## Open Questions

- Which inherited instructions and integrations remain active after configuration isolation?
- What timeout and attempt limits does the first company pilot justify?

## References

- [Project overview](README.md)
- [Workflow](workflow.md)
- [Valuation](valuation.md)
