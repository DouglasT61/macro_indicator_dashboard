from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx


WORLD_BANK_API_URL = 'https://api.worldbank.org/v2/country/{country}/indicator/{indicator}'
USER_AGENT = 'macro-stress-dashboard/0.1'
COUNTRY_WEIGHTS = {
    'JPN': 0.45,
    'DEU': 0.35,
    'CHN': 0.20,
}
COUNTRY_LABELS = {
    'JPN': 'Japan',
    'DEU': 'Germany',
    'CHN': 'China',
}
INDICATOR_IDS = {
    'current_account_balance': 'BN.CAB.XOKA.GD.ZS',
    'imports_share_gdp': 'NE.IMP.GNFS.ZS',
}


@dataclass(slots=True)
class WorldBankImporterVulnerabilityAssessment:
    score: float
    source: str
    notes: str
    history: list[tuple[datetime, float]]


def _safe_float(value: object) -> float | None:
    if value in {None, '', 'null', 'None'}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_indicator_observations(
    client: httpx.Client,
    country: str,
    indicator: str,
) -> list[tuple[int, float]]:
    response = client.get(
        WORLD_BANK_API_URL.format(country=country, indicator=indicator),
        params={'format': 'json', 'per_page': 80},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        return []

    observations: list[tuple[int, float]] = []
    for row in payload[1]:
        if not isinstance(row, dict):
            continue
        year_raw = row.get('date')
        value = _safe_float(row.get('value'))
        if value is None:
            continue
        try:
            year = int(str(year_raw))
        except (TypeError, ValueError):
            continue
        observations.append((year, value))
    observations.sort(key=lambda item: item[0])
    return observations


def _current_account_stress(value: float) -> float:
    # Positive current-account balances reduce vulnerability; deficits quickly raise it.
    return max(0.0, min(100.0, 50.0 - (value * 8.0)))


def _imports_share_stress(value: float) -> float:
    return max(0.0, min(100.0, value * 2.0))


def _latest_country_score(
    current_account: list[tuple[int, float]],
    imports_share: list[tuple[int, float]],
) -> tuple[float, int] | None:
    if not current_account or not imports_share:
        return None

    current_account_map = {year: value for year, value in current_account}
    imports_share_map = {year: value for year, value in imports_share}
    common_years = sorted(set(current_account_map) & set(imports_share_map))
    if not common_years:
        return None

    latest_year = common_years[-1]
    current_account_value = current_account_map[latest_year]
    imports_share_value = imports_share_map[latest_year]
    score = (
        0.42 * _current_account_stress(current_account_value)
        + 0.58 * _imports_share_stress(imports_share_value)
    )
    return round(score, 4), latest_year


def _build_constant_daily_history(
    start: date,
    end: date,
    value: float,
) -> list[tuple[datetime, float]]:
    history: list[tuple[datetime, float]] = []
    current = start
    while current <= end:
        history.append((datetime.combine(current, datetime.min.time(), tzinfo=UTC).replace(hour=12), round(value, 6)))
        current += timedelta(days=1)
    return history


def collect_world_bank_importer_vulnerability(
    *,
    timeout_seconds: float = 20.0,
    days: int = 180,
    end_date: date | None = None,
) -> WorldBankImporterVulnerabilityAssessment:
    end = end_date or date.today()
    start = end - timedelta(days=days - 1)
    country_scores: list[tuple[str, float, int]] = []

    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        for country in COUNTRY_WEIGHTS:
            current_account = _fetch_indicator_observations(client, country, INDICATOR_IDS['current_account_balance'])
            imports_share = _fetch_indicator_observations(client, country, INDICATOR_IDS['imports_share_gdp'])
            latest = _latest_country_score(current_account, imports_share)
            if latest is None:
                continue
            score, latest_year = latest
            country_scores.append((country, score, latest_year))

    if not country_scores:
        raise ValueError('World Bank indicator responses unavailable')

    weighted_score = 0.0
    total_weight = 0.0
    component_labels: list[str] = []
    latest_year = min(item[2] for item in country_scores)
    for country, score, country_year in country_scores:
        weight = COUNTRY_WEIGHTS.get(country, 0.0)
        weighted_score += score * weight
        total_weight += weight
        component_labels.append(f"{COUNTRY_LABELS.get(country, country)} {score:.1f} ({country_year})")
    composite = weighted_score / max(total_weight, 1.0)
    history = _build_constant_daily_history(start, end, composite)
    checked_at = datetime.now(UTC).isoformat()
    notes = (
        'Auto-scored from World Bank importer indicators; '
        'source=world-bank-indicators; '
        f'checked={checked_at}; '
        f'items={len(country_scores)}; '
        f'signal={composite:.2f}; '
        f'components={" | ".join(component_labels)}; '
        'notes=Germany is used as the Europe proxy for this structural overlay.'
    )
    return WorldBankImporterVulnerabilityAssessment(
        score=round(composite, 2),
        source='worldbank/importer-vulnerability',
        notes=notes,
        history=history,
    )
