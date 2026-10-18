__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent_targets.codex import CodexAdapter
from agent_targets.runner import RunStatus, run_pipeline
from agent_targets.sources import SourceError, build_initiation_record, fetch_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Invalid usage exits 2 through argparse
EXIT_CODES = {RunStatus.COMPLETED: 0, RunStatus.FAILED: 3}
EXIT_SOURCE_FAILURE = 3

DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_EFFORT = "xhigh"


def build_parser() -> argparse.ArgumentParser:
    """:returns: Argument parser for the `research` command"""
    parser = argparse.ArgumentParser(
        prog="research",
        description="Run the agent-led company research and valuation pipeline.",
    )
    parser.add_argument("ticker", help="Company ticker to research")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Codex model identifier used for every stage (default: %(default)s)",
    )
    parser.add_argument(
        "--effort",
        default=DEFAULT_EFFORT,
        help=(
            "Reasoning effort level used for every stage; the available levels "
            "depend on the model (default: %(default)s)"
        ),
    )
    return parser


def run_research(argv: list[str] | None = None) -> int:
    """
    Entry point for the `research` console script.

    :param argv: Argument list, defaulting to `sys.argv[1:]`
    :returns: Exit code: 0 completed, 3 a source failed or a stage returned no response
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    executable = shutil.which("codex")

    # parser.error exits with status 2, so executable is a path from here on
    if executable is None:
        parser.error("Codex CLI executable not found on PATH")

    try:
        initiation_record = build_initiation_record(
            args.ticker, fetch_url, datetime.now(timezone.utc)
        )
    except SourceError as error:
        print(f"failed: {error}", file=sys.stderr)
        return EXIT_SOURCE_FAILURE

    result = run_pipeline(
        ticker=args.ticker,
        initiation_record=initiation_record,
        adapter=CodexAdapter(Path(executable), args.model, args.effort),
        prompts_directory=PROJECT_ROOT / "prompts",
        runs_directory=PROJECT_ROOT / "runs",
    )

    print(f"{result.status.value}: {result.run_dir}")
    if result.detail:
        print(result.detail, file=sys.stderr)
    return EXIT_CODES[result.status]
