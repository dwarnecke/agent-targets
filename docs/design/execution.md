# DCF Pipeline Execution

## Problem Statement

Unattended research calls must preserve their output and pass it forward, and a failed call must never leave a plausible partial result that looks accepted.

## Proposed Solution

A small local Python runner fetches the initiation facts, builds each stage's prompt, invokes the Codex CLI, retries a call that returns nothing, and saves each response. Agents also write their forecast schedules as plain-text tab files, and after each stage the runner packs them into Excel workbooks. Its only source retrieval is the initiation facts; it has no valuation logic, response validation or database, and the only arithmetic it performs is evaluating the formulas the agents wrote in those tab files.

## Technical Details

### Components

One Python package, `agent_targets`, with one console entry point, `research`. It dispatches into the initiation sources, the runner, the workbook packer and the Codex adapter and uses only the standard library: argument parsing, HTTP requests, zip and XML reading and writing, subprocesses and file handling. No workflow framework is needed for six fixed stages.

### Run lifecycle

1. `research <ticker> [--model <model-id>] [--effort <level>]` locates the Codex executable, then fetches and checks the initiation facts. An unreadable source or a stale rate ends the command with exit code 3 before a run directory exists. Otherwise it creates a new run directory with an empty `model/` directory and saves the facts as `initiation.md`.
2. For each of the six agent stages in order, the runner builds the prompt and invokes the CLI with the run directory as its working directory and a fresh attempt directory for the call's events and diagnostics. `research` starts the conversation and gets the common policy, its template, the ticker and the initiation record. Every later stage resumes that conversation, which already holds the policy, the ticker, the initiation record and all earlier work, so it gets only its template.
3. The CLI's final message is the stage response. An empty or missing final message, or a timeout, is no response. The first stage also needs the CLI to report its conversation ID, or its call counts as no response.
4. A response is saved as `<stage>.md`. The report stage's response is `report.md`. The ID of the conversation `research` started is resumed by every later stage.
5. After each response is saved the runner packs the tab files under `model/` into workbooks, as described in [workbooks](workflow.md#workbooks), and saves their evaluated tabs as text in `model/values.md`. Packing problems are saved to `model/problems.md` for the next stage to read and never fail the run. Both files are replaced after every stage.
6. A call with no response uses one of the stage's attempts. When they are exhausted the run fails and later stages do not run.

The agent stages are `research`, `modeling`, `refutation`, `comparison`, `review` and `report`, each using the same model. No prompt relies on account memory. The conversation is a persisted Codex session, so its context grows through the report stage and the CLI's own compaction applies.

### Context and configuration

One common policy and six stage templates live in `prompts/`, found by stage name. The report stage's prompt also carries the saved initiation record, the responses of the five earlier agent stages, the evaluated contents of every workbook and any open packing problems as labeled text blocks after its template, because compaction can drop schedule detail from the conversation. The workbooks hold the schedules, so a stage's response names the workbook tabs it changed instead of restating them. The model is `gpt-5.6-sol` unless `--model` overrides it. The reasoning effort is `xhigh` unless `--effort` overrides it; the levels available depend on the model. There is no configuration file.

Evidence cannot override trusted prompts or request credentials, broader tool access or execution of source-provided code. A source URL, ticker or model response is never turned into a shell command.

One execution profile applies: model shell access that can write only inside the run directory, non-interactive approvals and live search. Agents calculate with the shell's PowerShell arithmetic and write workbook tab files with its file cmdlets. The shell has no Python or spreadsheet library, which is why the runner packs the workbooks. Credentials are not copied into the run, and organizational policy is not disabled to make a run succeed.

### Codex adapter

The documented CLI exposes JSONL events, a final-output file, resumable sessions and saved authentication. [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

The argument layout for a new conversation. The earlier read-only form was confirmed against local CLI 0.154.0; the `workspace-write` value that replaces it is the documented alternative and is not yet confirmed (see the open questions):

```text
codex --ask-for-approval never --search exec
  --ignore-user-config -c project_doc_max_bytes=0
  -c windows.sandbox="elevated"
  -c model_reasoning_effort="<level>"
  --skip-git-repo-check --model <model-id>
  --json --output-last-message <attempt-candidate.md>
  --sandbox workspace-write --cd <run-directory> -
```

A continued conversation uses `exec resume`, which has no `--sandbox` or `--cd` option. It takes the same options with `-c sandbox_mode="workspace-write"` in place of `--sandbox`, runs in the run directory as its process working directory, and names the session before the final `-`:

```text
codex --ask-for-approval never --search exec resume
  --ignore-user-config -c project_doc_max_bytes=0
  -c windows.sandbox="elevated"
  -c model_reasoning_effort="<level>"
  --skip-git-repo-check --model <model-id>
  --json --output-last-message <attempt-candidate.md>
  -c sandbox_mode="workspace-write" <session-id> -
```

The session ID is the `thread_id` of the first `thread.started` event in `stdout.jsonl`. No call uses `--ephemeral`, because an ephemeral session cannot be resumed. The sessions are saved under the Codex home directory. Under the earlier read-only profile a resumed call kept the conversation's memory, was still denied file creation, and worked from a different working directory.
`--ignore-user-config` avoids dependence on ordinary user config while retaining the CLI's authentication; it does not prove that every instruction or integration has been excluded. `project_doc_max_bytes=0` stops the CLI from loading the repository's `AGENTS.md`, which the run directories inherit because they sit inside the repository; those notes are for developers and would send the analysis agents to read the repository documentation. `--ignore-user-config` also drops the Windows sandbox setting, and without a configured sandbox the CLI rejects every shell command as blocked by policy, leaving the agent no calculator. The explicit `windows.sandbox="elevated"` override restores command execution inside the sandbox: PowerShell arithmetic runs. The sandbox has no `python`, and PowerShell runs in constrained language mode, so method calls such as `[math]::Pow` are rejected; the agents write tab files with `Set-Content` and similar cmdlets. The intended write scope is the run directory, so a call cannot change another run or the repository's own files; confirming that scope is an open question. Live search must be explicit because the documented default is cached. `--skip-git-repo-check` supports a run directory that is not a repository. Never use sandbox or approval bypass flags. [CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

The adapter builds an argument list with `shell=False`, sends UTF-8 prompt bytes on stdin and writes the event stream and stderr straight to files in the attempt directory, so a full pipe cannot stall the child.

### Storage

```text
pyproject.toml
src/agent_targets/          CLI, initiation sources, runner, workbook packer, Codex adapter
prompts/                    common policy and six stage templates
scripts/                    report and model checks, design check
tests/                      offline tests
runs/<run-id>/
  <stage>-attempt-<n>/      stdout.jsonl, stderr.log, attempt-candidate.md
  initiation.md             the initiation record, written by code
  research.md               one saved response per agent stage
  modeling.md
  refutation.md
  comparison.md
  review.md
  report.md                 the report stage's response, saved byte for byte
  model/
    <book>/<Tab>.tsv        tab files written by the agents
    <book>.xlsx             workbook packed by the runner after each stage
    values.md               the evaluated tabs as text, replaced after each stage
    problems.md             packing problems from the latest stage, when any
```

Responses are saved as UTF-8 bytes that preserve whitespace and line endings. Runs and credentials stay out of version control; templates, code and tests are committed. Licensed source content stays local where permitted.

## Failure Handling

### Retries and limits

Each stage gets up to three model invocations including the first. A call that times out after thirty minutes or leaves an empty final message uses one and is retried with the same input. A retry in a resumed conversation continues it, so it can include what an interrupted attempt had already done. Exhausting the attempts fails the run with exit code 3 and later stages never run. Anything an agent reports about its own analysis is content, not a failure. Initiation requests are not retried; each has a 30-second timeout, and a failure ends the command with exit code 3.

Source-tool requests happen inside the agent invocation and share its timeout. A timeout kills the direct Codex process only; containing descendants, for example with a Windows Job Object, is deferred. Invocation limits do not cap internal searches or tokens, and no stage waits for user input.

A workbook packing problem is saved for the next stage and the report and never fails a run, because the runner does not reject a response for its content.

A failed run keeps its attempt directories, saved responses and model files for diagnosis; the next try is a new run.

## Validation

Use a fake adapter to verify stage order, that every stage after the first resumes one conversation, what each prompt carries, retries, report persistence and that workbooks are packed after each stage and carried in the report prompt. Use saved source responses to verify each initiation parser, the freshness limits and the rendered record. Use a short-lived real child process to verify the adapter's stdin delivery, diagnostics files, final-message and session-ID reading and timeout, and check the new and resume argument lists against the safety flags and the run-directory write scope. Verify the packer with sample tab files: formula evaluation, the generated `.xlsx` read back as a zip of XML, and each packing problem reported without failing. Check a finished run's workbooks with `scripts/check-model.ps1`; it reports facts and never changes a run.

## Not Implemented

- Supervisors for other operating systems, cross-run caching, distributed execution and alternative research backends.

## Open Questions

- Which inherited instructions and integrations remain active after configuration isolation?
- What timeout and attempt limits does the first company pilot justify?
- Does `workspace-write` confine a resumed call's writes to the run directory, and can agents create the tab files with the shell's constrained PowerShell?
- Does the report prompt stay within context when it carries the evaluated workbooks?

## References

- [Project overview](README.md)
- [Workflow](workflow.md)
- [Valuation](valuation.md)
