__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import math
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

COMPANY_BOOK = "company"
RETIRED_SUFFIX = "-retired"
GOING_CONCERN_TABS = (
    "Inputs",
    "Revenue",
    "Income",
    "Balance",
    "CashFlow",
    "Value",
    "Tests",
)
EVENT_TABS = ("Inputs", "Recovery", "Tests")
TAB_ORDER = (
    "Inputs",
    "Revenue",
    "Income",
    "Balance",
    "CashFlow",
    "Value",
    "Recovery",
    "Tests",
)
BOOK_NAME = re.compile(r"[A-Za-z0-9_-]+")
TAB_NAME = re.compile(r"[A-Za-z0-9_ ]{1,31}")
NUMBER_TEXT = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
CELL_REFERENCE = re.compile(r"\$?([A-Za-z]{1,3})\$?(\d+)")
XML_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
TOKEN_PATTERN = re.compile(
    r"""
    (?P<space>\s+)
    | (?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
    | (?P<string>"[^"]*")
    | (?P<function>[A-Za-z][A-Za-z0-9.]*)(?=\()
    | (?P<reference>
        (?:(?:'[^']+'|[A-Za-z0-9_]+)!)?
        \$?[A-Za-z]{1,3}\$?\d+
        (?::\$?[A-Za-z]{1,3}\$?\d+)?
      )
    | (?P<operator><=|>=|<>|[-+*/^%(),=<>])
    """,
    re.VERBOSE,
)
COMPARISONS = ("=", "<>", "<", ">", "<=", ">=")
CHECK_TOLERANCE = 1e-6
VALUE_LABEL = "Fair value per share"
VALUE_TABS = ("Value", "Recovery")
SPREADSHEET_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
STYLES_XML = (
    XML_HEADER
    + f'<styleSheet xmlns="{SPREADSHEET_NAMESPACE}">'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/>'
    "</border></borders>"
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
    "</cellStyleXfs>"
    '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" '
    'xfId="0"/></cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/>'
    "</cellStyles></styleSheet>"
)

CellKey = tuple[str, int, int]


class FormulaError(Exception):
    """A formula that cannot be parsed or evaluated, with the reason."""


@dataclass(frozen=True)
class Cell:
    """One cell as the agent wrote it."""

    raw: str
    number: float | None

    @property
    def is_formula(self) -> bool:
        """:returns: Whether the cell holds a formula"""
        return self.raw.startswith("=")


@dataclass(frozen=True)
class Tab:
    """One tab: its name and its non-blank cells by zero-based row and column."""

    name: str
    cells: dict[tuple[int, int], Cell]


@dataclass(frozen=True)
class Book:
    """One workbook: its name and its tabs by tab name."""

    name: str
    tabs: dict[str, Tab]


@dataclass(frozen=True)
class Evaluated:
    """A cell's evaluated value, or the reason it has none."""

    value: float | str | bool | None
    error: str | None


@dataclass(frozen=True)
class CheckReport:
    """Facts about one model directory, for a person to read."""

    findings: list[str]
    values: dict[str, float | None]


def column_letters(column: int) -> str:
    """
    Convert a zero-based column index to spreadsheet letters.

    :param column: Zero-based column index
    :returns: Letters such as ``A`` for 0 and ``AA`` for 26
    """
    letters = ""
    number = column + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def cell_label(row: int, column: int) -> str:
    """
    Name a cell the way a spreadsheet does.

    :param row: Zero-based row index
    :param column: Zero-based column index
    :returns: Label such as ``D7``
    """
    return f"{column_letters(column)}{row + 1}"


def _decode(data: bytes) -> str:
    """
    Decode a tab file, accepting UTF-8 and the UTF-16 PowerShell can write.

    :param data: File bytes
    :returns: File text without a byte-order mark
    """
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def parse_tab(name: str, text: str) -> Tab:
    """
    Parse tab-separated text into cells.

    A cell beginning with ``=`` is a formula, a cell that reads as a plain
    number is a number, and anything else is text. Blank cells are omitted.

    :param name: Tab name
    :param text: Contents of the tab file
    :returns: The parsed tab
    """
    cells: dict[tuple[int, int], Cell] = {}
    for row, line in enumerate(text.splitlines()):
        for column, raw in enumerate(line.split("\t")):
            raw = raw.strip()
            if not raw:
                continue
            number = float(raw) if NUMBER_TEXT.fullmatch(raw) else None
            if number is not None and not math.isfinite(number):
                number = None
            cells[(row, column)] = Cell(raw, number)
    return Tab(name, cells)


def load_books(model_dir: Path) -> tuple[list[Book], list[str]]:
    """
    Read every workbook directory under the model directory.

    A directory or file whose name cannot be used, or a file that cannot be
    read, is skipped and reported.

    :param model_dir: Directory holding one subdirectory per workbook
    :returns: The books in name order and one problem line per skipped item
    """
    books: list[Book] = []
    problems: list[str] = []
    if not model_dir.is_dir():
        return books, problems

    for book_dir in sorted(path for path in model_dir.iterdir() if path.is_dir()):
        if not BOOK_NAME.fullmatch(book_dir.name):
            problems.append(
                f"{book_dir.name}: workbook directory name must use only "
                "letters, digits, - and _"
            )
            continue

        tabs: dict[str, Tab] = {}
        for tab_path in sorted(book_dir.glob("*.tsv")):
            if not TAB_NAME.fullmatch(tab_path.stem):
                problems.append(
                    f"{book_dir.name}/{tab_path.name}: tab name must use only "
                    "letters, digits, spaces and _ and be at most 31 characters"
                )
                continue
            try:
                text = _decode(tab_path.read_bytes())
            except (OSError, UnicodeDecodeError) as error:
                problems.append(f"{book_dir.name}/{tab_path.name}: unreadable ({error})")
                continue
            tabs[tab_path.stem] = parse_tab(tab_path.stem, text)
        if tabs:
            books.append(Book(book_dir.name, tabs))
    return books, problems


def _tokenize(formula: str) -> list[tuple[str, str]]:
    """
    Split a formula into tokens.

    :param formula: Formula text without the leading ``=``
    :returns: Pairs of token kind and text, without whitespace
    """
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(formula):
        match = TOKEN_PATTERN.match(formula, position)
        if match is None:
            raise FormulaError(f"unexpected text {formula[position:position + 12]!r}")
        position = match.end()
        if match.lastgroup != "space":
            tokens.append((str(match.lastgroup), match.group()))
    return tokens


def _parse_cell(text: str) -> tuple[int, int]:
    """
    Convert a cell reference without a tab to zero-based row and column.

    :param text: Reference such as ``$D$7``
    :returns: Zero-based row and column
    """
    match = CELL_REFERENCE.fullmatch(text)
    if match is None:
        raise FormulaError(f"bad cell reference {text!r}")
    column = 0
    for letter in match.group(1).upper():
        column = column * 26 + (ord(letter) - ord("A") + 1)
    row = int(match.group(2))
    if row < 1:
        raise FormulaError(f"bad cell reference {text!r}")
    return row - 1, column - 1


class _Parser:
    """Recursive-descent parser from formula text to a small syntax tree."""

    def __init__(self, formula: str, tab_name: str) -> None:
        """
        :param formula: Formula text without the leading ``=``
        :param tab_name: Tab that unqualified references belong to
        """
        self._tokens = _tokenize(formula)
        self._tab_name = tab_name
        self._position = 0

    def parse(self) -> tuple:
        """:returns: The syntax tree of the whole formula"""
        if not self._tokens:
            raise FormulaError("empty formula")
        tree = self._comparison()
        if self._position != len(self._tokens):
            raise FormulaError(f"unexpected {self._tokens[self._position][1]!r}")
        return tree

    def _peek(self) -> tuple[str, str] | None:
        """:returns: The next token, or None at the end"""
        if self._position < len(self._tokens):
            return self._tokens[self._position]
        return None

    def _take_operator(self, operators: tuple[str, ...]) -> str | None:
        """
        Consume the next token when it is one of the given operators.

        :param operators: Operator texts to accept
        :returns: The operator consumed, or None when the next token differs
        """
        token = self._peek()
        if token is not None and token[0] == "operator" and token[1] in operators:
            self._position += 1
            return token[1]
        return None

    def _comparison(self) -> tuple:
        """:returns: Syntax tree of a comparison or anything tighter"""
        left = self._additive()
        operator = self._take_operator(COMPARISONS)
        while operator is not None:
            left = ("bin", operator, left, self._additive())
            operator = self._take_operator(COMPARISONS)
        return left

    def _additive(self) -> tuple:
        """:returns: Syntax tree of a sum or difference or anything tighter"""
        left = self._term()
        operator = self._take_operator(("+", "-"))
        while operator is not None:
            left = ("bin", operator, left, self._term())
            operator = self._take_operator(("+", "-"))
        return left

    def _term(self) -> tuple:
        """:returns: Syntax tree of a product or quotient or anything tighter"""
        left = self._power()
        operator = self._take_operator(("*", "/"))
        while operator is not None:
            left = ("bin", operator, left, self._power())
            operator = self._take_operator(("*", "/"))
        return left

    def _power(self) -> tuple:
        """:returns: Syntax tree of a power, grouped left to right as a spreadsheet does"""
        left = self._unary()
        while self._take_operator(("^",)) is not None:
            left = ("bin", "^", left, self._unary())
        return left

    def _unary(self) -> tuple:
        """:returns: Syntax tree of a signed operand"""
        operator = self._take_operator(("-", "+"))
        if operator == "-":
            return ("neg", self._unary())
        if operator == "+":
            return self._unary()
        return self._postfix()

    def _postfix(self) -> tuple:
        """:returns: Syntax tree of an operand with any percent signs applied"""
        operand = self._primary()
        while self._take_operator(("%",)) is not None:
            operand = ("percent", operand)
        return operand

    def _primary(self) -> tuple:
        """:returns: Syntax tree of a number, text, reference, call or group"""
        token = self._peek()
        if token is None:
            raise FormulaError("formula ends early")
        self._position += 1
        kind, text = token

        if kind == "number":
            return ("number", float(text))
        if kind == "string":
            return ("text", text[1:-1])
        if kind == "reference":
            return self._reference(text)
        if kind == "function":
            return self._call(text)
        if kind == "operator" and text == "(":
            inner = self._comparison()
            if self._take_operator((")",)) is None:
                raise FormulaError("missing )")
            return inner
        raise FormulaError(f"unexpected {text!r}")

    def _reference(self, text: str) -> tuple:
        """
        Build a reference or range node from reference text.

        :param text: Reference text such as ``Revenue!D7`` or ``D5:M5``
        :returns: A ``reference`` or ``range`` node
        """
        tab_name = self._tab_name
        if "!" in text:
            sheet, text = text.rsplit("!", 1)
            tab_name = sheet.strip("'")
        if ":" in text:
            first, last = text.split(":", 1)
            first_row, first_column = _parse_cell(first)
            last_row, last_column = _parse_cell(last)
            return (
                "range",
                tab_name,
                min(first_row, last_row),
                min(first_column, last_column),
                max(first_row, last_row),
                max(first_column, last_column),
            )
        row, column = _parse_cell(text)
        return ("reference", tab_name, row, column)

    def _call(self, name: str) -> tuple:
        """
        Parse a function call whose name has been consumed.

        :param name: Function name
        :returns: A ``call`` node
        """
        if self._take_operator(("(",)) is None:
            raise FormulaError(f"{name} needs (")
        arguments: list[tuple] = []
        if self._take_operator((")",)) is not None:
            return ("call", name.upper(), arguments)
        arguments.append(self._comparison())
        while self._take_operator((",",)) is not None:
            arguments.append(self._comparison())
        if self._take_operator((")",)) is None:
            raise FormulaError(f"{name} is missing )")
        return ("call", name.upper(), arguments)


def _dependencies(tree: tuple, cells_by_tab: dict[str, list[CellKey]]) -> set[CellKey]:
    """
    Collect the existing cells a syntax tree reads.

    :param tree: Syntax tree of a formula
    :param cells_by_tab: Every non-blank cell of the book, grouped by tab name
    :returns: Keys of the cells the formula reads
    """
    found: set[CellKey] = set()
    pending = [tree]
    while pending:
        node = pending.pop()
        kind = node[0]
        if kind == "reference":
            found.add((node[1], node[2], node[3]))
        elif kind == "range":
            _, tab_name, first_row, first_column, last_row, last_column = node
            for key in cells_by_tab.get(tab_name, ()):
                _, row, column = key
                if first_row <= row <= last_row and first_column <= column <= last_column:
                    found.add(key)
        elif kind == "call":
            pending.extend(node[2])
        elif kind == "bin":
            pending.extend(node[2:])
        elif kind in ("neg", "percent"):
            pending.append(node[1])
    return found


class _BookEvaluator:
    """Evaluates every cell of one book, dependencies first."""

    def __init__(self, book: Book) -> None:
        """
        :param book: Workbook whose formulas are evaluated
        """
        self._book = book
        self._tab_names = {name.lower(): name for name in book.tabs}
        self._results: dict[CellKey, Evaluated] = {}
        self._pending_formulas: set[CellKey] = set()

    def run(self) -> dict[CellKey, Evaluated]:
        """:returns: The evaluated value or error of every non-blank cell"""
        trees: dict[CellKey, tuple] = {}
        cells_by_tab: dict[str, list[CellKey]] = {}
        for tab in self._book.tabs.values():
            for (row, column), cell in tab.cells.items():
                key = (tab.name, row, column)
                cells_by_tab.setdefault(tab.name, []).append(key)
                if not cell.is_formula:
                    value = cell.number if cell.number is not None else cell.raw
                    self._results[key] = Evaluated(value, None)
                    continue
                try:
                    trees[key] = _Parser(cell.raw[1:], tab.name).parse()
                except FormulaError as error:
                    self._results[key] = Evaluated(None, str(error))

        self._pending_formulas = set(trees)
        dependencies = {
            key: _dependencies(tree, cells_by_tab) for key, tree in trees.items()
        }
        order, cyclic = self._order(dependencies)
        for key in order:
            if key in cyclic:
                self._results[key] = Evaluated(None, "circular reference")
                continue
            try:
                value = self._evaluate(trees[key])
            except FormulaError as error:
                self._results[key] = Evaluated(None, str(error))
            else:
                self._results[key] = Evaluated(value, None)
            self._pending_formulas.discard(key)
        return self._results

    def _order(
        self, dependencies: dict[CellKey, set[CellKey]]
    ) -> tuple[list[CellKey], set[CellKey]]:
        """
        Order the formula cells so each follows the formulas it reads.

        :param dependencies: Cells each formula cell reads
        :returns: The evaluation order and the cells that close a cycle
        """
        order: list[CellKey] = []
        cyclic: set[CellKey] = set()
        state: dict[CellKey, int] = {}
        for start in dependencies:
            if start in state:
                continue
            state[start] = 1
            stack = [(start, iter(sorted(dependencies[start])))]
            while stack:
                key, children = stack[-1]
                descended = False
                for child in children:
                    if child not in dependencies:
                        continue
                    if child not in state:
                        state[child] = 1
                        stack.append((child, iter(sorted(dependencies[child]))))
                        descended = True
                        break
                    if state[child] == 1:
                        cyclic.add(child)
                if not descended:
                    state[key] = 2
                    order.append(key)
                    stack.pop()
        return order, cyclic

    def _lookup(self, tab_name: str, row: int, column: int) -> float | str | bool | None:
        """
        Read one cell's value for a formula.

        :param tab_name: Tab the cell is on
        :param row: Zero-based row
        :param column: Zero-based column
        :returns: The value, or None for a blank cell
        """
        resolved = self._tab_names.get(tab_name.lower())
        if resolved is None:
            raise FormulaError(f"unknown tab {tab_name}")
        key = (resolved, row, column)
        label = f"{resolved}!{cell_label(row, column)}"
        if key in self._results:
            result = self._results[key]
            if result.error is not None:
                raise FormulaError(f"depends on {label}, which has an error")
            return result.value
        if key in self._pending_formulas:
            raise FormulaError(f"circular reference through {label}")
        return None

    def _grid(self, node: tuple) -> tuple[list[float | str | bool | None], tuple[int, int]]:
        """
        Read the values of a range or single reference.

        :param node: A ``range`` or ``reference`` node
        :returns: Values in row order and the range's row and column counts
        """
        if node[0] == "reference":
            return [self._lookup(node[1], node[2], node[3])], (1, 1)
        _, tab_name, first_row, first_column, last_row, last_column = node
        values = [
            self._lookup(tab_name, row, column)
            for row in range(first_row, last_row + 1)
            for column in range(first_column, last_column + 1)
        ]
        return values, (last_row - first_row + 1, last_column - first_column + 1)

    def _number(self, node: tuple) -> float:
        """
        Evaluate a node that must be a number.

        :param node: Syntax tree node
        :returns: Its numeric value, with a blank cell as 0 and a boolean as 0 or 1
        """
        value = self._evaluate(node)
        if value is None:
            return 0.0
        if isinstance(value, str):
            raise FormulaError(f"text {value!r} used as a number")
        return float(value)

    def _evaluate(self, node: tuple) -> float | str | bool | None:
        """
        Evaluate a syntax tree.

        :param node: Syntax tree node
        :returns: The node's value
        """
        kind = node[0]
        if kind in ("number", "text"):
            return node[1]
        if kind == "reference":
            return self._lookup(node[1], node[2], node[3])
        if kind == "range":
            raise FormulaError("a range can only be used inside a function")
        if kind == "neg":
            return -self._number(node[1])
        if kind == "percent":
            return self._number(node[1]) / 100
        if kind == "bin":
            return self._binary(node[1], node[2], node[3])
        return self._call(node[1], node[2])

    def _binary(self, operator: str, left_node: tuple, right_node: tuple) -> float | bool:
        """
        Evaluate an operator applied to two operands.

        :param operator: One of the arithmetic or comparison operators
        :param left_node: Left operand
        :param right_node: Right operand
        :returns: The number or comparison result
        """
        if operator in COMPARISONS:
            left = self._evaluate(left_node)
            right = self._evaluate(right_node)
            if isinstance(left, str) != isinstance(right, str):
                raise FormulaError("compares text with a number")
            left = 0.0 if left is None else left
            right = 0.0 if right is None else right
            return {
                "=": left == right,
                "<>": left != right,
                "<": left < right,
                ">": left > right,
                "<=": left <= right,
                ">=": left >= right,
            }[operator]

        left = self._number(left_node)
        right = self._number(right_node)
        try:
            if operator == "+":
                result = left + right
            elif operator == "-":
                result = left - right
            elif operator == "*":
                result = left * right
            elif operator == "/":
                result = left / right
            else:
                result = math.pow(left, right)
        except ZeroDivisionError as error:
            raise FormulaError("division by zero") from error
        except (ValueError, OverflowError) as error:
            raise FormulaError(f"invalid power {left} ^ {right}") from error
        if not math.isfinite(result):
            raise FormulaError("result is too large")
        return result

    def _numbers_in(self, arguments: list[tuple]) -> list[float]:
        """
        Gather the numbers a summarizing function reads.

        A range contributes only its numeric cells; a single argument must be
        a number.

        :param arguments: Argument nodes
        :returns: The numbers found
        """
        numbers: list[float] = []
        for argument in arguments:
            if argument[0] == "range":
                values, _ = self._grid(argument)
                numbers.extend(
                    value
                    for value in values
                    if isinstance(value, float) and not isinstance(value, bool)
                )
            else:
                numbers.append(self._number(argument))
        return numbers

    def _call(self, name: str, arguments: list[tuple]) -> float | bool:
        """
        Evaluate a function call.

        :param name: Upper-case function name
        :param arguments: Argument nodes
        :returns: The function's result
        """
        if name == "IF":
            if len(arguments) not in (2, 3):
                raise FormulaError("IF needs two or three arguments")
            condition = self._evaluate(arguments[0])
            if isinstance(condition, str):
                raise FormulaError("IF condition is text")
            if condition:
                return self._number_or_bool(arguments[1])
            if len(arguments) == 3:
                return self._number_or_bool(arguments[2])
            return False
        if name == "SUM":
            return sum(self._numbers_in(arguments))
        if name == "MIN":
            numbers = self._numbers_in(arguments)
            return min(numbers) if numbers else 0.0
        if name == "MAX":
            numbers = self._numbers_in(arguments)
            return max(numbers) if numbers else 0.0
        if name == "AVERAGE":
            numbers = self._numbers_in(arguments)
            if not numbers:
                raise FormulaError("AVERAGE has no numbers")
            return sum(numbers) / len(numbers)
        if name == "ABS":
            if len(arguments) != 1:
                raise FormulaError("ABS needs one argument")
            return abs(self._number(arguments[0]))
        if name == "ROUND":
            if len(arguments) != 2:
                raise FormulaError("ROUND needs two arguments")
            return _round_half_away(
                self._number(arguments[0]), int(self._number(arguments[1]))
            )
        if name == "SUMPRODUCT":
            return self._sum_product(arguments)
        raise FormulaError(f"unsupported function {name}")

    def _number_or_bool(self, node: tuple) -> float | bool:
        """
        Evaluate an IF branch.

        :param node: Branch node
        :returns: The branch's number or boolean
        """
        value = self._evaluate(node)
        if isinstance(value, str):
            raise FormulaError("IF returns text")
        return 0.0 if value is None else value

    def _sum_product(self, arguments: list[tuple]) -> float:
        """
        Evaluate SUMPRODUCT over ranges of the same shape.

        :param arguments: Range or reference nodes
        :returns: Sum of the products of corresponding cells, text counted as 0
        """
        if not arguments:
            raise FormulaError("SUMPRODUCT needs a range")
        grids = []
        shape = None
        for argument in arguments:
            if argument[0] not in ("range", "reference"):
                raise FormulaError("SUMPRODUCT needs ranges")
            values, grid_shape = self._grid(argument)
            if shape is not None and grid_shape != shape:
                raise FormulaError("SUMPRODUCT ranges differ in size")
            shape = grid_shape
            grids.append(values)
        total = 0.0
        for values in zip(*grids):
            product = 1.0
            for value in values:
                numeric = isinstance(value, float) and not isinstance(value, bool)
                product *= value if numeric else 0.0
            total += product
        return total


def _round_half_away(value: float, digits: int) -> float:
    """
    Round the way a spreadsheet does, with halves moving away from zero.

    :param value: Number to round
    :param digits: Decimal places, which may be negative
    :returns: The rounded number
    """
    factor = 10.0**digits
    rounded = math.floor(abs(value) * factor + 0.5) / factor
    return math.copysign(rounded, value) if rounded else 0.0


def evaluate_book(book: Book) -> dict[CellKey, Evaluated]:
    """
    Evaluate every cell of a workbook.

    A formula that cannot be parsed or evaluated gets an error and no value,
    and so does every formula that reads it.

    :param book: Workbook to evaluate
    :returns: Each non-blank cell's evaluated value or error, by tab, row and column
    """
    return _BookEvaluator(book).run()


def _tab_sort_key(name: str) -> tuple[int, str]:
    """
    Order tabs as the design lists them, with unknown tabs last.

    :param name: Tab name
    :returns: Sort key
    """
    if name in TAB_ORDER:
        return TAB_ORDER.index(name), name
    return len(TAB_ORDER), name


def _cell_xml(
    row: int, column: int, cell: Cell, result: Evaluated
) -> str:
    """
    Write one cell as spreadsheet XML.

    :param row: Zero-based row
    :param column: Zero-based column
    :param cell: The cell as written
    :param result: The cell's evaluated value or error
    :returns: The ``c`` element
    """
    reference = cell_label(row, column)
    if cell.is_formula:
        formula = escape(XML_ILLEGAL.sub("", cell.raw[1:]))
        value = result.value
        if result.error is not None or value is None:
            return f'<c r="{reference}"><f>{formula}</f></c>'
        if isinstance(value, bool):
            return f'<c r="{reference}" t="b"><f>{formula}</f><v>{int(value)}</v></c>'
        if isinstance(value, str):
            return (
                f'<c r="{reference}" t="str"><f>{formula}</f>'
                f"<v>{escape(XML_ILLEGAL.sub('', value))}</v></c>"
            )
        return f'<c r="{reference}"><f>{formula}</f><v>{value!r}</v></c>'
    if cell.number is not None:
        return f'<c r="{reference}"><v>{cell.number!r}</v></c>'
    text = escape(XML_ILLEGAL.sub("", cell.raw))
    return (
        f'<c r="{reference}" t="inlineStr"><is>'
        f'<t xml:space="preserve">{text}</t></is></c>'
    )


def _sheet_xml(tab: Tab, results: dict[CellKey, Evaluated]) -> str:
    """
    Write one tab as worksheet XML.

    :param tab: Tab to write
    :param results: Evaluated cells of the whole book
    :returns: The worksheet part
    """
    rows: dict[int, list[tuple[int, Cell]]] = {}
    for (row, column), cell in tab.cells.items():
        rows.setdefault(row, []).append((column, cell))

    row_xml = []
    for row in sorted(rows):
        cells = "".join(
            _cell_xml(row, column, cell, results[(tab.name, row, column)])
            for column, cell in sorted(rows[row], key=lambda item: item[0])
        )
        row_xml.append(f'<row r="{row + 1}">{cells}</row>')
    return (
        XML_HEADER
        + f'<worksheet xmlns="{SPREADSHEET_NAMESPACE}">'
        '<cols><col min="1" max="1" width="40" customWidth="1"/>'
        '<col min="2" max="2" width="28" customWidth="1"/></cols>'
        f"<sheetData>{''.join(row_xml)}</sheetData></worksheet>"
    )


def write_xlsx(path: Path, book: Book, results: dict[CellKey, Evaluated]) -> None:
    """
    Write a workbook as an ``.xlsx`` file.

    Each formula is stored with its evaluated value when it has one, and the
    file asks the spreadsheet program to recalculate on opening.

    :param path: File to write
    :param book: Workbook to write
    :param results: The book's evaluated cells
    """
    names = sorted(book.tabs, key=_tab_sort_key)
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{number}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.worksheet+xml"/>'
        for number in range(1, len(names) + 1)
    )
    content_types = (
        XML_HEADER
        + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
        'package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{overrides}</Types>"
    )
    root_relationships = (
        XML_HEADER
        + f'<Relationships xmlns="{PACKAGE_RELATIONSHIP_NAMESPACE}">'
        f'<Relationship Id="rId1" Type="{RELATIONSHIP_NAMESPACE}/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{number}" r:id="rId{number}"/>'
        for number, name in enumerate(names, start=1)
    )
    workbook = (
        XML_HEADER
        + f'<workbook xmlns="{SPREADSHEET_NAMESPACE}" '
        f'xmlns:r="{RELATIONSHIP_NAMESPACE}">'
        f'<sheets>{sheets}</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/>'
        "</workbook>"
    )
    sheet_relationships = "".join(
        f'<Relationship Id="rId{number}" Type="{RELATIONSHIP_NAMESPACE}/worksheet" '
        f'Target="worksheets/sheet{number}.xml"/>'
        for number in range(1, len(names) + 1)
    )
    workbook_relationships = (
        XML_HEADER
        + f'<Relationships xmlns="{PACKAGE_RELATIONSHIP_NAMESPACE}">'
        f"{sheet_relationships}"
        f'<Relationship Id="rId{len(names) + 1}" '
        f'Type="{RELATIONSHIP_NAMESPACE}/styles" Target="styles.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_relationships)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_relationships)
        archive.writestr("xl/styles.xml", STYLES_XML)
        for number, name in enumerate(names, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{number}.xml", _sheet_xml(book.tabs[name], results)
            )


def _error_problems(book: Book, results: dict[CellKey, Evaluated]) -> list[str]:
    """
    List the formulas that could not be evaluated, root causes first.

    :param book: Workbook the results belong to
    :param results: The book's evaluated cells
    :returns: One line per formula with its own error, then a count of the
        formulas that only read an error
    """
    problems: list[str] = []
    dependent = 0
    for key in sorted(results):
        result = results[key]
        if result.error is None:
            continue
        if result.error.startswith(("depends on", "circular reference through")):
            dependent += 1
            continue
        tab_name, row, column = key
        problems.append(
            f"{book.name}/{tab_name}!{cell_label(row, column)}: {result.error}"
        )
    if dependent:
        problems.append(
            f"{book.name}: {dependent} further formulas read a cell with an error"
        )
    return problems


def pack_workbooks(model_dir: Path) -> list[str]:
    """
    Pack every workbook directory into an ``.xlsx`` file.

    Packed files with no tab files left to pack are removed. A problem is
    reported and never raised: the affected cell is left without a value.

    :param model_dir: Directory holding one subdirectory of tab files per workbook
    :returns: One line per problem found, empty when everything packed cleanly
    """
    books, problems = load_books(model_dir)
    for book in books:
        results = evaluate_book(book)
        problems.extend(_error_problems(book, results))
        write_xlsx(model_dir / f"{book.name}.xlsx", book, results)

    if model_dir.is_dir():
        current = {book.name for book in books}
        for packed in model_dir.glob("*.xlsx"):
            if packed.stem not in current:
                packed.unlink()
    return problems


def _format_value(result: Evaluated | None) -> str:
    """
    Show an evaluated cell as text.

    :param result: The cell's evaluation, or None for a blank cell
    :returns: Text for the cell, with an error marked
    """
    if result is None:
        return ""
    if result.error is not None:
        return f"#ERROR ({result.error})"
    value = result.value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return "0" if text in ("", "-0") else text
    return "" if value is None else str(value)


def render_workbooks(model_dir: Path) -> str:
    """
    Show every workbook's evaluated tabs as text for a prompt.

    :param model_dir: Directory holding one subdirectory of tab files per workbook
    :returns: One fenced tab-separated block per tab, or an empty string when
        there are no workbooks
    """
    books, _ = load_books(model_dir)
    blocks: list[str] = []
    for book in sorted(books, key=lambda item: (item.name != COMPANY_BOOK, item.name)):
        results = evaluate_book(book)
        for name in sorted(book.tabs, key=_tab_sort_key):
            tab = book.tabs[name]
            if not tab.cells:
                continue
            last_row = max(row for row, _ in tab.cells)
            last_column = max(column for _, column in tab.cells)
            lines = [
                "\t".join(
                    _format_value(results.get((name, row, column)))
                    for column in range(last_column + 1)
                ).rstrip("\t")
                for row in range(last_row + 1)
            ]
            blocks.append(f"### {book.name} / {name}\n\n```tsv\n" + "\n".join(lines) + "\n```")
    return "\n\n".join(blocks)


def _label_rows(tab: Tab) -> dict[str, int]:
    """
    Index a tab's rows by the text in column A.

    :param tab: Tab to index
    :returns: Row number by label, keeping the first row for a repeated label
    """
    rows: dict[str, int] = {}
    for (row, column), cell in sorted(tab.cells.items()):
        if column == 0 and cell.number is None and not cell.is_formula:
            rows.setdefault(cell.raw, row)
    return rows


def _result_number(
    results: dict[CellKey, Evaluated], tab_name: str, row: int, column: int
) -> float | None:
    """
    Read a numeric result.

    :param results: Evaluated cells of a book
    :param tab_name: Tab the cell is on
    :param row: Zero-based row
    :param column: Zero-based column
    :returns: The number, or None when the cell is blank, text or an error
    """
    result = results.get((tab_name, row, column))
    if result is None or result.error is not None:
        return None
    if isinstance(result.value, float) and not isinstance(result.value, bool):
        return result.value
    return None


def check_model(model_dir: Path) -> CheckReport:
    """
    Report facts about a finished run's workbooks without changing anything.

    The facts are packing problems, tabs missing from the expected set,
    ``Check`` rows that are not 0, outcome ``Inputs`` values that differ from
    the company row with the same label, and each outcome's per-share value.

    :param model_dir: Directory holding one subdirectory of tab files per workbook
    :returns: The findings and each outcome's per-share value by workbook name
    """
    books, findings = load_books(model_dir)
    values: dict[str, float | None] = {}
    evaluated = {book.name: evaluate_book(book) for book in books}
    company = next((book for book in books if book.name == COMPANY_BOOK), None)

    company_inputs: dict[str, float] = {}
    if company is not None and "Inputs" in company.tabs:
        for label, row in _label_rows(company.tabs["Inputs"]).items():
            number = _result_number(evaluated[COMPANY_BOOK], "Inputs", row, 2)
            if number is not None:
                company_inputs[label] = number

    for book in books:
        results = evaluated[book.name]
        findings.extend(_error_problems(book, results))

        if not book.name.endswith(RETIRED_SUFFIX):
            if book.name == COMPANY_BOOK:
                expected = ("Inputs",)
            elif "Recovery" in book.tabs:
                expected = EVENT_TABS
            else:
                expected = GOING_CONCERN_TABS
            missing = [name for name in expected if name not in book.tabs]
            if missing:
                findings.append(f"{book.name}: missing tabs {', '.join(missing)}")

        for name, tab in book.tabs.items():
            check_rows = {
                row: cell.raw
                for (row, column), cell in tab.cells.items()
                if column == 0
                and cell.number is None
                and not cell.is_formula
                and cell.raw.startswith("Check")
            }
            for (row, column) in sorted(tab.cells):
                if row not in check_rows or column < 2:
                    continue
                number = _result_number(results, name, row, column)
                if number is None or abs(number) > CHECK_TOLERANCE:
                    findings.append(
                        f"{book.name}/{name}!{cell_label(row, column)}: "
                        f"{check_rows[row]} is not 0"
                    )

        if book.name != COMPANY_BOOK and "Inputs" in book.tabs:
            for label, row in _label_rows(book.tabs["Inputs"]).items():
                number = _result_number(results, "Inputs", row, 2)
                expected_value = company_inputs.get(label)
                if number is None or expected_value is None:
                    continue
                if not math.isclose(number, expected_value, rel_tol=1e-9, abs_tol=1e-9):
                    findings.append(
                        f"{book.name}/Inputs!C{row + 1}: {label} is {number} "
                        f"but the company workbook has {expected_value}"
                    )

        if book.name != COMPANY_BOOK:
            values[book.name] = None
            for name in VALUE_TABS:
                if name not in book.tabs:
                    continue
                row = _label_rows(book.tabs[name]).get(VALUE_LABEL)
                if row is not None:
                    values[book.name] = _result_number(results, name, row, 2)
            if values[book.name] is None:
                findings.append(f"{book.name}: no numeric '{VALUE_LABEL}' in column C")
    return CheckReport(findings, values)


def run_check(argv: list[str] | None = None) -> int:
    """
    Print the check report for each run directory or model directory given.

    :param argv: Paths to check, defaulting to ``sys.argv[1:]``
    :returns: 0 when every path has no findings, otherwise 1
    """
    paths = [Path(argument) for argument in (sys.argv[1:] if argv is None else argv)]
    failed = False
    for path in paths:
        model_dir = path / "model" if (path / "model").is_dir() else path
        label = model_dir.parent.name if model_dir.name == "model" else model_dir.name
        report = check_model(model_dir)
        print(f"{'FAIL' if report.findings else 'PASS'}: {label}")
        for finding in report.findings:
            print(f"  {finding}")
        for name, value in report.values.items():
            print(f"  {name}: fair value per share {value}")
        failed = failed or bool(report.findings)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_check())
