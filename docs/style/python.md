# Python Conventions

Use these conventions for Agent Targets Python code. Keep expressions readable, interfaces explicit and documentation consistent with the implementation.

## File layout and formatting

Use the author/email header shown in the example below. Follow it with imports, constants/type aliases, classes and functions; keep script entry points last. Group imports as standard library, third party and local, with blank lines between groups. Use absolute `agent_targets` imports without modifying `sys.path`.

A future import, when needed, must precede the metadata assignments. A standalone string below the header is not Python's module `__doc__`; use class/function docstrings or the project documentation for explanations.

- Use four spaces, double quotes by default, and f-strings for interpolation.
- Separate top-level definitions with two blank lines and methods with one. Separate meaningful steps within a function with blank lines.
- Aim for 88-character code lines. Wrap with parentheses and trailing commas; prefer one item per line in multiline calls and collections.
- Use keyword arguments when positional values would be ambiguous.
- Prefer named intermediate results, early returns and ordinary loops. Use a short comprehension for a simple mapping or filter; avoid nested expressions that conceal decisions or side effects.

Formatter/linter tooling is not yet configured.

## Names and types

Use `snake_case` for modules, functions, parameters and attributes; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants; and one leading underscore for internal helpers and state. For example, name a private instance field `_ticker`.

Name operations for their effect: `fetch_source`, `parse_response`, `validate_response`, `save_attempt`. A property or `get_` method should not unexpectedly fetch data or launch work. Name units where ambiguity matters, such as `timeout_seconds` or `treasury_10y_percent`.

Annotate parameters and returns accurately, including `-> None` for constructors and operations returning no value. Prefer built-in collections and union syntax: `list[str]`, `dict[str, str]`, `tuple[str, str]`, `Path | None`. Match actual tuple order and nullable behavior. Use a small dataclass or `TypedDict` for a stable shared record when it clarifies required fields; avoid spreading bare `dict` or `Any` across interfaces. An annotation does not replace external-data validation.

## Docstrings and comments

Give every class, function and method a triple-double-quoted rST docstring, including private helpers, one-line wrappers, `__init__`, dunder methods such as `__enter__`/`__exit__`, and properties. Start with a short purpose statement and describe important constraints or failures in prose. One-line docstrings are fine when the purpose statement is self-contained, but they do not excuse omitting required fields below.

Include a `:param name:` field for every parameter (skip only `self` and `cls`) and a `:returns:` field whenever the operation returns a value other than `None`; omit `:returns:` entirely when the operation always returns `None`. Keep types in signatures; omit `:type:`, `:rtype:` and `:raises:`. Keep parameter names, units and returned values synchronized with the implementation.

Comments explain intent, ownership or ordering. Prefer a single short line that stays on one line, for example `# Reserve the attempt before launch so a crash still consumes it`; reach for a longer or multi-line comment only when one line cannot carry the needed context. A single-line comment has no trailing period and is always preceded by a blank line. Multi-line comments use full sentences. Avoid narrating obvious statements, decorative banners and commented-out experiments.

## Example

These examples illustrate the conventions, including a trivial accessor documented like any other method.

```python
__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

from hashlib import sha256
from pathlib import Path


class ReportStore:
    """Owns the saved location of one run's report."""

    def __init__(self, run_dir: Path) -> None:
        """
        :param run_dir: Root directory of the run owning this report
        """
        self._run_dir = run_dir

    def report_path(self) -> Path:
        """:returns: Path of the run's saved report file"""
        return self._run_dir / "report.md"


def read_report(path: Path, expected_hash: str) -> str:
    """
    Read a saved report after verifying its exact bytes.

    Raise ValueError when the content hash differs. File access and UTF-8
    decoding errors propagate to the caller.

    :param path: Path of the saved report
    :param expected_hash: Expected SHA-256 hexadecimal digest of the report bytes
    :returns: Report text with its original whitespace and line endings
    """
    content = path.read_bytes()
    actual_hash = sha256(content).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"Report hash mismatch: {path}")

    # Decode bytes directly to preserve the report's saved line endings
    return content.decode("utf-8")
```
