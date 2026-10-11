__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import sys
from pathlib import Path

from agent_targets.codex import CodexAdapter

WRITES_FINAL_MESSAGE = (
    "import sys\n"
    "sys.stdin.buffer.read()\n"
    "open(sys.argv[1], 'w').write('# Final message')\n"
)
WRITES_BLANK_MESSAGE = (
    "import sys\n"
    "sys.stdin.buffer.read()\n"
    "open(sys.argv[1], 'w').write('  \\n')\n"
)
SLEEPS = "import time\ntime.sleep(30)\n"


def _invoke(tmp_path: Path, script: str, timeout_seconds: float) -> str | None:
    """
    Invoke an adapter whose child process is a short Python script.

    :param tmp_path: Directory used for the call's working files
    :param script: Python source the child runs; argv[1] is the final-message path
    :param timeout_seconds: Timeout passed to the adapter
    :returns: The adapter's final message text, or None
    """
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    adapter = CodexAdapter(tmp_path / "unused", "test-model")
    adapter.build_args = lambda context_dir, output_path: [
        sys.executable,
        "-c",
        script,
        str(output_path),
    ]
    return adapter.invoke(context_dir, "prompt", timeout_seconds)


def test_build_args_keeps_the_safety_flags(tmp_path: Path) -> None:
    """
    The argument list never relaxes approvals or the sandbox.

    :param tmp_path: Directory used for the executable and output paths
    """
    output_path = tmp_path / "out.md"
    args = CodexAdapter(tmp_path / "codex.exe", "test-model").build_args(
        tmp_path / "context", output_path
    )

    assert args[args.index("--ask-for-approval") + 1] == "never"
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert args[args.index("--model") + 1] == "test-model"
    assert args[args.index("--output-last-message") + 1] == str(output_path)
    assert args[args.index("-c") + 1] == 'windows.sandbox="elevated"'
    assert "--dangerously-bypass-approvals-and-sandbox" not in args
    assert "--output-schema" not in args
    assert "--search" in args
    assert args[-1] == "-"


def test_invoke_returns_the_final_message_and_saves_diagnostics(
    tmp_path: Path,
) -> None:
    """
    A real child process receives stdin and its final message is returned.

    :param tmp_path: Directory used for the call's working files
    """
    assert _invoke(tmp_path, WRITES_FINAL_MESSAGE, timeout_seconds=30) == (
        "# Final message"
    )
    assert (tmp_path / "context" / "stdout.jsonl").is_file()
    assert (tmp_path / "context" / "stderr.log").is_file()


def test_invoke_returns_none_for_a_blank_message(tmp_path: Path) -> None:
    """
    A blank final message counts as no response.

    :param tmp_path: Directory used for the call's working files
    """
    assert _invoke(tmp_path, WRITES_BLANK_MESSAGE, timeout_seconds=30) is None


def test_invoke_returns_none_when_the_call_times_out(tmp_path: Path) -> None:
    """
    A child that outlives the timeout is killed and yields no response.

    :param tmp_path: Directory used for the call's working files
    """
    assert _invoke(tmp_path, SLEEPS, timeout_seconds=1) is None
