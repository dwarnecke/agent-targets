__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import argparse
import shutil
import sys
from pathlib import Path

from agent_targets.codex import CodexAdapter
from agent_targets.runner import RunStatus, run_pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Invalid usage exits 2 through argparse
EXIT_CODES = {RunStatus.COMPLETED: 0, RunStatus.FAILED: 3}

DEFAULT_MODEL = "gpt-6-astra"


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
    return parser


def run_research(argv: list[str] | None = None) -> int:
    """
    Entry point for the `research` console script.

    :param argv: Argument list, defaulting to `sys.argv[1:]`
    :returns: Exit code: 0 completed, 3 a stage returned no response
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    executable = shutil.which("codex")

    # parser.error exits with status 2, so executable is a path from here on
    if executable is None:
        parser.error("Codex CLI executable not found on PATH")

    result = run_pipeline(
        ticker=args.ticker,
        adapter=CodexAdapter(Path(executable), args.model),
        prompts_directory=PROJECT_ROOT / "prompts",
        runs_directory=PROJECT_ROOT / "runs",
    )

    print(f"{result.status.value}: {result.run_dir}")
    if result.detail:
        print(result.detail, file=sys.stderr)
    return EXIT_CODES[result.status]
