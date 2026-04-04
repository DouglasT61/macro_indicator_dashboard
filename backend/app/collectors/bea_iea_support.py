from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, timedelta

import httpx


BEA_IIP_PRODUCT_URL = 'https://www.bea.gov/data/intl-trade-investment/international-investment-position'
IEA_NETIMPORTS_LATEST_URL = 'https://api.iea.org/netimports/latest'
IEA_NETIMPORTS_MONTHLY_URL = 'https://api.iea.org/netimports/monthly/'

BEA_ARTICLE_LINK_RE = re.compile(
    r'https://apps\.bea\.gov/scb/issues/\d{4}/[^"]+international-investment-position\.htm',
    flags=re.IGNORECASE,
)
BEA_TITLE_RE = re.compile(
    r'<title>\s*SCB,\s*A Look at the U\.S\. International Investment Position:\s*(?P<title>[^<]+?)\s*,\s*[A-Za-z]+\s+\d{4}\s*</title>',
    flags=re.IGNORECASE,
)
BEA_NET_IIP_RE = re.compile(
    r'The net international investment position (?:decreased|increased) from (?P<previous>-?\$?[0-9.,]+) trillion .*? to (?P<current>-?\$?[0-9.,]+) trillion',
    flags=re.IGNORECASE,
)
BEA_ASSETS_TOTAL_RE = re.compile(
    r'U\.S\. assets (?:increased|decreased) by \$[0-9.,]+ (?:billion|trillion) to a total of \$(?P<current>[0-9.,]+) trillion',
    flags=re.IGNORECASE,
)
BEA_LIABILITIES_TOTAL_RE = re.compile(
    r'U\.S\. liabilities (?:increased|decreased) by \$[0-9.,]+ (?:billion|trillion) to a total of \$(?P<current>[0-9.,]+) trillion',
    flags=re.IGNORECASE,
)
BEA_LIABILITY_TRANSACTIONS_RE = re.compile(
    r'Financial transactions(?: .*?)? (?P<direction>raised|lowered|reduced) U\.S\. liabilities by \$(?P<value>[0-9.,]+) (?P<unit>billion|trillion)',
    flags=re.IGNORECASE,
)

QUARTER_ENDS = {
    'first': (3, 31),
    'second': (6, 30),
    'third': (9, 30),
    'fourth': (12, 31),
}


@dataclass(slots=True)
class BEAIIPObservation:
    observed_at: date
    net_iip_trillion: float
    assets_total_trillion: float
    liabilities_total_trillion: float
    liability_financial_transactions_billion: float


@dataclass(slots=True)
class IEAOilStockObservation:
    observed_at: date
    country_name: str
    total_days: float | None
    industry_days: float | None
    public_days: float | None
    abroad_industry_days: float | None
    abroad_public_days: float | None


def fetch_bea_iip_observations(client: httpx.Client) -> list[BEAIIPObservation]:
    response = client.get(BEA_IIP_PRODUCT_URL)
    response.raise_for_status()
    article_links = sorted(set(BEA_ARTICLE_LINK_RE.findall(response.text)))
    if not article_links:
        raise ValueError('No BEA IIP article links were found on the product page')

    observations: list[BEAIIPObservation] = []
    for url in article_links:
        article = client.get(url)
        article.raise_for_status()
        parsed = parse_bea_iip_article(article.text)
        if parsed is not None:
            observations.append(parsed)

    if not observations:
        raise ValueError('Unable to parse any BEA IIP article pages')

    deduped = {item.observed_at: item for item in observations}
    return [deduped[key] for key in sorted(deduped)]


def parse_bea_iip_article(raw_html: str) -> BEAIIPObservation | None:
    title_match = BEA_TITLE_RE.search(raw_html)
    if title_match is None:
        return None

    observed_at = _parse_quarter_end(title_match.group('title'))
    if observed_at is None:
        return None

    text = html.unescape(raw_html)
    text = text.replace('&minus;', '-')
    text = text.replace('−', '-')
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    net_match = BEA_NET_IIP_RE.search(text)
    assets_match = BEA_ASSETS_TOTAL_RE.search(text)
    liabilities_match = BEA_LIABILITIES_TOTAL_RE.search(text)
    transactions_match = BEA_LIABILITY_TRANSACTIONS_RE.search(text)
    if None in {net_match, assets_match, liabilities_match, transactions_match}:
        return None

    return BEAIIPObservation(
        observed_at=observed_at,
        net_iip_trillion=_parse_signed_trillion(net_match.group('current')),
        assets_total_trillion=float(assets_match.group('current').replace(',', '')),
        liabilities_total_trillion=float(liabilities_match.group('current').replace(',', '')),
        liability_financial_transactions_billion=_signed_transaction_billions(transactions_match),
    )


def fetch_iea_oil_stock_observations(
    client: httpx.Client,
    start: date,
    end: date,
) -> list[IEAOilStockObservation]:
    latest_month = fetch_iea_latest_month(client)
    requested_start = date(start.year, start.month, 1)
    current = requested_start
    latest = date(latest_month[0], latest_month[1], 1)
    observations: list[IEAOilStockObservation] = []

    while current <= latest:
        response = client.get(
            IEA_NETIMPORTS_MONTHLY_URL,
            params={'year': current.year, 'month': current.month},
        )
        response.raise_for_status()
        payload = response.json()
        observed_at = _month_end(current.year, current.month)
        for row in payload:
            observations.append(
                IEAOilStockObservation(
                    observed_at=observed_at,
                    country_name=str(row.get('countryName') or '').strip(),
                    total_days=_parse_iea_value(row.get('total')),
                    industry_days=_parse_iea_value(row.get('industry')),
                    public_days=_parse_iea_value(row.get('publicData')),
                    abroad_industry_days=_parse_iea_value(row.get('abroadIndustry')),
                    abroad_public_days=_parse_iea_value(row.get('abroadPublic')),
                )
            )
        current = _next_month(current)

    if not observations:
        raise ValueError('IEA oil stock API returned no observations')
    return [item for item in observations if item.observed_at <= end]


def fetch_iea_latest_month(client: httpx.Client) -> tuple[int, int]:
    response = client.get(IEA_NETIMPORTS_LATEST_URL)
    response.raise_for_status()
    payload = response.json()
    year = int(payload['year'])
    month = int(payload['month'])
    return year, month


def _parse_quarter_end(title: str) -> date | None:
    match = re.search(r'(First|Second|Third|Fourth) Quarter(?: and Year)?\s+(\d{4})', title, flags=re.IGNORECASE)
    if match is None:
        return None
    month, day = QUARTER_ENDS[match.group(1).lower()]
    return date(int(match.group(2)), month, day)


def _parse_signed_trillion(value: str) -> float:
    cleaned = value.replace('$', '').replace(',', '').strip()
    return float(cleaned)


def _unit_to_billions(value: float, unit: str) -> float:
    return round(value * 1000.0, 6) if unit.lower() == 'trillion' else round(value, 6)


def _signed_transaction_billions(match: re.Match[str]) -> float:
    value = _unit_to_billions(float(match.group('value').replace(',', '')), match.group('unit'))
    direction = match.group('direction').lower()
    if direction in {'lowered', 'reduced'}:
        return -value
    return value


def _parse_iea_value(raw_value: object) -> float | None:
    if raw_value in {None, '', '-', 'Net Exporter'}:
        return None
    cleaned = str(raw_value).replace(',', '').replace(' ', '').strip()
    if cleaned in {'', '-', 'NetExporter'}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _next_month(current: date) -> date:
    if current.month == 12:
        return date(current.year + 1, 1, 1)
    return date(current.year, current.month + 1, 1)
