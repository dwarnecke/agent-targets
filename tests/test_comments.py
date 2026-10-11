__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import io
import tokenize
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = ("src", "tests", "scripts")


def find_comment_problems() -> list[str]:
    """:returns: One ``path:line`` entry per single-line comment breaking the convention"""
    findings = []
    for root in SOURCE_ROOTS:
        for path in sorted((PROJECT_ROOT / root).rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()
            tokens = tokenize.generate_tokens(io.StringIO(source).readline)
            for token in tokens:
                if token.type != tokenize.COMMENT:
                    continue
                line_number = token.start[0]
                if not lines[line_number - 1].lstrip().startswith("#"):
                    continue

                previous = lines[line_number - 2].strip() if line_number > 1 else ""
                following = lines[line_number].strip() if line_number < len(lines) else ""
                if previous.startswith("#") or following.startswith("#"):
                    continue

                location = f"{path}:{line_number}"
                if token.string.endswith("."):
                    findings.append(f"{location} trailing period")
                if previous != "":
                    findings.append(f"{location} no blank line before comment")
    return findings


def test_single_line_comments_follow_convention() -> None:
    """Fail with a full list when a single-line comment breaks docs/style/python.md."""
    findings = find_comment_problems()
    assert not findings, "\n" + "\n".join(findings)
