__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import subprocess
from pathlib import Path


class CodexAdapter:
    """Builds arguments for and invokes the Codex CLI's non-interactive mode."""

    def __init__(self, executable: Path, model: str) -> None:
        """
        :param executable: Resolved path to the Codex CLI executable
        :param model: Model identifier passed to every invocation
        """
        self._executable = executable
        self._model = model

    def build_args(self, context_dir: Path, output_path: Path) -> list[str]:
        """
        Build the documented non-interactive invocation argument list.

        :param context_dir: Read-only working directory for the call
        :param output_path: File the CLI writes its final message to
        :returns: Complete argument list, passed without a shell
        """
        return [
            str(self._executable),
            "--ask-for-approval",
            "never",
            "--search",
            "exec",
            "--ignore-user-config",
            # Without this the Windows sandbox is unconfigured and the model's
            # shell commands are rejected, leaving it no calculator.
            "-c",
            'windows.sandbox="elevated"',
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--cd",
            str(context_dir),
            "--model",
            self._model,
            "--json",
            "--output-last-message",
            str(output_path),
            "-",
        ]

    def invoke(
        self, context_dir: Path, prompt_text: str, timeout_seconds: float
    ) -> str | None:
        """
        Run one Codex CLI call and return its final message.

        The event stream and diagnostics are written to `stdout.jsonl` and
        `stderr.log` in `context_dir`. A timeout kills the direct child
        process; containing its descendants is deferred.

        :param context_dir: Read-only working directory for the call
        :param prompt_text: Combined instructions sent on stdin
        :param timeout_seconds: Maximum time to wait before killing the call
        :returns: The final message text, or None on timeout or an empty message
        """
        output_path = context_dir / "attempt-candidate.md"
        args = self.build_args(context_dir, output_path)

        # The child writes straight to files, so a full pipe can never stall it
        with (
            (context_dir / "stdout.jsonl").open("wb") as stdout,
            (context_dir / "stderr.log").open("wb") as stderr,
        ):
            try:
                subprocess.run(
                    args,
                    cwd=context_dir,
                    input=prompt_text.encode("utf-8"),
                    stdout=stdout,
                    stderr=stderr,
                    timeout=timeout_seconds,
                    shell=False,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return None

        return _read_final_message(output_path)


def _read_final_message(path: Path) -> str | None:
    """
    Read the CLI's final-message file.

    :param path: File the CLI was told to write its final message to
    :returns: The message text, or None if the file is absent or blank
    """
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return text if text.strip() else None
