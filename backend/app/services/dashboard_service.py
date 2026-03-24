from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.alerts.engine import build_state_space_alerts
from app.models import Alert, EventAnnotation, IndicatorSeries, IndicatorValue, ManualInput, RegimeScore
from app.regime_engine.config_loader import load_effective_config
from app.services.analytics import determine_status, normalize_value, rolling_change
from app.services.backtest_service import build_backtest_overview
from app.services.seed_service import seed_demo_data
from app.services.settings_service import get_alerts_enabled, get_source_status
from app.services.state_space_service import evaluate_state_space

HEADLINE_KEYS = [
    'brent_prompt_spread',
    'jpy_usd_basis',
    'sofr_spread',
    'move_index',
    'ten_year_yield',
    'thirty_year_yield',
    'fima_repo_usage',
    'auction_stress',
]

CRISIS_KEYS = [
    ('treasury_liquidity_proxy', 'Treasury liquidity / depth proxy'),
    ('sofr_spread', 'SOFR versus target'),
    ('treasury_basis_proxy', 'Cash-futures Treasury basis proxy'),
    ('jpy_usd_basis', 'JPY cross-currency basis'),
    ('brent_prompt_spread', 'Brent M1-M6 spread'),
]

PANEL_LAYOUT = {
    'oil_shipping': [
        {
            'id': 'oil-shipping-core',
            'title': 'Oil / Shipping View',
            'description': 'Physical scarcity, marine insurance, freight stress, and Gulf-U.S. crude dislocation.',
            'series': ['brent_prompt_spread', 'wti_prompt_spread', 'murban_wti_spread', 'oman_wti_spread', 'gulf_crude_dislocation', 'tanker_freight_proxy', 'hormuz_tanker_transit_stress', 'lng_proxy', 'marine_insurance_stress', 'tanker_disruption_score'],
        },
        {
            'id': 'geopolitical-triggers',
            'title': 'Geopolitical Trigger Overlays',
            'description': 'Documentary and event-driven upstream triggers that extend disruption half-life and escalation risk.',
            'series': ['p_and_i_circular_stress', 'iaea_nuclear_ambiguity', 'interceptor_depletion', 'governance_fragmentation', 'geopolitical_escalation_toggle'],
        },
    ],
    'funding': [
        {
            'id': 'market-plumbing',
            'title': 'Dollar Funding / Plumbing View',
            'description': 'Repo, cross-currency basis, swap lines, Treasury depth, volatility, and broad risk aversion.',
            'series': ['sofr_spread', 'eur_usd_basis', 'jpy_usd_basis', 'synthetic_usd_funding_pressure', 'move_index', 'vix_index', 'treasury_liquidity_proxy', 'treasury_basis_proxy', 'fed_swap_line_usage'],
        },
        {
            'id': 'external-importer',
            'title': 'External Importer Stress',
            'description': 'Local-currency oil stress for Japan, Europe, and China as a bridge into UST demand and Fed plumbing.',
            'series': ['oil_in_yen_stress', 'oil_in_eur_stress', 'oil_in_cny_stress', 'external_importer_stress'],
        },
        {
            'id': 'fx-funding-support',
            'title': 'FX Funding Support',
            'description': 'Direct spot FX and official short-rate inputs supporting the basis interpretation.',
            'series': ['eur_usd_spot', 'usd_jpy_spot', 'usd_cny_spot', 'sofr_rate', 'ecb_deposit_rate', 'japan_short_rate'],
        },
    ],
    'ust_funding': [
        {
            'id': 'ust-funding',
            'title': 'UST / Funding View',
            'description': 'Duration clearing, yields, term premium, auctions, and FIMA use.',
            'series': ['ten_year_yield', 'thirty_year_yield', 'term_premium_proxy', 'auction_stress', 'auction_clearing_stress', 'auction_foreign_sponsorship_stress', 'auction_issuance_mix_stress', 'fima_repo_usage', 'fed_swap_line_usage'],
        },
        {
            'id': 'inflation-expectations',
            'title': 'Inflation Expectations & Credibility',
            'description': 'Cleveland/FRED expected-inflation curve features and survey confirmation for persistence and credibility stress.',
            'series': ['expected_inflation_5y5y', 'inflation_expectations_level', 'inflation_expectations_slope', 'inflation_expectations_curvature', 'survey_market_expectations_gap', 'expectations_entrenchment_score'],
        },
    ],
    'employment': [
        {
            'id': 'employment-transmission',
            'title': 'Employment / Receipts / Household Credit View',
            'description': 'BLS labor transmission into household income squeeze, tax receipts, and credit impairment.',
            'series': ['payroll_momentum', 'unemployment_rate', 'wage_stickiness', 'hours_worked_momentum', 'temp_help_stress', 'employment_tax_base_proxy', 'household_real_income_squeeze'],
        },
    ],
    'consumer_credit': [
        {
            'id': 'consumer-credit',
            'title': 'Consumer / Fiscal / Credit View',
            'description': 'Consumer stress, receipts quality, deficits, private credit pressure, and market-sensitive tax stress.',
            'series': ['consumer_credit_stress', 'federal_receipts_quality', 'tax_receipts_market_stress', 'deficit_trend', 'private_credit_stress', 'employment_tax_base_proxy'],
        },
    ],
    'asset_regime': [
        {
            'id': 'asset-regime',
            'title': 'Asset Regime View',
            'description': 'Nominal duration risk, inflation hedges, oil, spreads, the dollar, and equities.',
            'series': ['spx_equal_weight', 'tips_vs_nominals', 'gold_price', 'oil_price', 'credit_spreads', 'usd_index_proxy', 'vix_index'],
        },
    ],
}

MANUAL_LABELS = {
    'marine_insurance_stress': ('Marine Insurance Stress', 'oil_shipping', 'score'),
    'tanker_disruption_score': ('Tanker Disruption Score', 'oil_shipping', 'score'),
    'private_credit_stress': ('Private Credit Markdown Stress', 'consumer_credit', 'score'),
    'geopolitical_escalation_toggle': ('Geopolitical Escalation Toggle', 'manual', 'toggle'),
    'central_bank_intervention_toggle': ('Central Bank Intervention Toggle', 'manual', 'toggle'),
    'p_and_i_circular_stress': ('P&I Circular Stress', 'geopolitical', 'score'),
    'iaea_nuclear_ambiguity': ('IAEA Nuclear Ambiguity', 'geopolitical', 'score'),
    'interceptor_depletion': ('Interceptor Depletion', 'geopolitical', 'score'),
    'governance_fragmentation': ('Governance Fragmentation', 'geopolitical', 'score'),
}

AUTO_OVERLAY_SOURCES = {
    'marine_insurance_stress': 'auto/beinsure-site-scan',
    'tanker_disruption_score': 'auto/public-shipping-scan',
    'private_credit_stress': 'auto/public-private-credit-scan',
    'geopolitical_escalation_toggle': 'auto/public-news-scan',
    'central_bank_intervention_toggle': 'auto/fed-feed-scan',
    'p_and_i_circular_stress': 'auto/pni-circular-scan',
    'iaea_nuclear_ambiguity': 'auto/iaea-verification-scan',
    'interceptor_depletion': 'auto/interceptor-depletion-scan',
    'governance_fragmentation': 'auto/governance-fragmentation-scan',
}

CAUSAL_LABELS = {
    'marine_insurance_stress': 'Marine insurance stress',
    'oil_physical_stress': 'Oil physical stress',
    'dollar_funding_stress': 'Dollar funding stress',
    'ust_demand_stress': 'UST demand stress',
    'repo_basis_stress': 'Repo / basis stress',
    'fed_intervention_stress': 'Fed intervention stress',
    'inflation_repression_stress': 'Inflation / repression stress',
    'expectations_credibility_stress': 'Expectations / credibility stress',
    'geopolitical_trigger_stress': 'Geopolitical trigger stress',
    'external_importer_stress': 'External importer stress',
    'household_tax_stress': 'Household / tax stress',
}

SOURCE_CONFIDENCE = {
    'live': 1.0,
    'proxy': 0.85,
    'auto': 0.75,
    'manual': 0.65,
    'demo': 0.0,
}


def _alert_field(alert: Any, field: str) -> Any:
    return getattr(alert, field) if hasattr(alert, field) else alert.get(field)


def _normalize_alert_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _serialize_alert(alert: Any) -> dict[str, Any]:
    return {
        'id': _alert_field(alert, 'id'),
        'timestamp': _normalize_alert_timestamp(_alert_field(alert, 'timestamp')),
        'severity': _alert_field(alert, 'severity'),
        'title': _alert_field(alert, 'title'),
        'body': _alert_field(alert, 'body'),
        'related_indicators': _alert_field(alert, 'related_indicators_json') or [],
        'next_stage_consequence': _alert_field(alert, 'next_stage_consequence'),
    }


def _classify_source(source: str) -> str:
    if source == 'manual':
        return 'manual'
    if source.startswith('auto/'):
        return 'auto'
    if source.startswith('demo/'):
        return 'demo'
    if source.startswith('proxy/'):
        return 'proxy'
    return 'live'


def _is_auto_overlay(manual: ManualInput) -> bool:
    notes = (manual.notes or '').strip().lower()
    auto_prefixes = (
        'auto-scored from',
        'eia chokepoint scan:',
        'portwatch strait of hormuz transit scan:',
    )
    return notes.startswith(auto_prefixes) or 'source=' in notes or 'checked=' in notes or 'aishub' in notes


def _manual_overlay_source(key: str, manual: ManualInput) -> tuple[str, str, str]:
    name = MANUAL_LABELS.get(key, (key.replace('_', ' ').title(), 'manual', 'score'))[0]
    if _is_auto_overlay(manual):
        source = AUTO_OVERLAY_SOURCES.get(key, 'auto/public-overlay')
        return source, 'auto', f'{name} is auto-scored from public-source refresh at {manual.value:.2f}.'
    return 'manual', 'manual', f'{name} is set manually at {manual.value:.2f}.'


def _latest_manual_inputs(db: Session) -> dict[str, ManualInput]:
    latest: dict[str, ManualInput] = {}
    for row in db.query(ManualInput).order_by(ManualInput.timestamp.asc()).all():
        latest[row.key] = row
    return latest


def _build_series_map(db: Session) -> dict[str, IndicatorSeries]:
    return {series.key: series for series in db.query(IndicatorSeries).all()}


def _series_values(db: Session, series_id: int) -> list[IndicatorValue]:
    return (
        db.query(IndicatorValue)
        .filter(IndicatorValue.series_id == series_id)
        .order_by(IndicatorValue.timestamp.asc())
        .all()
    )


def _build_indicator_snapshot(
    key: str,
    series_map: dict[str, IndicatorSeries],
    config: dict[str, Any],
    db: Session,
    days: int = 90,
) -> dict[str, Any]:
    thresholds = config['thresholds'].get(key)
    is_auction_series = key.startswith('auction_')
    chart_style = 'step' if is_auction_series else 'line'
    chart_window_label = '90d'
    if key in series_map:
        series = series_map[key]
        values = _series_values(db, series.id)
        if not values:
            raise KeyError(key)
        history_values = values[-days:]
        if is_auction_series:
            one_year_values = values[-365:] if len(values) >= 365 else values
            if len({round(float(item.value), 4) for item in one_year_values}) > 1:
                history_values = one_year_values
                chart_window_label = '1y'
            else:
                two_year_values = values[-730:] if len(values) >= 730 else values
                history_values = two_year_values
                chart_window_label = '2y'
        latest = values[-1]
        source_class = _classify_source(series.source)
        status = determine_status(float(latest.value), thresholds)
        display_name = series.name
        display_unit = series.unit
        if key == 'jpy_usd_basis' and series.source.startswith('support/'):
            display_name = 'JPY/USD Funding Stress'
        narrative = f"{display_name} is {status} at {float(latest.value):.2f} {display_unit}."
        if source_class == 'demo':
            narrative = f'{display_name} live feed is unavailable. Demo fallback values are suppressed in the UI.'
        elif source_class == 'proxy':
            narrative = f'{display_name} is a proxy-derived signal at {float(latest.value):.2f} {display_unit}.'
        elif key == 'jpy_usd_basis' and series.source.startswith('support/'):
            narrative = (
                f'{display_name} is {status} at {float(latest.value):.2f} {display_unit}. '
                'This is a live funding-stress construct built from direct spot FX and official short-rate inputs.'
            )
        elif is_auction_series:
            narrative = (
                f'{display_name} is {status} at {float(latest.value):.2f} {display_unit}. '
                f'This is an event-driven stepped series and only changes when qualifying auctions occur. '
                f'The card is showing a {chart_window_label} window.'
            )
        return {
            'key': key,
            'name': display_name,
            'category': series.category,
            'unit': display_unit,
            'source': series.source,
            'source_class': source_class,
            'latest_value': round(float(latest.value), 2),
            'normalized_value': latest.normalized_value,
            'zscore': latest.zscore,
            'rate_of_change': latest.rate_of_change,
            'acceleration': latest.acceleration,
            'status': status,
            'warning_threshold': thresholds['warning'] if thresholds else None,
            'critical_threshold': thresholds['critical'] if thresholds else None,
            'direction': thresholds.get('direction', 'high') if thresholds else 'high',
            'chart_style': chart_style,
            'chart_window_label': chart_window_label,
            'narrative': narrative,
            'history': [
                {'timestamp': item.timestamp, 'value': round(float(item.value), 2)}
                for item in history_values
            ],
        }

    manual = _latest_manual_inputs(db).get(key)
    if manual is None:
        raise KeyError(key)
    name, category, unit = MANUAL_LABELS.get(key, (key.replace('_', ' ').title(), 'manual', 'score'))
    status = determine_status(float(manual.value), thresholds)
    source, source_class, narrative = _manual_overlay_source(key, manual)
    return {
        'key': key,
        'name': name,
        'category': category,
        'unit': unit,
        'source': source,
        'source_class': source_class,
        'latest_value': round(float(manual.value), 2),
        'normalized_value': None,
        'zscore': None,
        'rate_of_change': None,
        'acceleration': None,
        'status': status,
        'warning_threshold': thresholds['warning'] if thresholds else None,
        'critical_threshold': thresholds['critical'] if thresholds else None,
        'direction': thresholds.get('direction', 'high') if thresholds else 'high',
        'chart_style': chart_style,
        'chart_window_label': chart_window_label,
        'narrative': narrative,
        'history': [{'timestamp': manual.timestamp, 'value': round(float(manual.value), 2)}],
    }


def _regime_propagation_boost(explanation: dict[str, Any], regime_name: str) -> float:
    return float(
        explanation.get('propagation', {})
        .get('regime_effects', {})
        .get(regime_name, {})
        .get('total', 0.0)
    )


def _build_regime_overview(db: Session) -> dict[str, Any]:
    rows = db.query(RegimeScore).order_by(RegimeScore.timestamp.asc()).all()
    latest = rows[-1]
    sticky_values = [row.sticky_score for row in rows]
    convex_values = [row.convex_score for row in rows]
    break_values = [row.break_score for row in rows]
    explanation = latest.explanation_json
    return {
        'current_regime': explanation['current_regime'].replace('_', ' ').title(),
        'sticky': {
            'name': 'Sticky Inflation',
            'score': latest.sticky_score,
            'change_7d': rolling_change(sticky_values, 7),
            'change_30d': rolling_change(sticky_values, 30),
            'propagation_boost': _regime_propagation_boost(explanation, 'sticky'),
            'top_drivers': explanation['summary']['sticky'][:3],
        },
        'convex': {
            'name': 'Convex Inflation / Funding Stress',
            'score': latest.convex_score,
            'change_7d': rolling_change(convex_values, 7),
            'change_30d': rolling_change(convex_values, 30),
            'propagation_boost': _regime_propagation_boost(explanation, 'convex'),
            'top_drivers': explanation['summary']['convex'][:3],
        },
        'break': {
            'name': 'Break / Repression',
            'score': latest.break_score,
            'change_7d': rolling_change(break_values, 7),
            'change_30d': rolling_change(break_values, 30),
            'propagation_boost': _regime_propagation_boost(explanation, 'break'),
            'top_drivers': explanation['summary']['break'][:3],
        },
        'explanation': explanation,
        'history': [
            {
                'timestamp': row.timestamp,
                'sticky_score': row.sticky_score,
                'convex_score': row.convex_score,
                'break_score': row.break_score,
            }
            for row in rows[-90:]
        ],
    }


def _build_causal_chain(config: dict[str, Any], snapshots: dict[str, dict[str, Any]], explanation: dict[str, Any]) -> list[dict[str, Any]]:
    propagated = explanation.get('propagation', {}).get('node_states', {})
    nodes: list[dict[str, Any]] = []
    for key, indicators in config['causal_groups'].items():
        node_state = propagated.get(key)
        if node_state is not None:
            score = float(node_state['propagated_score'])
            base_score = float(node_state['base_score'])
            incoming_pressure = float(node_state['incoming_pressure'])
            top_upstream = ', '.join(item['source'].replace('_', ' ') for item in node_state.get('top_upstream', [])[:2]) or 'no active upstream loop'
            top_inputs = ', '.join(item['indicator'].replace('_', ' ') for item in node_state.get('inputs', [])[:2]) or 'none'
            explanation_text = (
                f'Base {base_score:.0f}, propagated {score:.0f}, loop pressure {incoming_pressure:.0f}. '
                f'Inputs: {top_inputs}. Feedback from {top_upstream}.'
            )
        else:
            relevant = [snapshots[indicator] for indicator in indicators if indicator in snapshots]
            values = [item['normalized_value'] for item in relevant if item['normalized_value'] is not None]
            score = round(sum(float(value) for value in values) / len(values), 2) if values else 0.0
            base_score = None
            incoming_pressure = None
            top = max(relevant, key=lambda item: float(item['normalized_value'] or 0.0), default=None)
            explanation_text = f"Grouped first-order stress from {top['name'] if top else 'available indicators'}."
        nodes.append(
            {
                'key': key,
                'label': CAUSAL_LABELS.get(key, key.replace('_', ' ').title()),
                'status': determine_status(score, {'warning': 50, 'critical': 75, 'direction': 'high'}),
                'score': round(score, 2),
                'base_score': round(base_score, 2) if base_score is not None else None,
                'incoming_pressure': round(incoming_pressure, 2) if incoming_pressure is not None else None,
                'explanation': explanation_text,
            }
        )
    return nodes


def _build_crisis_monitor(config: dict[str, Any], snapshots: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    crisis_items: list[dict[str, Any]] = []
    active_count = 0
    for key, label in CRISIS_KEYS:
        snapshot = snapshots.get(key)
        if snapshot is None:
            continue
        if snapshot['status'] in {'orange', 'red'}:
            active_count += 1
        crisis_items.append(
            {
                'key': key,
                'label': label,
                'value': snapshot['latest_value'],
                'status': snapshot['status'],
                'explanation': snapshot['narrative'],
            }
        )
    systemic_alert = active_count >= int(config['alert_rules']['systemic_warning_count']['warning'])
    return crisis_items, systemic_alert


def _format_stage_label(score: float) -> str:
    if score >= 75:
        return 'dominant'
    if score >= 60:
        return 'active'
    if score >= 45:
        return 'building'
    return 'background'


def _indicator_score(snapshot: dict[str, Any]) -> float:
    source_class = snapshot.get('source_class') or 'demo'
    confidence = SOURCE_CONFIDENCE.get(source_class, 0.0)
    normalized = snapshot.get('normalized_value')
    if normalized is None:
        warning = snapshot.get('warning_threshold')
        critical = snapshot.get('critical_threshold')
        direction = snapshot.get('direction', 'high')
        if warning is not None and critical is not None:
            normalized = normalize_value(
                float(snapshot['latest_value']),
                {'warning': warning, 'critical': critical, 'direction': direction},
            )
    if normalized is None:
        return 0.0
    return round(float(normalized) * confidence, 2)


def _raw_indicator_score(snapshot: dict[str, Any]) -> float:
    normalized = snapshot.get('normalized_value')
    if normalized is None:
        warning = snapshot.get('warning_threshold')
        critical = snapshot.get('critical_threshold')
        direction = snapshot.get('direction', 'high')
        if warning is not None and critical is not None:
            normalized = normalize_value(
                float(snapshot['latest_value']),
                {'warning': warning, 'critical': critical, 'direction': direction},
            )
    if normalized is None:
        return 0.0
    return round(float(normalized), 2)


def _stage_input_confidence(snapshot: dict[str, Any]) -> float:
    source_class = snapshot.get('source_class') or 'demo'
    source = snapshot.get('source') or ''
    if source_class == 'live' and source.startswith('support/'):
        return 0.8
    return SOURCE_CONFIDENCE.get(source_class, 0.0)


def _stage_confidence_label(confidence: float) -> str:
    if confidence >= 0.9:
        return 'high confidence'
    if confidence >= 0.7:
        return 'medium confidence'
    if confidence > 0.0:
        return 'low confidence'
    return 'demo-only'


def _build_stage_scores(snapshots: dict[str, dict[str, Any]]) -> dict[str, float]:
    stage_inputs = {
        'physical': ['brent_prompt_spread', 'tanker_freight_proxy', 'marine_insurance_stress', 'hormuz_tanker_transit_stress', 'gulf_crude_dislocation'],
        'domestic': ['household_real_income_squeeze', 'employment_tax_base_proxy', 'tax_receipts_market_stress', 'consumer_credit_stress'],
        'financial': ['jpy_usd_basis', 'synthetic_usd_funding_pressure', 'auction_stress', 'treasury_liquidity_proxy', 'fima_repo_usage'],
    }
    scores: dict[str, float] = {}
    for stage, keys in stage_inputs.items():
        values = [_indicator_score(snapshots[key]) for key in keys if key in snapshots]
        scores[stage] = round(sum(values) / len(values), 2) if values else 0.0
    return scores


def _build_ordering_framework(snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stages = [
        ('Shock', ['brent_prompt_spread', 'marine_insurance_stress', 'hormuz_tanker_transit_stress']),
        ('Income Squeeze', ['external_importer_stress', 'household_real_income_squeeze', 'employment_tax_base_proxy']),
        ('Labor / Receipts', ['payroll_momentum', 'employment_tax_base_proxy', 'tax_receipts_market_stress']),
        ('Financial Tightening', ['jpy_usd_basis', 'synthetic_usd_funding_pressure', 'auction_stress', 'fima_repo_usage']),
    ]
    items = []
    for label, keys in stages:
        relevant = [snapshots[key] for key in keys if key in snapshots]
        raw_values = [_raw_indicator_score(snapshot) for snapshot in relevant]
        raw_score = round(sum(raw_values) / len(raw_values), 2) if raw_values else 0.0
        confidence_values = [_stage_input_confidence(snapshot) for snapshot in relevant]
        confidence_score = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.0
        items.append(
            {
                'label': label,
                'score': raw_score,
                'status': _format_stage_label(raw_score),
                'confidence_score': confidence_score,
                'confidence_label': _stage_confidence_label(confidence_score),
            }
        )
    lead = max(items, key=lambda item: item['score']) if items else {
        'label': 'Shock',
        'score': 0.0,
        'status': 'background',
        'confidence_score': 0.0,
        'confidence_label': 'demo-only',
    }
    summary = (
        'Ordering discipline: physical shock first, household real-income squeeze next, then labor / receipts damage, '
        'and finally broader financial tightening and Fed plumbing stress.'
    )
    return {
        'summary': summary,
        'lead_stage': lead['label'],
        'lead_score': lead['score'],
        'lead_confidence_label': lead['confidence_label'],
        'items': items,
    }


def _build_stagflation_overview(snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    inflation_keys = ['brent_prompt_spread', 'expected_inflation_5y5y', 'expectations_entrenchment_score', 'wage_stickiness']
    growth_keys = ['household_real_income_squeeze', 'payroll_momentum', 'temp_help_stress', 'consumer_credit_stress']
    policy_keys = ['move_index', 'auction_stress', 'fima_repo_usage', 'fed_swap_line_usage']
    inflation_values = [_indicator_score(snapshots[key]) for key in inflation_keys if key in snapshots]
    growth_values = [_indicator_score(snapshots[key]) for key in growth_keys if key in snapshots]
    policy_values = [_indicator_score(snapshots[key]) for key in policy_keys if key in snapshots]
    inflation_score = round(sum(inflation_values) / len(inflation_values), 2) if inflation_values else 0.0
    growth_score = round(sum(growth_values) / len(growth_values), 2) if growth_values else 0.0
    policy_score = round(sum(policy_values) / len(policy_values), 2) if policy_values else 0.0
    composite = round((inflation_score + growth_score + policy_score) / 3.0, 2)
    summary = (
        f'Stagflation risk is {_format_stage_label(composite)}. Inflation pressure scores {inflation_score:.1f}, '
        f'real-activity impairment scores {growth_score:.1f}, and policy constraint scores {policy_score:.1f}.'
    )
    return {
        'summary': summary,
        'composite_score': composite,
        'status': _format_stage_label(composite),
        'inflation_score': inflation_score,
        'growth_score': growth_score,
        'policy_constraint_score': policy_score,
    }


def _build_migration_overview(snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stages = _build_stage_scores(snapshots)
    spread = round(stages['financial'] - stages['physical'], 2)
    if stages['financial'] >= 60 and stages['physical'] >= 60:
        summary = 'The shock is broadening from physical oil dislocation into funding, Treasury-demand, and Fed-plumbing stress.'
    elif stages['physical'] >= 60:
        summary = 'The shock is still predominantly physical. Funding and Treasury channels are not yet leading the move.'
    else:
        summary = 'Physical and financial stress remain mixed. The migration into broader nominal stress is incomplete.'
    return {
        'summary': summary,
        'physical_score': stages['physical'],
        'domestic_score': stages['domestic'],
        'financial_score': stages['financial'],
        'financial_minus_physical': spread,
    }


def _build_narratives(
    regime: dict[str, Any],
    alerts: list[Any],
    state_space: dict[str, Any],
    backtest: dict[str, Any],
    ordering_framework: dict[str, Any],
    stagflation_overview: dict[str, Any],
    migration_overview: dict[str, Any],
) -> dict[str, str]:
    dominant_key = regime['explanation']['current_regime']
    dominant_card = regime[dominant_key if dominant_key != 'break' else 'break']
    drivers = dominant_card['top_drivers'][:3]
    propagation_nodes = regime['explanation'].get('propagation', {}).get('node_states', {})
    amplified = [
        node.replace('_', ' ')
        for node, state in propagation_nodes.items()
        if float(state.get('amplification', 0.0)) > 0
    ][:3]
    amplified_text = ', '.join(amplified) if amplified else 'no major recursive amplification yet'
    daily = (
        f"Current regime is {regime['current_regime']}. {ordering_framework['summary']} {migration_overview['summary']} "
        f"Top drivers are {', '.join(drivers) if drivers else 'not available'}. Recursive amplification is strongest in {amplified_text}."
    )
    weekly = (
        f"Stagflation framing: {stagflation_overview['summary']} The closest historical family is "
        f"{backtest.get('dominant_cluster_label', 'unclassified')} at {backtest.get('cluster_confidence', 0.0) * 100:.0f}% confidence."
    )
    top_alerts = ', '.join(_alert_field(alert, 'title') for alert in alerts[:3]) if alerts else 'no active alerts'
    escalation = (
        f"Escalation watch: {top_alerts}. Econometric regime is {state_space['current_regime'].replace('_', ' ')} "
        f"at {state_space['current_probability']:.1f}% probability."
    )
    return {'daily': daily, 'weekly': weekly, 'escalation': escalation}


def _build_panels(config: dict[str, Any], snapshots: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    panels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group, entries in PANEL_LAYOUT.items():
        for panel in entries:
            panels[group].append(
                {
                    'id': panel['id'],
                    'title': panel['title'],
                    'description': panel['description'],
                    'indicators': [snapshots[key] for key in panel['series'] if key in snapshots],
                }
            )
    return panels


def _derive_data_mode(snapshots: dict[str, dict[str, Any]], keys: list[str]) -> str:
    relevant = [snapshots[key] for key in keys if key in snapshots]
    if not relevant:
        return 'demo'

    source_classes = {item.get('source_class') or 'demo' for item in relevant}
    if source_classes == {'live'}:
        return 'live'
    if source_classes == {'demo'}:
        return 'demo'
    return 'mixed'


def _avg_normalized(snapshots: dict[str, dict[str, Any]], keys: list[str]) -> float:
    values = [snapshots[key]['normalized_value'] for key in keys if key in snapshots and snapshots[key]['normalized_value'] is not None]
    if not values:
        return 0.0
    return round(sum(float(value) for value in values) / len(values), 4)


def _build_interpretation_chart(snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sticky_keys = ['brent_prompt_spread', 'wti_prompt_spread', 'tanker_freight_proxy', 'household_real_income_squeeze']
    convex_keys = ['jpy_usd_basis', 'sofr_spread', 'move_index', 'synthetic_usd_funding_pressure', 'external_importer_stress']
    break_keys = ['auction_stress', 'treasury_liquidity_proxy', 'fima_repo_usage', 'tax_receipts_market_stress']

    timeline_lookup: dict[Any, dict[str, float]] = {}
    for key in sticky_keys + convex_keys + break_keys:
        snapshot = snapshots.get(key)
        if snapshot is None:
            continue
        for point in snapshot['history'][-90:]:
            timeline_lookup.setdefault(point['timestamp'], {})[key] = float(point['value'])

    ordered_timestamps = sorted(timeline_lookup.keys())
    series: list[dict[str, Any]] = []
    for timestamp in ordered_timestamps:
        current: dict[str, dict[str, float]] = {}
        for key in sticky_keys + convex_keys + break_keys:
            snapshot = snapshots.get(key)
            if snapshot is None:
                continue
            value = timeline_lookup[timestamp].get(key)
            if value is None:
                continue
            warning = snapshot['warning_threshold']
            critical = snapshot['critical_threshold']
            direction = snapshot['direction']
            normalized = 0.0
            if warning is not None and critical is not None:
                normalized = normalize_value(
                    value,
                    {'warning': warning, 'critical': critical, 'direction': direction},
                ) or 0.0
            confidence = SOURCE_CONFIDENCE.get(snapshot.get('source_class') or 'demo', 0.0)
            normalized = round(normalized * confidence, 2)
            current[key] = {'normalized_value': normalized}
        sticky_score = _avg_normalized(current, sticky_keys)
        convex_score = _avg_normalized(current, convex_keys)
        break_score = _avg_normalized(current, break_keys)
        interpretation_value = round(max(sticky_score, convex_score, break_score), 2)
        series.append({'timestamp': timestamp, 'value': interpretation_value})

    return {
        'series': series,
        'thresholds': [
            {'label': 'Sticky Threshold', 'value': 45.0, 'color': '#f59e0b'},
            {'label': 'Convex Threshold', 'value': 60.0, 'color': '#38bdf8'},
            {'label': 'Break Threshold', 'value': 75.0, 'color': '#ef4444'},
        ],
    }


def get_dashboard_overview(db: Session) -> dict[str, Any]:
    seed_demo_data(db)
    config = load_effective_config(db)
    series_map = _build_series_map(db)
    manual_map = _latest_manual_inputs(db)
    snapshot_keys = set(series_map.keys()) | set(manual_map.keys())
    snapshots = {key: _build_indicator_snapshot(key, series_map, config, db) for key in snapshot_keys}
    regime = _build_regime_overview(db)
    state_space = evaluate_state_space(snapshots, config, regime['current_regime'])
    backtest = build_backtest_overview(snapshots, regime, state_space)

    stored_alerts = (
        db.query(Alert)
        .order_by(Alert.timestamp.desc(), Alert.severity.desc())
        .all()
        if get_alerts_enabled(db)
        else []
    )
    live_state_space_alerts = (
        build_state_space_alerts(state_space, backtest, datetime.now(timezone.utc))
        if get_alerts_enabled(db)
        else []
    )
    alerts = [*stored_alerts, *live_state_space_alerts]
    alerts.sort(
        key=lambda alert: (str(_alert_field(alert, 'severity')), _normalize_alert_timestamp(_alert_field(alert, 'timestamp'))),
        reverse=True,
    )

    crisis_monitor, systemic_alert = _build_crisis_monitor(config, snapshots)
    event_annotations = db.query(EventAnnotation).order_by(EventAnnotation.timestamp.desc()).limit(25).all()
    source_status = get_source_status(db)
    providers = dict(source_status.get('providers', {}))
    providers['ig_cds_status'] = 'Not included in live scoring because a clean direct public IG CDS feed is not yet available.'
    current_data_mode = _derive_data_mode(snapshots, HEADLINE_KEYS)
    ordering_framework = _build_ordering_framework(snapshots)
    stagflation_overview = _build_stagflation_overview(snapshots)
    migration_overview = _build_migration_overview(snapshots)

    return {
        'generated_at': datetime.now(timezone.utc),
        'data_mode': current_data_mode,
        'regime': regime,
        'state_space': state_space,
        'backtest': backtest,
        'headline_indicators': [snapshots[key] for key in HEADLINE_KEYS if key in snapshots],
        'causal_chain': _build_causal_chain(config, snapshots, regime['explanation']),
        'crisis_monitor': crisis_monitor,
        'systemic_stress_alert': systemic_alert,
        'alerts': [_serialize_alert(alert) for alert in alerts[:20]],
        'narratives': _build_narratives(
            regime,
            alerts,
            state_space,
            backtest,
            ordering_framework,
            stagflation_overview,
            migration_overview,
        ),
        'panels': _build_panels(config, snapshots),
        'manual_inputs': [
            {
                'id': item.id,
                'timestamp': item.timestamp,
                'key': item.key,
                'value': item.value,
                'notes': item.notes,
            }
            for item in manual_map.values()
        ],
        'event_annotations': [
            {
                'id': item.id,
                'timestamp': item.timestamp,
                'title': item.title,
                'description': item.description,
                'related_series': item.related_series,
                'severity': item.severity,
            }
            for item in event_annotations
        ],
        'source_status': providers,
        'interpretation_chart': _build_interpretation_chart(snapshots),
        'ordering_framework': ordering_framework,
        'stagflation_overview': stagflation_overview,
        'migration_overview': migration_overview,
    }
