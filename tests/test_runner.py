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
INITIATION = "Initiation facts: WMT closed at 112.28"


class FakeAdapter:
    """In-process stand-in for CodexAdapter that replays scripted responses."""

    def __init__(
        self,
        scripted: dict[str, list[str | None]] | None = None,
        model_files: dict[str, dict[str, str | None]] | None = None,
    ) -> None:
        """
        :param scripted: Responses per stage in call order; the last one repeats
        :param model_files: Files each stage writes under `model/`, by relative
            path; a None text deletes the file
        """
        self.scripted = {stage: [f"{stage} text"] for stage in STAGE_ORDER}
        self.scripted["report"] = [REPORT]
        self.scripted.update(scripted or {})
        self.model_files = model_files or {}
        self.calls: list[str] = []
        self.prompts: dict[str, str] = {}
        self.sessions: dict[str, str | None] = {}
        self.workspaces: dict[str, Path] = {}

    def invoke(
        self,
        context_dir: Path,
        workspace_dir: Path,
        prompt_text: str,
        timeout_seconds: float,
        session_id: str | None = None,
    ) -> CodexResponse | None:
        """
        Return the next scripted response for the stage named by the prompt.

        A new conversation gets a fresh ID; a resumed one keeps its ID. The
        stage's scripted model files are written into the workspace first.

        :param context_dir: Attempt directory; its name identifies the stage
        :param workspace_dir: Working directory the call may write to
        :param prompt_text: Prompt text captured for handoff assertions
        :param timeout_seconds: Timeout (unused by the fake)
        :param session_id: Conversation being continued, if any
        :returns: The scripted response, or None to simulate a failed call
        """
        stage_id = context_dir.name.rsplit("-attempt-", 1)[0]
        self.calls.append(stage_id)
        self.prompts[stage_id] = prompt_text
        self.sessions[stage_id] = session_id
        self.workspaces[stage_id] = workspace_dir
        for relative_path, text in self.model_files.get(stage_id, {}).items():
            path = workspace_dir / "model" / relative_path
            if text is None:
                path.unlink(missing_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
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
    return run_pipeline(
        "WMT", INITIATION, adapter, PROJECT_ROOT / "prompts", runs_directory
    )


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
    assert (result.run_dir / "initiation.md").read_text(encoding="utf-8") == INITIATION
    assert (result.run_dir / "report.md").read_bytes() == REPORT.encode("utf-8")


def test_review_runs_after_comparison_and_before_the_report() -> None:
    """The final review sees the comparison's edits and the report sees the review."""
    assert STAGE_ORDER[-3:] == ["comparison", "review", "report"]


def test_every_stage_continues_the_first_stages_conversation(
    tmp_path: Path,
) -> None:
    """
    The first stage starts the conversation and every later stage resumes it.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    _run(adapter, tmp_path)

    assert adapter.sessions["research"] is None
    for stage_id in STAGE_ORDER[1:]:
        assert adapter.sessions[stage_id] == "session-1"


def test_only_the_first_stage_receives_the_policy_ticker_and_initiation(
    tmp_path: Path,
) -> None:
    """
    Later stages get just their template, since the conversation holds the rest.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    _run(adapter, tmp_path)

    first_prompt = adapter.prompts["research"]
    assert "Common Analytical Policy" in first_prompt
    assert "Ticker: WMT" in first_prompt
    assert f"## Saved record: initiation\n\n{INITIATION}" in first_prompt
    for stage_id in STAGE_ORDER[1:]:
        prompt = adapter.prompts[stage_id]
        assert "Common Analytical Policy" not in prompt
        assert "Ticker:" not in prompt
        assert "<accepted_stage" not in prompt


def test_only_the_report_stage_receives_the_earlier_responses(tmp_path: Path) -> None:
    """
    The report prompt carries the initiation record and every earlier response.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    _run(adapter, tmp_path)

    report_prompt = adapter.prompts["report"]
    assert f"## Saved record: initiation\n\n{INITIATION}" in report_prompt
    for stage_id in STAGE_ORDER[:-1]:
        assert f"## Saved record: {stage_id}\n\n{stage_id} text" in report_prompt
    for stage_id in STAGE_ORDER[1:-1]:
        assert "## Saved record:" not in adapter.prompts[stage_id]
    assert "## Saved record: report" not in report_prompt


def test_failed_call_is_retried_and_the_run_completes(tmp_path: Path) -> None:
    """
    One failed call uses one attempt and the retry's response is used.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()
    adapter.scripted["modeling"].insert(0, None)

    result = _run(adapter, tmp_path)

    assert result.status is RunStatus.COMPLETED
    assert adapter.calls.count("modeling") == 2
    assert adapter.sessions["modeling"] == "session-1"


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
    prompt = build_context(PROJECT_ROOT / "prompts", "research", "WMT")

    assert "Common Analytical Policy" in prompt
    assert "## Input\n\nTicker: WMT" in prompt


def test_build_context_for_a_resumed_stage_is_only_its_template() -> None:
    """A resumed prompt omits what the conversation already holds."""
    prompt = build_context(PROJECT_ROOT / "prompts", "refutation", "WMT", resumed=True)

    assert prompt.startswith("# Stage: Refutation")
    assert "Common Analytical Policy" not in prompt and "Ticker:" not in prompt


def test_every_call_works_in_the_run_directory(tmp_path: Path) -> None:
    """
    Each stage runs in the run directory, which starts with an empty model directory.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter()

    result = _run(adapter, tmp_path)

    for stage_id in STAGE_ORDER:
        assert adapter.workspaces[stage_id] == result.run_dir
    assert list((result.run_dir / "model").iterdir()) == []


def test_workbooks_are_packed_after_the_stage_and_carried_into_the_report(
    tmp_path: Path,
) -> None:
    """
    A stage's tab files become an .xlsx and only the report prompt carries them.

    :param tmp_path: Directory the run directory is created in
    """
    tab = "Item\tUnit\tOpening\nRevenue\tUSD m\t100\nFair value per share\t\t=C2*2\n"
    adapter = FakeAdapter(model_files={"modeling": {"O1/Value.tsv": tab}})

    result = _run(adapter, tmp_path)

    model_dir = result.run_dir / "model"
    assert (model_dir / "O1.xlsx").is_file()
    assert "### O1 / Value" in (model_dir / "values.md").read_text(encoding="utf-8")
    assert "Fair value per share\t\t200" in adapter.prompts["report"]
    assert "## Saved record: workbooks" in adapter.prompts["report"]
    for stage_id in STAGE_ORDER[1:-1]:
        assert "## Saved record:" not in adapter.prompts[stage_id]
    assert not (model_dir / "problems.md").exists()


def test_a_packing_problem_is_saved_and_never_fails_the_run(tmp_path: Path) -> None:
    """
    A formula that cannot be evaluated is listed for the next stage and the report.

    :param tmp_path: Directory the run directory is created in
    """
    tab = "Item\tUnit\tOpening\nBad\t\t=1/0\n"
    adapter = FakeAdapter(model_files={"review": {"O1/Revenue.tsv": tab}})

    result = _run(adapter, tmp_path)

    assert result.status is RunStatus.COMPLETED
    problems = (result.run_dir / "model" / "problems.md").read_text(encoding="utf-8")
    assert "after report" in problems
    assert "O1/Revenue!C2: division by zero" in problems
    assert "## Saved record: workbook problems" in adapter.prompts["report"]


def test_a_later_stage_that_repairs_a_file_clears_the_problem(tmp_path: Path) -> None:
    """
    The problems file describes the latest state, so a repair removes it.

    :param tmp_path: Directory the run directory is created in
    """
    broken = "Item\tUnit\tOpening\nBad\t\t=1/0\n"
    repaired = "Item\tUnit\tOpening\nBad\t\t=1/2\n"
    adapter = FakeAdapter(
        model_files={
            "modeling": {"O1/Revenue.tsv": broken},
            "refutation": {"O1/Revenue.tsv": repaired},
        }
    )

    result = _run(adapter, tmp_path)

    assert not (result.run_dir / "model" / "problems.md").exists()
    assert "## Saved record: workbook problems" not in adapter.prompts["report"]


def test_a_workbook_with_no_tab_files_left_is_not_kept(tmp_path: Path) -> None:
    """
    A packed file follows its tab files, so a withdrawn outcome leaves no stale workbook.

    :param tmp_path: Directory the run directory is created in
    """
    adapter = FakeAdapter(
        model_files={
            "modeling": {"O3/Revenue.tsv": "Item\n1\n"},
            "comparison": {"O3/Revenue.tsv": None},
        }
    )

    result = _run(adapter, tmp_path)

    assert not (result.run_dir / "model" / "O3.xlsx").exists()
    assert "### O3" not in adapter.prompts["report"]
