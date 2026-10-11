__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from secrets import token_hex

from agent_targets.codex import CodexAdapter

STAGE_ORDER = [
    "initiation",
    "research",
    "modeling",
    "refutation",
    "comparison",
    "report",
]
MAX_ATTEMPTS_PER_STAGE = 3
CALL_TIMEOUT_SECONDS = 600


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
    prompts_directory: Path, stage_id: str, ticker: str, accepted: dict[str, str]
) -> str:
    """
    Build one stage's prompt text.

    Combines the common policy and the stage template with the ticker and
    every accepted predecessor response, inlined as labeled text.

    :param prompts_directory: Directory holding the policy and stage templates
    :param stage_id: Stage being built
    :param ticker: Company ticker being researched
    :param accepted: Accepted stage responses so far, keyed by stage ID
    :returns: Combined prompt text
    """
    policy_path = prompts_directory / "common.md"
    template_path = prompts_directory / f"{stage_id}.md"

    parts = [
        policy_path.read_text(encoding="utf-8"),
        template_path.read_text(encoding="utf-8"),
        f"## Input\n\nTicker: {ticker}",
    ]

    # Only earlier stages are inlined, so a stage never sees later output
    for stage in STAGE_ORDER[: STAGE_ORDER.index(stage_id)]:
        if stage in accepted:
            parts.append(
                f'<accepted_stage name="{stage}">\n{accepted[stage]}\n</accepted_stage>'
            )
    return "\n\n".join(parts) + "\n"


def run_pipeline(
    ticker: str,
    adapter: CodexAdapter,
    prompts_directory: Path,
    runs_directory: Path,
) -> RunResult:
    """
    Run the six stages in order, saving each response to a new run directory.

    Stops only when a stage returns no response in its attempts. Each response
    is saved as `<stage>.md`; the report stage's response is the report.

    :param ticker: Company ticker to research
    :param adapter: Object whose `invoke(context_dir, prompt_text,
        timeout_seconds)` returns the final message text or None
    :param prompts_directory: Directory holding the policy and stage templates
    :param runs_directory: Directory the new run directory is created in
    :returns: The run's outcome and run directory
    """
    started_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # The random suffix keeps runs started in the same second from colliding
    run_dir = runs_directory / f"{ticker.upper()}-{started_at}-{token_hex(2)}"
    run_dir.mkdir(parents=True)

    accepted: dict[str, str] = {}
    for stage_id in STAGE_ORDER:
        prompt_text = build_context(prompts_directory, stage_id, ticker, accepted)
        response = _run_stage(adapter, run_dir, stage_id, prompt_text)
        if response is None:
            detail = (
                f"Stage '{stage_id}' returned no response in "
                f"{MAX_ATTEMPTS_PER_STAGE} attempts"
            )
            return RunResult(RunStatus.FAILED, run_dir, detail)

        accepted[stage_id] = response

        # Bytes preserve the response's whitespace and line endings exactly
        (run_dir / f"{stage_id}.md").write_bytes(response.encode("utf-8"))

    return RunResult(RunStatus.COMPLETED, run_dir, None)


def _run_stage(
    adapter: CodexAdapter, run_dir: Path, stage_id: str, prompt_text: str
) -> str | None:
    """
    Invoke one stage until it returns a response or attempts run out.

    Each attempt gets its own directory holding the CLI's events,
    diagnostics and final message. A timeout or empty final message uses up
    one attempt.

    :param adapter: Adapter used to invoke the model
    :param run_dir: Run directory the attempt directories are created in
    :param stage_id: Stage being run
    :param prompt_text: Complete prompt sent on every attempt
    :returns: The first response, or None if every attempt failed
    """
    for attempt in range(1, MAX_ATTEMPTS_PER_STAGE + 1):
        attempt_dir = run_dir / f"{stage_id}-attempt-{attempt}"
        attempt_dir.mkdir()
        response = adapter.invoke(
            context_dir=attempt_dir,
            prompt_text=prompt_text,
            timeout_seconds=CALL_TIMEOUT_SECONDS,
        )
        if response is not None:
            return response
    return None
