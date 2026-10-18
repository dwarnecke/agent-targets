__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import json
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

import pytest

from agent_targets.sources import (
    ERP_URL,
    QUOTE_URL,
    SECURITY_URL,
    TREASURY_URL,
    SourceError,
    build_initiation_record,
    fetch_url,
    parse_erp,
    parse_quote,
    parse_security,
    parse_treasury,
)

NOW = datetime(2026, 10, 14, 23, 20, tzinfo=timezone.utc)
SESSION_START = 1791984600
SESSION_END = 1792008000
DAY_SECONDS = 86400


def _security_list() -> bytes:
    """:returns: A small SEC ticker list in the published layout"""
    return json.dumps(
        {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [
                [1652044, "Alphabet Inc.", "GOOGL", "Nasdaq"],
                [104169, "Walmart Inc.", "WMT", "Nasdaq"],
            ],
        }
    ).encode()


def _quote(
    market_time: int = SESSION_END,
    currency: str = "USD",
    symbol: str = "WMT",
) -> bytes:
    """
    Build chart data with a closed session on the 13th and one on the 14th.

    :param market_time: Time of the latest trade
    :param currency: Currency of the chart
    :param symbol: Symbol the chart describes
    :returns: Yahoo chart API body
    """
    chart = {
        "meta": {
            "currency": currency,
            "symbol": symbol,
            "regularMarketTime": market_time,
            "gmtoffset": -14400,
            "timezone": "EDT",
            "exchangeTimezoneName": "America/New_York",
            "priceHint": 2,
            "currentTradingPeriod": {
                "regular": {"start": SESSION_START, "end": SESSION_END}
            },
        },
        "timestamp": [SESSION_START - DAY_SECONDS, SESSION_START],
        "indicators": {"quote": [{"close": [112.27999877929688, 116.16000366210938]}]},
    }
    return json.dumps({"chart": {"result": [chart]}}).encode()


def _treasury(*records: tuple[str, str | None]) -> bytes:
    """
    Build a Treasury feed whose 10-year column is not the first yield.

    :param records: Each record's date and its 10-year yield, or None when blank
    :returns: Treasury XML feed body
    """
    entries = ""
    for day, ten_year in records:
        blank = "" if ten_year is None else ten_year
        entries += (
            "<entry><content><m:properties>"
            f"<d:NEW_DATE>{day}T00:00:00</d:NEW_DATE>"
            "<d:BC_1MONTH>4.06</d:BC_1MONTH><d:BC_5YEAR>4.90</d:BC_5YEAR>"
            f"<d:BC_10YEAR>{blank}</d:BC_10YEAR><d:BC_30YEAR>5.40</d:BC_30YEAR>"
            "</m:properties></content></entry>"
        )
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" '
        'xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">'
        f"{entries}</feed>"
    ).encode()


def _erp_workbook(first_month_serial: int = 44804) -> bytes:
    """
    Build a workbook shaped like Damodaran's, with a decoy ERP column and sheet.

    Dates use the 1904 system. The payout-adjusted column is not the first ERP
    column, and a second sheet holds different numbers.

    :param first_month_serial: Date serial of the first data row; the second row
        is thirty days later
    :returns: Workbook bytes
    """
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    strings = ["Start of month", "ERP (T12m)", "ERP (T12 m with sustainable payout)"]
    header = "".join(
        f'<c r="{column}1" t="s"><v>{index}</v></c>'
        for index, column in enumerate("ABC")
    )
    rows = (
        f'<row r="1">{header}</row>'
        f'<row r="2"><c r="A2"><v>{first_month_serial}</v></c>'
        '<c r="B2"><v>4.0899999999999999E-2</v></c>'
        '<c r="C2"><v>4.1399999999999999E-2</v></c></row>'
        f'<row r="3"><c r="A3"><v>{first_month_serial + 30}</v></c>'
        '<c r="B3"><v>3.6999999999999998E-2</v></c>'
        '<c r="C3"><v>4.2000000000000003E-2</v></c></row>'
    )
    files = {
        "xl/workbook.xml": (
            f'<workbook xmlns="{main}" xmlns:r="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships"><workbookPr date1904="1"/><sheets>'
            '<sheet name="Decoy" sheetId="2" r:id="rId9"/>'
            '<sheet name="Historical ERP" sheetId="1" r:id="rId1"/>'
            "</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId9" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>'
        ),
        "xl/sharedStrings.xml": (
            f'<sst xmlns="{main}">'
            + "".join(f"<si><t>{text}</t></si>" for text in strings)
            + "</sst>"
        ),
        "xl/worksheets/sheet1.xml": (
            f'<worksheet xmlns="{main}"><sheetData>{rows}</sheetData></worksheet>'
        ),
        "xl/worksheets/sheet2.xml": (
            f'<worksheet xmlns="{main}"><sheetData><row r="1">'
            '<c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>'
        ),
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        for name, content in files.items():
            book.writestr(name, content)
    return buffer.getvalue()


def _responses(treasury_month: bytes | None = None) -> dict[str, bytes]:
    """
    Map every initiation URL to a healthy response.

    :param treasury_month: Body for the October Treasury feed, defaulting to a
        record dated the 14th
    :returns: Response body by URL
    """
    october = TREASURY_URL.format(month="202610")
    default_month = _treasury(("2026-10-13", "5.21"), ("2026-10-14", "5.19"))
    return {
        SECURITY_URL: _security_list(),
        QUOTE_URL.format(ticker="WMT"): _quote(),
        october: treasury_month or default_month,
        ERP_URL: _erp_workbook(),
    }


def _fetch_from(responses: dict[str, bytes]):
    """
    Build a fetch function that serves fixed responses.

    :param responses: Response body by URL
    :returns: Function that returns a body or raises SourceError for an unknown URL
    """

    def fetch(url: str) -> bytes:
        """
        :param url: Address requested
        :returns: The fixed response for the address
        """
        if url not in responses:
            raise SourceError(f"No response for {url}")
        return responses[url]

    return fetch


def test_security_is_found_by_ticker_ignoring_case() -> None:
    """The ticker maps to its row's name, CIK and exchange."""
    security = parse_security(_security_list(), "wmt")

    assert (security.ticker, security.legal_name) == ("WMT", "Walmart Inc.")
    assert (security.cik, security.exchange) == (104169, "Nasdaq")


def test_unknown_ticker_is_an_error() -> None:
    """A ticker missing from the SEC list raises SourceError."""
    with pytest.raises(SourceError):
        parse_security(_security_list(), "NOPE")


def test_quote_is_the_latest_completed_close_rounded_to_the_price_hint() -> None:
    """After the session ends the newest bar is the close, as a clean price."""
    quote = parse_quote(_quote(), "WMT", NOW)

    assert quote.price == Decimal("116.16")
    assert quote.session_date == date(2026, 10, 14)
    assert quote.time_zone == "America/New_York (EDT)"
    assert quote.currency == "USD"


def test_quote_drops_a_session_that_is_still_open() -> None:
    """During the regular session the newest bar is intraday and is not a close."""
    during_session = datetime.fromtimestamp(SESSION_START + 3600, timezone.utc)
    chart = _quote(market_time=SESSION_START + 3600)

    quote = parse_quote(chart, "WMT", during_session)

    assert quote.price == Decimal("112.28")
    assert quote.session_date == date(2026, 10, 13)


def test_quote_before_the_next_open_keeps_the_finished_session() -> None:
    """Pre-market after a close, the latest trade predates the new session's open."""
    next_morning = datetime.fromtimestamp(SESSION_END + 3600, timezone.utc)

    quote = parse_quote(_quote(market_time=SESSION_END), "WMT", next_morning)

    assert quote.session_date == date(2026, 10, 14)


def test_quote_rejects_another_currency_or_symbol() -> None:
    """Only a USD chart for the requested ticker is accepted."""
    with pytest.raises(SourceError):
        parse_quote(_quote(currency="EUR"), "WMT", NOW)
    with pytest.raises(SourceError):
        parse_quote(_quote(symbol="WMTX"), "WMT", NOW)


def test_treasury_reads_the_ten_year_element_by_name() -> None:
    """The 10-year yield is taken by element name and blank records are skipped."""
    observations = parse_treasury(
        _treasury(("2026-10-13", "5.21"), ("2026-10-14", None))
    )

    assert [(o.observed_on, o.percent) for o in observations] == [
        (date(2026, 10, 13), Decimal("5.21"))
    ]


def test_erp_reads_the_payout_adjusted_column_of_the_newest_month() -> None:
    """The ERP column is chosen by header, the sheet by name, with 1904 dates."""
    observation = parse_erp(_erp_workbook())

    assert observation.percent == Decimal("4.20")
    assert observation.observed_on == date(2026, 10, 1)


def test_initiation_record_states_every_fact_with_its_date() -> None:
    """The record carries the security, close and both rates with dates and ages."""
    record = build_initiation_record("wmt", _fetch_from(_responses()), NOW)

    assert "| Legal name | Walmart Inc. |" in record
    assert "| SEC CIK | 104169 |" in record
    assert "| Latest completed regular-session close | 116.16 USD |" in record
    assert "5.19 (observed 2026-10-14, 0 days before capture)" in record
    assert "4.20 (effective 2026-10-01, 13 days before capture)" in record
    assert "secondary" in record


def test_treasury_falls_back_to_last_month_when_this_month_is_empty() -> None:
    """On the first days of a month the previous month's newest record is used."""
    responses = _responses(treasury_month=_treasury())
    responses[TREASURY_URL.format(month="202609")] = _treasury(("2026-09-30", "5.00"))
    early_october = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)

    record = build_initiation_record("WMT", _fetch_from(responses), early_october)

    assert "5.00 (observed 2026-09-30, 2 days before capture)" in record


def test_stale_rates_fail_the_record() -> None:
    """A Treasury rate over 7 days old or an ERP over 45 days old raises."""
    stale_treasury = _responses(_treasury(("2026-10-06", "5.10")))
    with pytest.raises(SourceError, match="Treasury"):
        build_initiation_record("WMT", _fetch_from(stale_treasury), NOW)

    stale_erp = _responses()
    stale_erp[ERP_URL] = _erp_workbook(first_month_serial=44700)
    with pytest.raises(SourceError, match="ERP"):
        build_initiation_record("WMT", _fetch_from(stale_erp), NOW)


def test_unreadable_response_names_its_url() -> None:
    """A body that does not parse raises SourceError naming the source."""
    responses = _responses()
    responses[ERP_URL] = b"not a workbook"

    with pytest.raises(SourceError, match="pages.stern.nyu.edu"):
        build_initiation_record("WMT", _fetch_from(responses), NOW)


def test_network_failure_becomes_a_source_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A URL error from the HTTP client is translated to SourceError.

    :param monkeypatch: Pytest fixture used to make the request fail
    """

    def fail(*args: object, **kwargs: object) -> None:
        """
        :param args: Ignored positional arguments
        :param kwargs: Ignored keyword arguments
        """
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fail)

    with pytest.raises(SourceError, match="offline"):
        fetch_url(SECURITY_URL)
