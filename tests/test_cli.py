__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

from pathlib import Path

import pytest

from agent_targets import cli
from agent_targets.runner import RunResult, RunStatus
from agent_targets.sources import SourceError


def test_the_model_defaults_to_gpt_5_6_sol() -> None:
    """Omitting --model selects the default model, and --model overrides it."""
    parser = cli.build_parser()

    assert parser.parse_args(["WMT"]).model == "gpt-5.6-sol"
    assert parser.parse_args(["WMT", "--model", "test-model"]).model == "test-model"


def test_the_effort_defaults_to_xhigh() -> None:
    """Omitting --effort selects extra high, and --effort overrides it."""
    parser = cli.build_parser()

    assert parser.parse_args(["WMT"]).effort == "xhigh"
    assert parser.parse_args(["WMT", "--effort", "low"]).effort == "low"


def test_missing_codex_executable_is_invalid_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Without a Codex executable on PATH the command exits 2 instead of starting a run.

    :param monkeypatch: Pytest fixture used to hide the executable
    """
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)

    with pytest.raises(SystemExit) as exit_info:
        cli.run_research(["WMT", "--model", "test-model"])

    assert exit_info.value.code == 2


def test_each_run_status_maps_to_its_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Completed and failed runs exit 0 and 3.

    :param monkeypatch: Pytest fixture used to stub the executable and the pipeline
    :param tmp_path: Directory reported as the run directory
    """
    monkeypatch.setattr(cli.shutil, "which", lambda name: "codex")
    monkeypatch.setattr(cli, "build_initiation_record", lambda *args: "record")
    expected = {RunStatus.COMPLETED: 0, RunStatus.FAILED: 3}

    for status, exit_code in expected.items():
        monkeypatch.setattr(
            cli, "run_pipeline", lambda **kwargs: RunResult(status, tmp_path, None)
        )
        assert cli.run_research(["WMT", "--model", "test-model"]) == exit_code


def test_a_failed_source_exits_3_before_any_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An unreadable or stale initiation source ends the command without a run.

    :param monkeypatch: Pytest fixture used to stub the executable and sources
    """
    monkeypatch.setattr(cli.shutil, "which", lambda name: "codex")

    def fail(*args: object) -> str:
        """
        :param args: Ignored arguments
        :returns: Never returns
        """
        raise SourceError("Treasury observation is too old")

    def unexpected_run(**kwargs: object) -> None:
        """
        :param kwargs: Ignored arguments
        """
        raise AssertionError("The pipeline must not start")

    monkeypatch.setattr(cli, "build_initiation_record", fail)
    monkeypatch.setattr(cli, "run_pipeline", unexpected_run)

    assert cli.run_research(["WMT"]) == 3
