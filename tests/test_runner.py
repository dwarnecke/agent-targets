__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

from pathlib import Path

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

    def invoke(
        self, context_dir: Path, prompt_text: str, timeout_seconds: float
    ) -> str | None:
        """
        Return the next scripted response for the stage named by the prompt.

        :param context_dir: Attempt directory; its name identifies the stage
        :param prompt_text: Prompt text captured for handoff assertions
        :param timeout_seconds: Timeout (unused by the fake)
        :returns: The scripted response, or None to simulate a failed call
        """
        stage_id = context_dir.name.rsplit("-attempt-", 1)[0]
        self.calls.append(stage_id)
        self.prompts[stage_id] = prompt_text
        queue = self.scripted[stage_id]
        return queue.pop(0) if len(queue) > 1 else queue[0]


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


def test_each_stage_receives_only_its_predecessors_text(tmp_path: Path) -> None:
    """
    A stage's prompt carries the ticker and earlier responses, never later ones.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    _run(adapter, tmp_path)

    assert "Ticker: WMT" in adapter.prompts["initiation"]
    assert "<accepted_stage" not in adapter.prompts["initiation"]
    modeling = adapter.prompts["modeling"]
    assert "initiation text" in modeling and "research text" in modeling
    assert "refutation text" not in modeling
    assert "modeling text" in adapter.prompts["refutation"]


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


def test_build_context_labels_each_accepted_response() -> None:
    """The prompt combines policy, template, ticker and labeled earlier text."""
    prompt = build_context(
        PROJECT_ROOT / "prompts", "research", "WMT", {"initiation": "EARLIER"}
    )

    assert prompt.count('<accepted_stage name="initiation">\nEARLIER\n') == 1
    assert "## Input\n\nTicker: WMT" in prompt
