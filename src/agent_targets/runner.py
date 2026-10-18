__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from secrets import token_hex

from agent_targets.codex import CodexAdapter, CodexResponse

STAGE_ORDER = [
    "research",
    "modeling",
    "refutation",
    "comparison",
    "review",
    "report",
]

MAX_ATTEMPTS_PER_STAGE = 3
CALL_TIMEOUT_SECONDS = 1800


class RunStatus(Enum):
    """Final outcome of one run."""

    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RunResult:
    """Outcome of one run and where its files were saved."""

    status: RunStatus
    run_dir: Path
    detail: str | None


def build_context(
    prompts_directory: Path,
    stage_id: str,
    ticker: str,
    resumed: bool = False,
    records: dict[str, str] | None = None,
) -> str:
    """
    Build one stage's prompt text.

    The first stage starts the conversation, so it gets the common policy, its
    template and the ticker. Every later stage resumes that conversation,
    which already holds the policy, the ticker and all earlier work, so it
    gets only its template. A stage given saved records also gets them in full:
    the first stage gets the initiation record, and the last gets every earlier
    record, because compaction can drop detail from the conversation.

    :param prompts_directory: Directory holding the policy and stage templates
    :param stage_id: Stage being built
    :param ticker: Company ticker being researched
    :param resumed: Whether the stage continues the run's conversation
    :param records: Saved responses of earlier stages, by stage ID
    :returns: Combined prompt text
    """
    template_path = prompts_directory / f"{stage_id}.md"
    parts = [template_path.read_text(encoding="utf-8")]
    if not resumed:
        policy_path = prompts_directory / "common.md"
        parts.insert(0, policy_path.read_text(encoding="utf-8"))
        parts.append(f"## Input\n\nTicker: {ticker}")
    for record_stage, text in (records or {}).items():
        parts.append(f"## Saved record: {record_stage}\n\n{text}")
    return "\n\n".join(parts) + "\n"


def run_pipeline(
    ticker: str,
    initiation_record: str,
    adapter: CodexAdapter,
    prompts_directory: Path,
    runs_directory: Path,
) -> RunResult:
    """
    Run the six stages in one conversation, saving each response.

    Stops only when a stage returns no response in its attempts. The
    initiation record is saved as `initiation.md` and given to the first and
    last stages. Each response is saved as `<stage>.md`; the report stage's
    response is the report.

    :param ticker: Company ticker to research
    :param initiation_record: Sourced security, quote and rate facts
    :param adapter: Object whose `invoke(context_dir, prompt_text,
        timeout_seconds, session_id)` returns a response with its text and
        conversation ID, or None
    :param prompts_directory: Directory holding the policy and stage templates
    :param runs_directory: Directory the new run directory is created in
    :returns: The run's outcome and run directory
    """
    started_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # The random suffix keeps runs started in the same second from colliding
    run_dir = runs_directory / f"{ticker.upper()}-{started_at}-{token_hex(2)}"
    run_dir.mkdir(parents=True)
    (run_dir / "initiation.md").write_bytes(initiation_record.encode("utf-8"))

    session_id: str | None = None
    responses: dict[str, str] = {"initiation": initiation_record}
    for stage_id in STAGE_ORDER:
        gets_records = stage_id in (STAGE_ORDER[0], STAGE_ORDER[-1])
        prompt_text = build_context(
            prompts_directory,
            stage_id,
            ticker,
            resumed=session_id is not None,
            records=responses if gets_records else None,
        )
        response = _run_stage(adapter, run_dir, stage_id, prompt_text, session_id)
        if response is None:
            detail = (
                f"Stage '{stage_id}' returned no response in "
                f"{MAX_ATTEMPTS_PER_STAGE} attempts"
            )
            return RunResult(RunStatus.FAILED, run_dir, detail)

        session_id = response.session_id
        responses[stage_id] = response.text

        # Bytes preserve the response's whitespace and line endings exactly
        (run_dir / f"{stage_id}.md").write_bytes(response.text.encode("utf-8"))

    return RunResult(RunStatus.COMPLETED, run_dir, None)


def _run_stage(
    adapter: CodexAdapter,
    run_dir: Path,
    stage_id: str,
    prompt_text: str,
    session_id: str | None,
) -> CodexResponse | None:
    """
    Invoke one stage until it returns a response or attempts run out.

    Each attempt gets its own directory holding the CLI's events,
    diagnostics and final message. A timeout or empty final message uses up
    one attempt. A retry in a resumed conversation continues it, so it may
    include what an interrupted attempt had already done.

    :param adapter: Adapter used to invoke the model
    :param run_dir: Run directory the attempt directories are created in
    :param stage_id: Stage being run
    :param prompt_text: Complete prompt sent on every attempt
    :param session_id: Conversation to continue, or None to start a new one
    :returns: The first response, or None if every attempt failed
    """
    for attempt in range(1, MAX_ATTEMPTS_PER_STAGE + 1):
        attempt_dir = run_dir / f"{stage_id}-attempt-{attempt}"
        attempt_dir.mkdir()
        response = adapter.invoke(
            context_dir=attempt_dir,
            prompt_text=prompt_text,
            timeout_seconds=CALL_TIMEOUT_SECONDS,
            session_id=session_id,
        )
        if response is not None:
            return response
    return None
