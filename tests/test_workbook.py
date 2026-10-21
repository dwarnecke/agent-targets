__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from agent_targets.workbook import (
    check_model,
    evaluate_book,
    load_books,
    pack_workbooks,
    parse_tab,
    render_workbooks,
    run_check,
)

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _write_tabs(model_dir: Path, files: dict[str, str]) -> None:
    """
    Write tab files under a model directory.

    :param model_dir: Directory holding one subdirectory per workbook
    :param files: Tab file text by path such as ``O1/Revenue.tsv``
    """
    for relative_path, text in files.items():
        path = model_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _evaluate(tmp_path: Path, rows: list[list[str]]) -> dict[str, float | str | bool | None]:
    """
    Evaluate one tab and read its cells back by label.

    :param tmp_path: Directory used for the model directory
    :param rows: Rows of the single tab ``Calc``, each a list of cell texts
    :returns: Each cell's value keyed by label such as ``B2``, formulas in error as None
    """
    text = "\n".join("\t".join(row) for row in rows) + "\n"
    _write_tabs(tmp_path, {"B/Calc.tsv": text})
    books, _ = load_books(tmp_path)
    results = evaluate_book(books[0])
    return {
        f"{chr(ord('A') + column)}{row + 1}": result.value
        for (_, row, column), result in results.items()
    }


def _error(tmp_path: Path, formula: str) -> str | None:
    """
    Evaluate one formula and return its error.

    :param tmp_path: Directory used for the model directory
    :param formula: Formula text beginning with ``=``
    :returns: The error text, or None when the formula evaluates
    """
    _write_tabs(tmp_path, {"B/Calc.tsv": f"1\t2\t{formula}\n"})
    books, _ = load_books(tmp_path)
    return evaluate_book(books[0])[("Calc", 0, 2)].error


def test_parse_tab_reads_numbers_text_and_formulas() -> None:
    """A cell is a number, text or a formula, and blank cells are omitted."""
    tab = parse_tab("Calc", "Item\t1.5\t=A1\n\t-2e3\n$1,200\t5%\n")

    assert tab.cells[(0, 0)].number is None and not tab.cells[(0, 0)].is_formula
    assert tab.cells[(0, 1)].number == 1.5
    assert tab.cells[(0, 2)].is_formula
    assert (1, 0) not in tab.cells
    assert tab.cells[(1, 1)].number == -2000.0
    assert tab.cells[(2, 0)].number is None and tab.cells[(2, 1)].number is None


def test_a_utf16_tab_file_from_powershell_is_read(tmp_path: Path) -> None:
    """
    PowerShell's default redirection writes UTF-16 and still loads.

    :param tmp_path: Directory used for the model directory
    """
    path = tmp_path / "B" / "Calc.tsv"
    path.parent.mkdir()
    path.write_bytes("Item\t7\n".encode("utf-16"))

    books, problems = load_books(tmp_path)

    assert problems == []
    assert books[0].tabs["Calc"].cells[(0, 1)].number == 7.0


def test_operators_follow_spreadsheet_precedence(tmp_path: Path) -> None:
    """
    Negation binds tighter than powers, powers group left to right, and percent divides.

    :param tmp_path: Directory used for the model directory
    """
    values = _evaluate(
        tmp_path,
        [
            ["=-2^2", "=2^3^2", "=2+3*4", "=(2+3)*4", "=50%", "=10-4-3", "=2*3/4"],
        ],
    )

    assert [values[f"{column}1"] for column in "ABCDEFG"] == [
        4.0,
        64.0,
        14.0,
        20.0,
        0.5,
        3.0,
        1.5,
    ]


def test_functions_ranges_and_comparisons(tmp_path: Path) -> None:
    """
    Range functions skip text and blanks, and IF picks the branch.

    :param tmp_path: Directory used for the model directory
    """
    values = _evaluate(
        tmp_path,
        [
            ["1", "2", "label", "", "4"],
            [
                "=SUM(A1:E1)",
                "=MIN(A1:E1)",
                "=MAX(A1:E1)",
                "=AVERAGE(A1:E1)",
                "=ABS(-3)",
                "=SUMPRODUCT(A1:B1,A1:B1)",
            ],
            ["=IF(A1<B1,10,20)", "=IF(A1>=B1,10,20)", "=IF(A1=1,1)", "=IF(A1<>1,1,2)"],
        ],
    )

    assert [values[f"{column}2"] for column in "ABCDEF"] == [
        7.0,
        1.0,
        4.0,
        7 / 3,
        3.0,
        5.0,
    ]
    assert [values[f"{column}3"] for column in "ABCD"] == [10.0, 20.0, 1.0, 2.0]


def test_round_moves_halves_away_from_zero(tmp_path: Path) -> None:
    """
    ROUND follows the spreadsheet rule, not banker's rounding.

    :param tmp_path: Directory used for the model directory
    """
    values = _evaluate(
        tmp_path, [["=ROUND(2.5,0)", "=ROUND(-2.5,0)", "=ROUND(1.005*1000,0)", "=ROUND(1234,-2)"]]
    )

    assert [values[f"{column}1"] for column in "ABCD"] == [3.0, -3.0, 1005.0, 1200.0]


def test_references_cross_tabs_and_forward_cells(tmp_path: Path) -> None:
    """
    A formula can read a later cell, another tab and a quoted tab name.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(
        tmp_path,
        {
            "B/Inputs.tsv": "Rate\t\t0.1\n",
            "B/Net income.tsv": "Item\t\t=Inputs!C1*10\n",
            "B/Value.tsv": "Fair value per share\t\t='Net income'!C1+$C$2\nlater\t\t4\n",
        },
    )
    books, _ = load_books(tmp_path)

    results = evaluate_book(books[0])

    assert results[("Value", 0, 2)].value == pytest.approx(5.0)


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("=1/0", "division by zero"),
        ("=A1+D1", "text 'word' used as a number"),
        ("=NOPE(1)", "unsupported function NOPE"),
        ("=Missing!A1", "unknown tab Missing"),
        ("=A1+", "formula ends early"),
        ("=((1)", "missing )"),
        ("=1 2", "unexpected '2'"),
        ("=(-8)^0.5", "invalid power -8.0 ^ 0.5"),
        ("=A1:B1", "a range can only be used inside a function"),
        ("=", "empty formula"),
    ],
)
def test_a_formula_that_cannot_be_evaluated_reports_why(
    tmp_path: Path, formula: str, expected: str
) -> None:
    """
    Each failure has a reason and leaves the cell without a value.

    :param tmp_path: Directory used for the model directory
    :param formula: Formula under test
    :param expected: Error text the formula must report
    """
    _write_tabs(tmp_path, {"B/Calc.tsv": f"1\t2\t{formula}\tword\n"})
    books, _ = load_books(tmp_path)

    result = evaluate_book(books[0])[("Calc", 0, 2)]

    assert result.value is None
    assert result.error == expected


def test_circular_references_are_errors_and_dependents_follow(tmp_path: Path) -> None:
    """
    A cycle fails its cells, and a formula that reads them fails too.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(tmp_path, {"B/Calc.tsv": "=B1\t=A1\t=A1+1\t=D1\n"})
    books, _ = load_books(tmp_path)

    results = evaluate_book(books[0])

    assert results[("Calc", 0, 0)].error == "circular reference"
    assert results[("Calc", 0, 1)].error is not None
    assert results[("Calc", 0, 2)].error.startswith("depends on Calc!A1")
    assert results[("Calc", 0, 3)].error == "circular reference"


def test_a_long_dependency_chain_does_not_exhaust_the_stack(tmp_path: Path) -> None:
    """
    Evaluation order is computed without recursion.

    :param tmp_path: Directory used for the model directory
    """
    rows = ["1"] + [f"=A{row}+1" for row in range(1, 3000)]
    _write_tabs(tmp_path, {"B/Calc.tsv": "\n".join(rows) + "\n"})
    books, _ = load_books(tmp_path)

    results = evaluate_book(books[0])

    assert results[("Calc", 2999, 0)].value == 3000.0


def test_pack_writes_a_valid_xlsx_with_formulas_and_their_values(tmp_path: Path) -> None:
    """
    The file is a zip of well-formed XML holding formulas, values and text.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(
        tmp_path,
        {
            "O1/Tests.tsv": "Rule\tpass\n",
            "O1/Value.tsv": "Item\tUnit\tOpening\nFair value per share\t\t=2+3\nBad\t\t=1/0\n",
            "O1/Inputs.tsv": "r\t\t0.0875\n",
            "O1/Custom.tsv": "x\n",
        },
    )

    problems = pack_workbooks(tmp_path)

    with zipfile.ZipFile(tmp_path / "O1.xlsx") as archive:
        names = archive.namelist()
        parts = {name: ElementTree.fromstring(archive.read(name)) for name in names}
    assert "xl/workbook.xml" in names and "[Content_Types].xml" in names
    sheets = [sheet.get("name") for sheet in parts["xl/workbook.xml"].iter(f"{MAIN}sheet")]
    assert sheets == ["Inputs", "Value", "Tests", "Custom"]
    value_cells = {
        cell.get("r"): cell for cell in parts["xl/worksheets/sheet2.xml"].iter(f"{MAIN}c")
    }
    assert value_cells["C2"].find(f"{MAIN}f").text == "2+3"
    assert value_cells["C2"].find(f"{MAIN}v").text == "5.0"
    assert value_cells["C3"].find(f"{MAIN}f").text == "1/0"
    assert value_cells["C3"].find(f"{MAIN}v") is None
    assert value_cells["A2"].get("t") == "inlineStr"
    assert problems == ["O1/Value!C3: division by zero"]


def test_pack_reports_unusable_names_and_files_without_raising(tmp_path: Path) -> None:
    """
    A bad directory, a bad tab name and an unreadable file are reported and skipped.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(
        tmp_path,
        {
            "bad name/Value.tsv": "1\n",
            "O1/Bad.name.tsv": "1\n",
            "O1/Value.tsv": "1\n",
        },
    )
    (tmp_path / "O1" / "Broken.tsv").write_bytes(b"\xff\xfe\x00")
    (tmp_path / "notes.md").write_text("not a workbook", encoding="utf-8")

    problems = pack_workbooks(tmp_path)

    assert (tmp_path / "O1.xlsx").is_file()
    assert any(line.startswith("bad name:") for line in problems)
    assert any("O1/Bad.name.tsv: tab name" in line for line in problems)
    assert any("O1/Broken.tsv: unreadable" in line for line in problems)
    assert (tmp_path / "notes.md").is_file()


def test_pack_removes_a_workbook_whose_tab_files_are_gone(tmp_path: Path) -> None:
    """
    Packed files follow their tab files.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(tmp_path, {"O1/Value.tsv": "1\n", "O2/Value.tsv": "2\n"})
    pack_workbooks(tmp_path)
    (tmp_path / "O2" / "Value.tsv").unlink()

    pack_workbooks(tmp_path)

    assert (tmp_path / "O1.xlsx").is_file()
    assert not (tmp_path / "O2.xlsx").exists()


def test_pack_summarizes_formulas_that_only_read_an_error(tmp_path: Path) -> None:
    """
    One root cause is listed once, with a count of what depends on it.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(tmp_path, {"O1/Value.tsv": "=1/0\n=A1+1\n=A2+1\n"})

    problems = pack_workbooks(tmp_path)

    assert problems == [
        "O1/Value!A1: division by zero",
        "O1: 2 further formulas read a cell with an error",
    ]


def test_render_shows_evaluated_tabs_company_first(tmp_path: Path) -> None:
    """
    The prompt text lists the company tab first and formats values and errors.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(
        tmp_path,
        {
            "O1/Value.tsv": "Fair value per share\t\t=1/3\nBad\t\t=1/0\ntext\t=1=1\n",
            "company/Inputs.tsv": "r\t\t0.0875\n",
        },
    )

    text = render_workbooks(tmp_path)

    assert text.index("### company / Inputs") < text.index("### O1 / Value")
    assert "r\t\t0.0875" in text
    assert "Fair value per share\t\t0.333333" in text
    assert "Bad\t\t#ERROR (division by zero)" in text
    assert "text\tTRUE" in text
    assert render_workbooks(tmp_path / "missing") == ""


def _outcome(value: str, extra: str = "") -> dict[str, str]:
    """
    Build the tab files of a minimal going-concern outcome.

    :param value: Formula or number for the per-share value
    :param extra: Extra text for the outcome's ``Inputs`` tab
    :returns: Tab file text by path under the ``O1`` directory
    """
    header = "Item\tUnit\tOpening\tP1\tP2\n"
    return {
        "O1/Inputs.tsv": "Shares\t\t100\n" + extra,
        "O1/Revenue.tsv": header,
        "O1/Income.tsv": header,
        "O1/Balance.tsv": header + "Check balance\t\t0\t0\t0\n",
        "O1/CashFlow.tsv": header,
        "O1/Value.tsv": header + f"Fair value per share\t\t{value}\n",
        "O1/Tests.tsv": "Rule\tpass\n",
    }


def test_check_model_passes_a_consistent_run(tmp_path: Path) -> None:
    """
    A complete outcome with zero check rows and a value has no findings.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(tmp_path, {"company/Inputs.tsv": "Shares\t\t100\n", **_outcome("=12.5*2")})

    report = check_model(tmp_path)

    assert report.findings == []
    assert report.values == {"O1": 25.0}


def test_check_model_reports_facts_without_changing_anything(tmp_path: Path) -> None:
    """
    It flags a check row, an inputs difference, missing tabs and a missing value.

    :param tmp_path: Directory used for the model directory
    """
    files = _outcome("=1/0", extra="Hurdle\t\t0.1\n")
    files["O1/Balance.tsv"] += "Check cash\t\t0\t0.5\t=1/0\n"
    del files["O1/Tests.tsv"]
    files["company/Inputs.tsv"] = "Shares\t\t90\nHurdle\t\t0.1\n"
    files["O2-retired/Value.tsv"] = "Item\nFair value per share\t\t7\n"
    _write_tabs(tmp_path, files)
    before = sorted(path.name for path in tmp_path.rglob("*"))

    report = check_model(tmp_path)

    assert "O1/Balance!D3: Check cash is not 0" in report.findings
    assert "O1/Balance!E3: Check cash is not 0" in report.findings
    assert "O1/Inputs!C1: Shares is 100.0 but the company workbook has 90.0" in report.findings
    assert "O1: missing tabs Tests" in report.findings
    assert "O1: no numeric 'Fair value per share' in column C" in report.findings
    assert not any(finding.startswith("O2-retired: missing") for finding in report.findings)
    assert report.values["O2-retired"] == 7.0
    assert sorted(path.name for path in tmp_path.rglob("*")) == before


def test_an_event_outcome_is_checked_against_its_own_tabs(tmp_path: Path) -> None:
    """
    A workbook with a Recovery tab needs Inputs, Recovery and Tests only.

    :param tmp_path: Directory used for the model directory
    """
    _write_tabs(
        tmp_path,
        {
            "O4/Inputs.tsv": "Shares\t\t100\n",
            "O4/Recovery.tsv": "Fair value per share\t\t0\n",
            "O4/Tests.tsv": "Rule\tpass\n",
        },
    )

    report = check_model(tmp_path)

    assert report.findings == []
    assert report.values == {"O4": 0.0}


def test_run_check_prints_pass_or_fail_and_returns_an_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    The command accepts a run directory and fails when there are findings.

    :param tmp_path: Directory used for the model directory
    :param capsys: Fixture capturing printed output
    """
    good = tmp_path / "GOOD-run"
    bad = tmp_path / "BAD-run"
    _write_tabs(good / "model", _outcome("=2"))
    _write_tabs(bad / "model", {"O1/Value.tsv": "Item\n"})

    assert run_check([str(good)]) == 0
    assert run_check([str(good), str(bad)]) == 1

    output = capsys.readouterr().out
    assert "PASS: GOOD-run" in output
    assert "FAIL: BAD-run" in output
    assert "O1: fair value per share 2.0" in output
