__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodexResponse:
    """One call's final message and the conversation it belongs to."""

    text: str
    session_id: str


class CodexAdapter:
    """Builds arguments for and invokes the Codex CLI's non-interactive mode."""

    def __init__(self, executable: Path, model: str, effort: str) -> None:
        """
        :param executable: Resolved path to the Codex CLI executable
        :param model: Model identifier passed to every invocation
        :param effort: Reasoning effort level passed to every invocation
        """
        self._executable = executable
        self._model = model
        self._effort = effort

    def build_args(
        self, context_dir: Path, output_path: Path, session_id: str | None = None
    ) -> list[str]:
        """
        Build the documented non-interactive invocation argument list.

        :param context_dir: Read-only working directory for the call
        :param output_path: File the CLI writes its final message to
        :param session_id: Conversation to continue, or None to start a new one
        :returns: Complete argument list, passed without a shell
        """
        shared = [
            "--ignore-user-config",
            # The run directories sit inside this repository, so Codex would
            # otherwise load AGENTS.md, which is for developers, not analysts
            "-c",
            "project_doc_max_bytes=0",
            # Without this the Windows sandbox is unconfigured and the model's
            # shell commands are rejected, leaving it no calculator.
            "-c",
            'windows.sandbox="elevated"',
            "-c",
            f'model_reasoning_effort="{self._effort}"',
            "--skip-git-repo-check",
            "--model",
            self._model,
            "--json",
            "--output-last-message",
            str(output_path),
        ]
        prefix = [str(self._executable), "--ask-for-approval", "never", "--search"]

        if session_id is None:
            return [
                *prefix,
                "exec",
                *shared,
                "--sandbox",
                "read-only",
                "--cd",
                str(context_dir),
                "-",
            ]

        # `exec resume` has no --sandbox or --cd; the process working directory
        # is the call's context directory
        return [
            *prefix,
            "exec",
            "resume",
            *shared,
            "-c",
            'sandbox_mode="read-only"',
            session_id,
            "-",
        ]

    def invoke(
        self,
        context_dir: Path,
        prompt_text: str,
        timeout_seconds: float,
        session_id: str | None = None,
    ) -> CodexResponse | None:
        """
        Run one Codex CLI call and return its final message.

        The event stream and diagnostics are written to `stdout.jsonl` and
        `stderr.log` in `context_dir`. A timeout kills the direct child
        process; containing its descendants is deferred.

        :param context_dir: Read-only working directory for the call
        :param prompt_text: Combined instructions sent on stdin
        :param timeout_seconds: Maximum time to wait before killing the call
        :param session_id: Conversation to continue, or None to start a new one
        :returns: The final message and its conversation, or None on timeout,
            an empty message or a new conversation whose ID was not reported
        """
        output_path = context_dir / "attempt-candidate.md"
        args = self.build_args(context_dir, output_path, session_id)

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

        text = _read_final_message(output_path)
        session_id = session_id or _read_thread_id(context_dir / "stdout.jsonl")
        if text is None or session_id is None:
            return None
        return CodexResponse(text, session_id)


def _read_thread_id(path: Path) -> str | None:
    """
    Read the conversation ID from the event stream's `thread.started` event.

    :param path: JSONL event stream the CLI wrote
    :returns: The conversation ID, or None if no such event was written
    """
    with path.open(encoding="utf-8") as events:
        for line in events:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("type") == "thread.started":
                return event.get("thread_id")
    return None


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
