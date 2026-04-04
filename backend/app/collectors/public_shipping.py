from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlencode

import httpx


EIA_CHOKEPOINTS_URL = 'https://www.eia.gov/international/content/analysis/special_topics/World_Oil_Transit_Chokepoints/'
AISHUB_WS_URL = 'https://data.aishub.net/ws.php'
PORTWATCH_HORMUZ_QUERY_URL = 'https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query'
GLOBAL_FISHING_WATCH_EVENTS_URL = 'https://gateway.api.globalfishingwatch.org/v3/events'
PORTWATCH_FIELDS = 'date,portid,portname,n_tanker,n_total,capacity_tanker,capacity'
USER_AGENT = 'Mozilla/5.0 macro-stress-dashboard/0.1'
RED_SEA_BBOX = {'latmin': 11.0, 'latmax': 21.5, 'lonmin': 41.0, 'lonmax': 45.5}
HORMUZ_BBOX = {'latmin': 24.0, 'latmax': 28.5, 'lonmin': 54.0, 'lonmax': 58.5}
RED_SEA_POLYGON_WKT = 'POLYGON((41 11, 45.5 11, 45.5 21.5, 41 21.5, 41 11))'
HORMUZ_POLYGON_WKT = 'POLYGON((54 24, 58.5 24, 58.5 28.5, 54 28.5, 54 24))'
GFW_PORT_VISITS_DATASET = 'public-global-port-visits-events:v3.0'


@dataclass(slots=True)
class TankerDisruptionAssessment:
    score: float
    notes: str
    source: str


@dataclass(slots=True)
class HormuzTransitAssessment:
    score: float
    notes: str
    source: str
    history: list[tuple[datetime, float]]


@dataclass(slots=True)
class GlobalFishingWatchAssessment:
    score: float
    notes: str
    source: str
    history: list[tuple[datetime, float]]


def _strip_html(value: str) -> str:
    text = re.sub(r'<(script|style)[^>]*>.*?</>', ' ', value, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _safe_float(value: object) -> float | None:
    if value in {None, '', 'null', 'None'}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return datetime.fromisoformat(stripped.replace('Z', '+00:00')).astimezone(UTC)
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        return _parse_portwatch_datetime(value)
    return None


def _lookup_nested(mapping: dict[str, object], path: tuple[str, ...]) -> object | None:
    current: object = mapping
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _parse_portwatch_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            return datetime.fromtimestamp(float(value) / 1000.0, tz=UTC)
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            numeric = int(stripped)
            return _parse_portwatch_datetime(numeric)
        try:
            return datetime.fromisoformat(stripped.replace('Z', '+00:00')).astimezone(UTC)
        except ValueError:
            return None
    return None


def _normalize_hormuz_label(value: str | None) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def _is_hormuz_record(attributes: dict[str, object]) -> bool:
    port_name = _normalize_hormuz_label(str(attributes.get('portname') or ''))
    port_id = _normalize_hormuz_label(str(attributes.get('portid') or ''))
    return 'hormuz' in port_name or 'hormuz' in port_id


def _extract_bab_el_mandeb_flows(html: str) -> tuple[float | None, float | None]:
    text = _strip_html(html)
    match = re.search(
        r'Total oil flows through Bab el-Mandeb Strait\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)',
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None
    flow_2023 = float(match.group(4))
    flow_latest = float(match.group(6))
    return flow_2023, flow_latest


def score_eia_chokepoint_page(html: str) -> TankerDisruptionAssessment:
    text = _strip_html(html).lower()
    flow_2023, flow_latest = _extract_bab_el_mandeb_flows(html)
    disruption_score = 40.0
    details: list[str] = []

    if flow_2023 is not None and flow_latest is not None and flow_2023 > 0:
        drop_ratio = max(0.0, min(1.0, (flow_2023 - flow_latest) / flow_2023))
        disruption_score += drop_ratio * 35.0
        details.append(f'bab-el-mandeb flow drop from {flow_2023:.1f} to {flow_latest:.1f} mb/d')

    for term, weight in {
        'security concerns': 6.0,
        'high insurance rates': 8.0,
        'ships avoided the bab el-mandeb': 10.0,
        'red sea attacks': 10.0,
        'oil disruptions': 8.0,
    }.items():
        if term in text:
            disruption_score += weight
            details.append(term)

    disruption_score = max(10.0, min(90.0, disruption_score))
    return TankerDisruptionAssessment(
        score=round(disruption_score, 2),
        notes='EIA chokepoint scan: ' + '; '.join(details) if details else 'EIA chokepoint scan available but no disruption details parsed.',
        source='eia/chokepoints',
    )


def _count_aishub_objects(payload: object) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ('data', 'rows', 'objects', 'vessels'):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return len(payload)
    return 0


def _fetch_aishub_area_count(client: httpx.Client, username: str, bbox: dict[str, float]) -> int | None:
    response = client.get(
        AISHUB_WS_URL,
        params={
            'username': username,
            'format': 1,
            'output': 'json',
            'compress': 0,
            'interval': 1440,
            **bbox,
        },
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return None
    return _count_aishub_objects(payload)


def collect_tanker_disruption_assessment(
    aishub_username: str | None,
    global_fishing_watch_api_key: str | None = None,
    timeout_seconds: float = 20.0,
) -> TankerDisruptionAssessment:
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        eia_response = client.get(EIA_CHOKEPOINTS_URL)
        eia_response.raise_for_status()
        assessment = score_eia_chokepoint_page(eia_response.text)

        if aishub_username:
            try:
                red_sea_count = _fetch_aishub_area_count(client, aishub_username, RED_SEA_BBOX)
                hormuz_count = _fetch_aishub_area_count(client, aishub_username, HORMUZ_BBOX)
            except Exception:
                assessment.notes = assessment.notes + '; AISHub request unavailable'
            else:
                counts = [count for count in (red_sea_count, hormuz_count) if count is not None]
                if counts:
                    traffic_penalty = 0.0
                    if red_sea_count is not None and red_sea_count < 25:
                        traffic_penalty += 8.0
                    if hormuz_count is not None and hormuz_count < 20:
                        traffic_penalty += 6.0
                    assessment.score = round(max(10.0, min(90.0, assessment.score + traffic_penalty)), 2)
                    assessment.notes = assessment.notes + f'; AISHub counts red_sea={red_sea_count}, hormuz={hormuz_count}'
                    assessment.source = 'eia/chokepoints+aishub'
        else:
            assessment.notes = assessment.notes + '; AISHub not configured'

    if global_fishing_watch_api_key:
        try:
            gfw = collect_global_fishing_watch_assessment(global_fishing_watch_api_key, timeout_seconds=timeout_seconds)
        except Exception:
            assessment.notes = assessment.notes + '; Global Fishing Watch unavailable'
        else:
            assessment.score = round(max(10.0, min(95.0, 0.72 * assessment.score + 0.28 * gfw.score)), 2)
            assessment.notes = assessment.notes + f'; GFW signal={gfw.score:.2f}'
            assessment.source = f'{assessment.source}+gfw' if assessment.source != 'eia/chokepoints' else 'eia/chokepoints+gfw'
    return assessment


def _fetch_portwatch_hormuz_rows(client: httpx.Client) -> list[dict[str, object]]:
    response = client.get(
        PORTWATCH_HORMUZ_QUERY_URL,
        params={
            'where': '1=1',
            'outFields': PORTWATCH_FIELDS,
            'returnGeometry': 'false',
            'orderByFields': 'date ASC',
            'resultRecordCount': 10000,
            'f': 'json',
        },
    )
    response.raise_for_status()
    payload = response.json()
    features = payload.get('features', [])
    rows: list[dict[str, object]] = []
    for feature in features:
        attributes = feature.get('attributes', {}) if isinstance(feature, dict) else {}
        if isinstance(attributes, dict) and _is_hormuz_record(attributes):
            rows.append(attributes)
    if not rows:
        raise ValueError('No PortWatch Hormuz rows returned')
    return rows


def _window_average(values: list[float], end_index: int, window: int) -> float:
    start_index = max(0, end_index - window + 1)
    sample = values[start_index:end_index + 1]
    return sum(sample) / max(len(sample), 1)


def _fetch_gfw_event_rows(
    client: httpx.Client,
    api_key: str,
    *,
    geometry_wkt: str,
    start: date,
    end: date,
) -> list[dict[str, object]]:
    response = client.get(
        GLOBAL_FISHING_WATCH_EVENTS_URL,
        headers={
            'Authorization': f'Bearer {api_key}',
            'User-Agent': USER_AGENT,
        },
        params={
            'datasets[0]': GFW_PORT_VISITS_DATASET,
            'start-date': start.isoformat(),
            'end-date': end.isoformat(),
            'geometry': geometry_wkt,
            'limit': 2000,
            'offset': 0,
        },
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        for key in ('entries', 'data', 'events'):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def build_gfw_port_activity_stress_history(
    red_sea_rows: list[dict[str, object]],
    hormuz_rows: list[dict[str, object]],
    *,
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    def _daily_counts(rows: list[dict[str, object]]) -> dict[date, float]:
        counts: dict[date, float] = {}
        for row in rows:
            observed_at = None
            for path in (
                ('start',),
                ('startDate',),
                ('start_date',),
                ('eventStart',),
                ('eventInfo', 'start'),
                ('eventInfo', 'startDate'),
                ('portVisit', 'start'),
                ('portVisit', 'startDate'),
            ):
                observed_at = _extract_timestamp(_lookup_nested(row, path))
                if observed_at is not None:
                    break
            if observed_at is None:
                continue
            counts[observed_at.date()] = counts.get(observed_at.date(), 0.0) + 1.0
        return counts

    def _dense_counts(counts: dict[date, float]) -> list[tuple[datetime, float]]:
        history: list[tuple[datetime, float]] = []
        current = start
        while current <= end:
            history.append((datetime.combine(current, datetime.min.time(), tzinfo=UTC).replace(hour=12), counts.get(current, 0.0)))
            current += timedelta(days=1)
        return history

    def _region_stress(history: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
        values = [value for _, value in history]
        series: list[tuple[datetime, float]] = []
        prior_drop = 0.0
        for index, (timestamp, _) in enumerate(history):
            avg_7 = _window_average(values, index, 7)
            avg_30 = _window_average(values, index, 30)
            drop = max(0.0, (avg_30 - avg_7) / max(avg_30, 1.0))
            acceleration = max(0.0, drop - prior_drop)
            prior_drop = drop
            score = 22.0 + 92.0 * drop + 18.0 * acceleration
            series.append((timestamp, round(max(10.0, min(95.0, score)), 6)))
        return series

    red_history = _region_stress(_dense_counts(_daily_counts(red_sea_rows)))
    hormuz_history = _region_stress(_dense_counts(_daily_counts(hormuz_rows)))
    if not red_history and not hormuz_history:
        return []

    composite: list[tuple[datetime, float]] = []
    total_points = max(len(red_history), len(hormuz_history))
    for index in range(total_points):
        timestamp = red_history[index][0] if index < len(red_history) else hormuz_history[index][0]
        red_value = red_history[index][1] if index < len(red_history) else 10.0
        hormuz_value = hormuz_history[index][1] if index < len(hormuz_history) else 10.0
        composite.append((timestamp, round(0.65 * red_value + 0.35 * hormuz_value, 6)))
    return composite


def collect_global_fishing_watch_assessment(
    api_key: str,
    *,
    timeout_seconds: float = 20.0,
    days: int = 90,
    end_date: date | None = None,
) -> GlobalFishingWatchAssessment:
    end = end_date or date.today()
    start = end - timedelta(days=days - 1)
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        red_sea_rows = _fetch_gfw_event_rows(client, api_key, geometry_wkt=RED_SEA_POLYGON_WKT, start=start, end=end)
        hormuz_rows = _fetch_gfw_event_rows(client, api_key, geometry_wkt=HORMUZ_POLYGON_WKT, start=start, end=end)

    history = build_gfw_port_activity_stress_history(red_sea_rows, hormuz_rows, start=start, end=end)
    if not history:
        raise ValueError('Global Fishing Watch event history is empty')

    checked_at = datetime.now(UTC).isoformat()
    notes = (
        'Global Fishing Watch port-visit scan: '
        f'red_sea_events={len(red_sea_rows)}; hormuz_events={len(hormuz_rows)}; '
        'stress is based on 7-day versus 30-day deterioration in public port-visit events. '
        f'source=global-fishing-watch; checked={checked_at}; items={len(red_sea_rows) + len(hormuz_rows)}; signal={history[-1][1]:.2f}'
    )
    return GlobalFishingWatchAssessment(
        score=round(history[-1][1], 2),
        notes=notes,
        source='gfw/public-port-visits',
        history=history,
    )


def build_hormuz_transit_stress_history(rows: list[dict[str, object]]) -> list[tuple[datetime, float]]:
    daily_map: dict[date, dict[str, float]] = {}
    for row in rows:
        observed_at = _parse_portwatch_datetime(row.get('date'))
        if observed_at is None:
            continue
        observed_day = observed_at.date()
        entry = daily_map.setdefault(observed_day, {'n_tanker': 0.0, 'n_total': 0.0, 'capacity_tanker': 0.0, 'capacity': 0.0})
        entry['n_tanker'] += _safe_float(row.get('n_tanker')) or 0.0
        entry['n_total'] += _safe_float(row.get('n_total')) or 0.0
        entry['capacity_tanker'] += _safe_float(row.get('capacity_tanker')) or 0.0
        entry['capacity'] += _safe_float(row.get('capacity')) or 0.0

    if not daily_map:
        return []

    ordered_days = sorted(daily_map)
    current = ordered_days[0]
    end_day = ordered_days[-1]
    last_entry = daily_map[current]
    dense_entries: list[tuple[datetime, dict[str, float]]] = []
    while current <= end_day:
        if current in daily_map:
            last_entry = daily_map[current]
        dense_entries.append((datetime.combine(current, datetime.min.time(), tzinfo=UTC).replace(hour=12), dict(last_entry)))
        current += timedelta(days=1)

    tanker_counts = [entry['n_tanker'] for _, entry in dense_entries]
    tanker_capacity = [entry['capacity_tanker'] for _, entry in dense_entries]
    tanker_shares = [
        (entry['n_tanker'] / entry['n_total']) if entry['n_total'] > 0 else 0.0
        for _, entry in dense_entries
    ]

    history: list[tuple[datetime, float]] = []
    previous_count_drop = 0.0
    for index, (timestamp, _) in enumerate(dense_entries):
        count_avg_7 = _window_average(tanker_counts, index, 7)
        count_avg_30 = _window_average(tanker_counts, index, 30)
        cap_avg_7 = _window_average(tanker_capacity, index, 7)
        cap_avg_30 = _window_average(tanker_capacity, index, 30)
        share_avg_7 = _window_average(tanker_shares, index, 7)
        share_avg_30 = _window_average(tanker_shares, index, 30)

        count_drop = max(0.0, (count_avg_30 - count_avg_7) / max(count_avg_30, 1.0))
        capacity_drop = max(0.0, (cap_avg_30 - cap_avg_7) / max(cap_avg_30, 1.0))
        share_drop = max(0.0, share_avg_30 - share_avg_7)
        acceleration = max(0.0, count_drop - previous_count_drop)
        previous_count_drop = count_drop

        score = 25.0 + 78.0 * count_drop + 42.0 * capacity_drop + 10.0 * share_drop + 24.0 * acceleration
        history.append((timestamp, round(max(10.0, min(95.0, score)), 6)))
    return history


def collect_hormuz_transit_assessment(timeout_seconds: float = 20.0) -> HormuzTransitAssessment:
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        rows = _fetch_portwatch_hormuz_rows(client)

    history = build_hormuz_transit_stress_history(rows)
    if not history:
        raise ValueError('PortWatch Hormuz transit history is empty')

    latest = history[-1]
    latest_row = max(
        rows,
        key=lambda row: _parse_portwatch_datetime(row.get('date')) or datetime(1970, 1, 1, tzinfo=UTC),
    )
    latest_count = _safe_float(latest_row.get('n_tanker')) or 0.0
    latest_capacity = _safe_float(latest_row.get('capacity_tanker')) or 0.0
    latest_total = _safe_float(latest_row.get('n_total')) or 0.0
    notes = (
        'PortWatch Strait of Hormuz transit scan: '
        f'tanker_calls={latest_count:.1f}; tanker_capacity={latest_capacity:.1f}; total_calls={latest_total:.1f}; '
        'stress is based on 7-day versus 30-day deterioration in tanker calls, tanker capacity, and tanker share.'
    )
    return HormuzTransitAssessment(
        score=round(latest[1], 2),
        notes=notes,
        source='portwatch/hormuz-transits',
        history=history,
    )
