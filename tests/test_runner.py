__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

from pathlib import Path

from agent_targets.codex import CodexResponse
from agent_targets.runner import (
    MAX_ATTEMPTS_PER_STAGE,
    STAGE_ORDER,
    RunResult,
    RunStatus,
    build_context,
    run_pipeline,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT = "# Report\r\n\r\nValue: 60  \r\n"


class FakeAdapter:
    """In-process stand-in for CodexAdapter that replays scripted responses."""

    def __init__(self, scripted: dict[str, list[str | None]] | None = None) -> None:
        """
        :param scripted: Responses per stage in call order; the last one repeats
        """
        self.scripted = {stage: [f"{stage} text"] for stage in STAGE_ORDER}
        self.scripted["report"] = [REPORT]
        self.scripted.update(scripted or {})
        self.calls: list[str] = []
        self.prompts: dict[str, str] = {}
        self.sessions: dict[str, str | None] = {}

    def invoke(
        self,
        context_dir: Path,
        prompt_text: str,
        timeout_seconds: float,
        session_id: str | None = None,
    ) -> CodexResponse | None:
        """
        Return the next scripted response for the stage named by the prompt.

        A new conversation gets a fresh ID; a resumed one keeps its ID.

        :param context_dir: Attempt directory; its name identifies the stage
        :param prompt_text: Prompt text captured for handoff assertions
        :param timeout_seconds: Timeout (unused by the fake)
        :param session_id: Conversation being continued, if any
        :returns: The scripted response, or None to simulate a failed call
        """
        stage_id = context_dir.name.rsplit("-attempt-", 1)[0]
        self.calls.append(stage_id)
        self.prompts[stage_id] = prompt_text
        self.sessions[stage_id] = session_id
        queue = self.scripted[stage_id]
        text = queue.pop(0) if len(queue) > 1 else queue[0]
        if text is None:
            return None
        return CodexResponse(text, session_id or f"session-{len(self.calls)}")


def _run(adapter: FakeAdapter, runs_directory: Path) -> RunResult:
    """
    Run the pipeline with the real prompts against a fake adapter.

    :param adapter: Fake adapter scripted for the scenario
    :param runs_directory: Directory the run directory is created in
    :returns: The run's result
    """
    return run_pipeline("WMT", adapter, PROJECT_ROOT / "prompts", runs_directory)


def test_full_run_saves_every_stage_and_exact_report_bytes(tmp_path: Path) -> None:
    """
    All six stages run once in order and the report is saved byte for byte.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    result = _run(adapter, tmp_path)

    assert result.status is RunStatus.COMPLETED
    assert adapter.calls == STAGE_ORDER
    for stage_id in STAGE_ORDER:
        assert (result.run_dir / f"{stage_id}.md").is_file()
    assert (result.run_dir / "report.md").read_bytes() == REPORT.encode("utf-8")


def test_every_stage_continues_the_first_stages_conversation(
    tmp_path: Path,
) -> None:
    """
    The first stage starts the conversation and every later stage resumes it.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    _run(adapter, tmp_path)

    assert adapter.sessions["initiation"] is None
    for stage_id in STAGE_ORDER[1:]:
        assert adapter.sessions[stage_id] == "session-1"


def test_only_the_first_stage_receives_the_policy_and_ticker(tmp_path: Path) -> None:
    """
    Later stages get just their template, since the conversation holds the rest.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    _run(adapter, tmp_path)

    assert "Common Analytical Policy" in adapter.prompts["initiation"]
    assert "Ticker: WMT" in adapter.prompts["initiation"]
    for stage_id in STAGE_ORDER[1:]:
        prompt = adapter.prompts[stage_id]
        assert "Common Analytical Policy" not in prompt
        assert "Ticker:" not in prompt
        assert "<accepted_stage" not in prompt


def test_only_the_report_stage_receives_the_earlier_responses(tmp_path: Path) -> None:
    """
    The report prompt carries every earlier response in full; no other stage does.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    _run(adapter, tmp_path)

    for stage_id in STAGE_ORDER[:-1]:
        assert f"## Saved record: {stage_id}\n\n{stage_id} text" in adapter.prompts["report"]
        assert "## Saved record:" not in adapter.prompts[stage_id]
    assert "## Saved record: report" not in adapter.prompts["report"]


def test_failed_call_is_retried_and_the_run_completes(tmp_path: Path) -> None:
    """
    One failed call uses one attempt and the retry's response is used.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()
    adapter.scripted["research"].insert(0, None)

    result = _run(adapter, tmp_path)

    assert result.status is RunStatus.COMPLETED
    assert adapter.calls.count("research") == 2
    assert adapter.sessions["research"] == "session-1"


def test_stage_without_a_response_fails_after_its_attempts(tmp_path: Path) -> None:
    """
    A stage with no response fails the run and later stages never run.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter({"modeling": [None]})

    result = _run(adapter, tmp_path)

    assert result.status is RunStatus.FAILED
    assert adapter.calls.count("modeling") == MAX_ATTEMPTS_PER_STAGE
    assert "refutation" not in adapter.calls
    assert (result.run_dir / "research.md").is_file()
    assert not (result.run_dir / "report.md").exists()


def test_build_context_starts_a_conversation_with_policy_template_and_ticker() -> None:
    """A new conversation's prompt has the policy, the template and the ticker."""
    prompt = build_context(PROJECT_ROOT / "prompts", "initiation", "WMT")

    assert "Common Analytical Policy" in prompt
    assert "## Input\n\nTicker: WMT" in prompt


def test_build_context_for_a_resumed_stage_is_only_its_template() -> None:
    """A resumed prompt omits what the conversation already holds."""
    prompt = build_context(PROJECT_ROOT / "prompts", "refutation", "WMT", resumed=True)

    assert prompt.startswith("# Stage: Refutation")
    assert "Common Analytical Policy" not in prompt and "Ticker:" not in prompt
