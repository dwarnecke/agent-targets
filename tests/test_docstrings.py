__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = ("src", "tests", "scripts")
PARAM_PATTERN = re.compile(r"^\s*:param (\w+):", re.MULTILINE)
RETURNS_PATTERN = re.compile(r"^\s*:returns:", re.MULTILINE)


def _python_files() -> list[Path]:
    """:returns: Every project Python file covered by the docstring convention"""
    return sorted(
        path
        for root in SOURCE_ROOTS
        for path in (PROJECT_ROOT / root).rglob("*.py")
        if (PROJECT_ROOT / root).is_dir()
    )


def _own_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    """
    Collect the nodes of a function body, excluding nested scopes.

    :param function: Function whose own statements are inspected
    :returns: Body nodes that belong to this function rather than a nested one
    """
    nodes: list[ast.AST] = []
    pending: list[ast.AST] = list(function.body)
    while pending:
        node = pending.pop()
        nodes.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        pending.extend(ast.iter_child_nodes(node))
    return nodes


def _returns_value(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """
    Decide whether a function returns something other than ``None``.

    The return annotation decides when present; otherwise the body does.

    :param function: Function to classify
    :returns: True when callers receive a value that needs a ``:returns:`` field
    """
    annotation = function.returns
    if annotation is not None:
        return not (isinstance(annotation, ast.Constant) and annotation.value is None)

    for node in _own_nodes(function):
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(node, ast.Return) and node.value is not None:
            if not (isinstance(node.value, ast.Constant) and node.value.value is None):
                return True
    return False


def _parameter_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """
    List the parameters a docstring must document.

    :param function: Function whose signature is inspected
    :returns: Parameter names in order, excluding ``self`` and ``cls``
    """
    arguments = function.args
    parameters = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    if arguments.vararg is not None:
        parameters.append(arguments.vararg)
    if arguments.kwarg is not None:
        parameters.append(arguments.kwarg)
    return [parameter.arg for parameter in parameters if parameter.arg not in ("self", "cls")]


def _function_problems(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """
    Check one function's docstring against its signature and return behavior.

    :param function: Function or method to check
    :returns: Descriptions of each convention violation, empty when compliant
    """
    docstring = ast.get_docstring(function, clean=False)
    if docstring is None:
        return ["missing docstring"]

    problems = []
    documented = PARAM_PATTERN.findall(docstring)
    actual = _parameter_names(function)
    for name in actual:
        if name not in documented:
            problems.append(f"missing :param {name}:")
    for name in documented:
        if name not in actual:
            problems.append(f"documents unknown parameter {name}")

    has_returns = RETURNS_PATTERN.search(docstring) is not None
    returns_value = _returns_value(function)
    if returns_value and not has_returns:
        problems.append("missing :returns:")
    if has_returns and not returns_value:
        problems.append("has :returns: but returns None")
    return problems


def find_docstring_problems() -> list[str]:
    """:returns: One ``path:line name: problem`` entry per convention violation"""
    findings = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and ast.get_docstring(node) is None:
                findings.append(f"{path}:{node.lineno} {node.name}: missing docstring")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for problem in _function_problems(node):
                    findings.append(f"{path}:{node.lineno} {node.name}: {problem}")
    return findings


def test_every_class_and_function_follows_docstring_convention() -> None:
    """Fail with a full list when any class or function breaks docs/style/python.md."""
    findings = find_docstring_problems()
    assert not findings, "\n" + "\n".join(findings)
