__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree

USER_AGENT = "Mozilla/5.0 (compatible; agent-targets; dylan.warnecke@gmail.com)"
REQUEST_TIMEOUT_SECONDS = 30

TREASURY_MAX_AGE_DAYS = 7
ERP_MAX_AGE_DAYS = 45

SECURITY_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
QUOTE_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?range=10d&interval=1d"
)
TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"
    "/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month={month}"
)
ERP_URL = "https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx"

ERP_SHEET = "Historical ERP"
ERP_DATE_HEADER = "Start of month"
ERP_HEADER = "ERP (T12 m with sustainable payout)"

ATOM = "{http://www.w3.org/2005/Atom}"
SPREADSHEET = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOCUMENT_RELATIONSHIP = (
    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
)
PACKAGE_RELATIONSHIP = "{http://schemas.openxmlformats.org/package/2006/relationships}"

Fetch = Callable[[str], bytes]


class SourceError(Exception):
    """A required source could not be read, was unusable or was too old."""


@dataclass(frozen=True)
class Security:
    """Identity of the listed security."""

    ticker: str
    legal_name: str
    cik: int
    exchange: str


@dataclass(frozen=True)
class Quote:
    """Latest completed regular-session close."""

    price: Decimal
    session_date: date
    time_zone: str
    currency: str


@dataclass(frozen=True)
class RateObservation:
    """A published rate in percent and the date it applies to."""

    percent: Decimal
    observed_on: date


def fetch_url(url: str) -> bytes:
    """
    Download a URL.

    :param url: Address to read
    :returns: Response body
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as reply:
            return reply.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise SourceError(f"Could not fetch {url}: {error}") from error


def parse_security(content: bytes, ticker: str) -> Security:
    """
    Find a ticker in the SEC ticker list.

    :param content: SEC `company_tickers_exchange.json` body
    :param ticker: Ticker to find, ignoring case
    :returns: The security's identity
    """
    table = json.loads(content)
    for row in table["data"]:
        entry = dict(zip(table["fields"], row))
        if entry["ticker"].upper() == ticker.upper():
            return Security(
                ticker=entry["ticker"],
                legal_name=entry["name"],
                cik=int(entry["cik"]),
                exchange=entry["exchange"],
            )
    raise SourceError(f"{ticker} is not in the SEC ticker list")


def parse_quote(content: bytes, ticker: str, now: datetime) -> Quote:
    """
    Pick the latest completed regular-session close from daily chart data.

    The newest bar is dropped while its regular session is still open, so an
    intraday price is never reported as a close.

    :param content: Yahoo chart API body with daily bars
    :param ticker: Ticker the chart must describe
    :param now: Current time, timezone-aware
    :returns: The close with its session date, time zone and currency
    """
    result = json.loads(content)["chart"]["result"][0]
    meta = result["meta"]
    if meta["symbol"].upper() != ticker.upper():
        raise SourceError(f"Quote is for {meta['symbol']}, not {ticker}")
    if meta["currency"] != "USD":
        raise SourceError(
            f"Quote currency is {meta['currency']}; only USD is supported"
        )

    closes = [
        (timestamp, close)
        for timestamp, close in zip(
            result["timestamp"], result["indicators"]["quote"][0]["close"]
        )
        if close is not None
    ]
    regular = meta["currentTradingPeriod"]["regular"]
    session_is_open = (
        regular["start"] <= meta["regularMarketTime"] < regular["end"]
        and now.timestamp() < regular["end"]
    )
    if session_is_open:
        closes.pop()
    if not closes:
        raise SourceError("The chart has no completed session")

    timestamp, close = closes[-1]
    local_time = datetime.fromtimestamp(timestamp + meta["gmtoffset"], timezone.utc)
    return Quote(
        price=Decimal(str(close)).quantize(Decimal(1).scaleb(-meta["priceHint"])),
        session_date=local_time.date(),
        time_zone=f"{meta['exchangeTimezoneName']} ({meta['timezone']})",
        currency=meta["currency"],
    )


def parse_treasury(content: bytes) -> list[RateObservation]:
    """
    Read the 10-year par yields from one month of the Treasury XML feed.

    The yield is selected by its element name, `BC_10YEAR`, never by position.

    :param content: Treasury Daily Treasury Par Yield Curve Rates feed body
    :returns: One observation per dated record that has a 10-year yield
    """
    observations = []
    for entry in ElementTree.fromstring(content).iter(f"{ATOM}entry"):
        values = {
            element.tag.rsplit("}", 1)[-1]: (element.text or "").strip()
            for element in entry.iter()
        }
        if values.get("NEW_DATE") and values.get("BC_10YEAR"):
            observations.append(
                RateObservation(
                    percent=Decimal(values["BC_10YEAR"]),
                    observed_on=date.fromisoformat(values["NEW_DATE"][:10]),
                )
            )
    return observations


def parse_erp(content: bytes) -> RateObservation:
    """
    Read the latest implied ERP from Damodaran's monthly workbook.

    The column is selected by its header, "ERP (T12 m with sustainable payout)",
    which the home page labels "Trailing 12 month, with adjusted payout".

    :param content: Body of `ERPbymonth.xlsx`
    :returns: The newest month's ERP in percent and that month's first day
    """
    rows, uses_1904 = _read_erp_sheet(content)
    headers = {text: column for column, text in rows[1].items()}
    date_column = headers[ERP_DATE_HEADER]
    erp_column = headers[ERP_HEADER]
    latest = max(
        row
        for row, cells in rows.items()
        if row > 1 and date_column in cells and erp_column in cells
    )

    # Workbook dates count days from 1900, or from 1904 when the workbook says so
    epoch = date(1904, 1, 1) if uses_1904 else date(1899, 12, 30)
    return RateObservation(
        percent=(Decimal(rows[latest][erp_column]) * 100).quantize(Decimal("0.01")),
        observed_on=epoch + timedelta(days=int(Decimal(rows[latest][date_column]))),
    )


def build_initiation_record(ticker: str, fetch: Fetch, now: datetime) -> str:
    """
    Fetch the security, quote and rates and render them as the initiation record.

    Raise SourceError when a source is unreachable or unreadable, the quote is
    not in USD, or a rate is older than its freshness limit.

    :param ticker: Company ticker to resolve
    :param fetch: Function returning the body of a URL
    :param now: Capture time, timezone-aware
    :returns: Markdown record of the sourced facts
    """
    today = now.date()
    security = _read(SECURITY_URL, fetch, lambda body: parse_security(body, ticker))
    quote_url = QUOTE_URL.format(ticker=urllib.parse.quote(security.ticker))
    quote = _read(quote_url, fetch, lambda body: parse_quote(body, ticker, now))
    treasury = _fetch_treasury(fetch, today)
    erp = _read(ERP_URL, fetch, parse_erp)
    _require_fresh("Treasury", treasury, today, TREASURY_MAX_AGE_DAYS)
    _require_fresh("ERP", erp, today, ERP_MAX_AGE_DAYS)

    treasury_url = TREASURY_URL.format(month=f"{treasury.observed_on:%Y%m}")
    treasury_age = (today - treasury.observed_on).days
    erp_age = (today - erp.observed_on).days
    return "\n".join(
        [
            f"Captured {now.astimezone(timezone.utc):%Y-%m-%d %H:%M:%S} UTC by code "
            "from the sources below, not by an agent. Do not search again for "
            "these facts.",
            "",
            "| Fact | Value |",
            "|---|---|",
            f"| Ticker | {security.ticker} |",
            f"| Legal name | {security.legal_name} |",
            f"| Listing exchange | {security.exchange} |",
            f"| SEC CIK | {security.cik} |",
            "| Latest completed regular-session close "
            f"| {quote.price} {quote.currency} |",
            f"| Session date | {quote.session_date} |",
            f"| Session time zone | {quote.time_zone} |",
            "| Nominal U.S. 10-year Treasury par yield "
            f"| {treasury.percent} (observed {treasury.observed_on}, "
            f"{treasury_age} days before capture) |",
            "| Damodaran implied ERP, trailing 12 month with adjusted payout "
            f"| {erp.percent} (effective {erp.observed_on}, "
            f"{erp_age} days before capture) |",
            "",
            "Rates are published percentages, so 4.25 means 4.25%. The ERP is over "
            "the unadjusted U.S. Treasury rate. The security class is not "
            "included; identify it from the latest filing.",
            "",
            "Sources:",
            f"- Identity: SEC company_tickers_exchange.json, {SECURITY_URL}",
            f"- Close: Yahoo Finance chart data, {quote_url}. It is a secondary "
            "market-data source, not corroborated by a second source or the exchange.",
            "- Treasury: Daily Treasury Par Yield Curve Rates XML feed, element "
            f"BC_10YEAR, {treasury_url}",
            f"- ERP: Damodaran, {ERP_URL}, sheet \"{ERP_SHEET}\", column "
            f"\"{ERP_HEADER}\"",
            "",
        ]
    )


def _read_erp_sheet(content: bytes) -> tuple[dict[int, dict[str, str]], bool]:
    """
    Read the ERP sheet of the workbook as text cells by row number and column letter.

    The sheet is found by name through the workbook's relationships, and shared
    strings are resolved to their text.

    :param content: Body of `ERPbymonth.xlsx`
    :returns: The cells and whether the workbook counts dates from 1904
    """
    with zipfile.ZipFile(BytesIO(content)) as book:
        workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        strings = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
        sheet_id = [
            sheet.get(DOCUMENT_RELATIONSHIP)
            for sheet in workbook.iter(f"{SPREADSHEET}sheet")
            if sheet.get("name") == ERP_SHEET
        ][0]
        target = [
            link.get("Target")
            for link in relationships.iter(f"{PACKAGE_RELATIONSHIP}Relationship")
            if link.get("Id") == sheet_id
        ][0]
        sheet = ElementTree.fromstring(book.read(f"xl/{target}"))
    texts = [
        "".join(part.text or "" for part in item.iter(f"{SPREADSHEET}t"))
        for item in strings.iter(f"{SPREADSHEET}si")
    ]

    rows: dict[int, dict[str, str]] = {}
    for cell in sheet.iter(f"{SPREADSHEET}c"):
        value = cell.find(f"{SPREADSHEET}v")
        if value is None or value.text is None:
            continue
        column, row = re.fullmatch(r"([A-Z]+)(\d+)", cell.get("r")).groups()
        is_text = cell.get("t") == "s"
        rows.setdefault(int(row), {})[column] = (
            texts[int(value.text)] if is_text else value.text
        )
    properties = workbook.find(f"{SPREADSHEET}workbookPr")
    return rows, properties.get("date1904") in ("1", "true")


def _read[T](url: str, fetch: Fetch, parse: Callable[[bytes], T]) -> T:
    """
    Fetch a URL and parse its body, naming the URL in any failure.

    :param url: Address to read
    :param fetch: Function returning the body of a URL
    :param parse: Function turning the body into a result
    :returns: The parsed result
    """
    content = fetch(url)
    try:
        return parse(content)
    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        AttributeError,
        ElementTree.ParseError,
        zipfile.BadZipFile,
    ) as error:
        raise SourceError(f"Unreadable response from {url}: {error!r}") from error


def _fetch_treasury(fetch: Fetch, today: date) -> RateObservation:
    """
    Read the latest 10-year yield, looking back a month if this month is empty.

    :param fetch: Function returning the body of a URL
    :param today: Date of capture
    :returns: The newest observation
    """
    last_month = today.replace(day=1) - timedelta(days=1)
    for month in (today, last_month):
        url = TREASURY_URL.format(month=f"{month:%Y%m}")
        observations = _read(url, fetch, parse_treasury)
        if observations:
            return max(observations, key=lambda observation: observation.observed_on)
    raise SourceError("The Treasury feed has no 10-year yield this or last month")


def _require_fresh(
    label: str, observation: RateObservation, today: date, max_age_days: int
) -> None:
    """
    Raise SourceError when an observation is older than its limit.

    :param label: Rate name for the message
    :param observation: Observation to check
    :param today: Date of capture
    :param max_age_days: Oldest acceptable age in days
    """
    age_days = (today - observation.observed_on).days
    if age_days > max_age_days:
        raise SourceError(
            f"{label} observation of {observation.observed_on} is {age_days} days "
            f"old; the limit is {max_age_days}"
        )
