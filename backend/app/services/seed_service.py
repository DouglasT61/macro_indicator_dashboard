from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerts.engine import build_alerts
from app.collectors.demo_collector import generate_demo_history
from app.collectors.marine_insurance import collect_marine_insurance_assessment
from app.collectors.public_data import PublicDataCollector
from app.collectors.public_manual_overlays import (
    collect_central_bank_intervention_signal,
    collect_geopolitical_escalation_signal,
    collect_governance_fragmentation_signal,
    collect_iaea_nuclear_ambiguity,
    collect_interceptor_depletion_signal,
    collect_p_and_i_circular_stress,
    collect_private_credit_stress,
)
from app.collectors.public_shipping import collect_hormuz_transit_assessment, collect_tanker_disruption_assessment
from app.core.config import get_settings
from app.models import Alert, AppSetting, EventAnnotation, IndicatorSeries, IndicatorValue, ManualInput, RegimeScore
from app.regime_engine.config_loader import load_file_config
from app.regime_engine.engine import build_regime_history
from app.seed.catalog import MANUAL_INPUT_DEFAULTS, SERIES_DEFINITIONS
from app.services.analytics import compute_series_metrics, determine_status
from app.services.settings_service import get_imported_series_keys, get_source_status, save_imported_series_keys, save_source_status


LIVE_HISTORY_DAYS = 180
settings = get_settings()

HORMUZ_TRAFFIC_SETTING_KEY = 'hormuz_traffic_stats'


def _upsert_hormuz_traffic_stats(db: Session, stats: object) -> None:
    """Persist PortWatch tanker-count statistics to AppSetting for dashboard display."""
    from app.collectors.public_shipping import HormuzTrafficStats
    if not isinstance(stats, HormuzTrafficStats):
        return
    payload = {
        'latest_count': stats.latest_count,
        'avg_30d': stats.avg_30d,
        'avg_longterm': stats.avg_longterm,
        'latest_date': stats.latest_date,
        'source': 'portwatch/hormuz-transits',
    }
    setting = db.query(AppSetting).filter(AppSetting.key == HORMUZ_TRAFFIC_SETTING_KEY).one_or_none()
    if setting is None:
        from datetime import datetime, timezone
        setting = AppSetting(key=HORMUZ_TRAFFIC_SETTING_KEY, value_json=payload, updated_at=datetime.now(timezone.utc))
        db.add(setting)
    else:
        setting.value_json = payload
        from datetime import datetime, timezone
        setting.updated_at = datetime.now(timezone.utc)
    db.commit()


def ensure_series_registry(db: Session) -> dict[str, IndicatorSeries]:
    series_lookup: dict[str, IndicatorSeries] = {}
    for definition in SERIES_DEFINITIONS:
        existing = db.query(IndicatorSeries).filter(IndicatorSeries.key == definition.key).one_or_none()
        if existing is None:
            existing = IndicatorSeries(
                key=definition.key,
                name=definition.name,
                category=definition.category,
                source=definition.source,
                frequency=definition.frequency,
                unit=definition.unit,
                description=definition.description,
            )
            db.add(existing)
            db.flush()
        else:
            existing.name = definition.name
            existing.category = definition.category
            existing.frequency = definition.frequency
            existing.unit = definition.unit
            existing.description = definition.description
        series_lookup[definition.key] = existing
    db.commit()
    return series_lookup


def get_manual_inputs_lookup(db: Session) -> dict[str, float]:
    latest_inputs: dict[str, float] = {}
    for row in db.query(ManualInput).order_by(ManualInput.timestamp.asc()).all():
        latest_inputs[row.key] = row.value
    return latest_inputs


def seed_manual_inputs(db: Session) -> bool:
    existing_keys = {row[0] for row in db.query(ManualInput.key).distinct().all()}
    missing_keys = [key for key in MANUAL_INPUT_DEFAULTS if key not in existing_keys]
    if not missing_keys:
        return False
    now = datetime.now(timezone.utc)
    for key in missing_keys:
        db.add(ManualInput(timestamp=now, key=key, value=MANUAL_INPUT_DEFAULTS[key], notes='Seeded demo default'))
    db.commit()
    return True


def seed_events(db: Session) -> None:
    if db.query(EventAnnotation).count() > 0:
        return

    now = datetime.now(timezone.utc)
    events = [
        EventAnnotation(
            timestamp=now - timedelta(days=62),
            title='Insurance premiums jump after Gulf escalation',
            description='Manual sample event to illustrate marine insurance stress annotations.',
            related_series=['marine_insurance_stress', 'tanker_freight_proxy', 'brent_prompt_spread'],
            severity='warning',
        ),
        EventAnnotation(
            timestamp=now - timedelta(days=34),
            title='Weak 30Y auction and higher MOVE',
            description='Sample sovereign duration stress event.',
            related_series=['auction_stress', 'move_index', 'thirty_year_yield'],
            severity='warning',
        ),
        EventAnnotation(
            timestamp=now - timedelta(days=13),
            title='FIMA usage rises for multiple sessions',
            description='Sample central-bank plumbing event.',
            related_series=['fima_repo_usage', 'fed_swap_line_usage'],
            severity='critical',
        ),
    ]
    db.add_all(events)
    db.commit()


def _replace_series_values(
    db: Session,
    series: IndicatorSeries,
    records: list[dict],
    source_override: str | None = None,
    *,
    commit: bool = True,
) -> None:
    db.query(IndicatorValue).filter(IndicatorValue.series_id == series.id).delete()
    db.flush()
    for record in records:
        db.add(
            IndicatorValue(
                series_id=series.id,
                timestamp=record['timestamp'],
                value=float(record['value']),
                normalized_value=record['normalized_value'],
                zscore=record['zscore'],
                moving_average_7=record['moving_average_7'],
                moving_average_30=record['moving_average_30'],
                percentile=record['percentile'],
                rate_of_change=record['rate_of_change'],
                acceleration=record['acceleration'],
            )
        )
    if source_override is not None:
        series.source = source_override
    series.last_updated = records[-1]['timestamp'] if records else None
    if commit:
        db.commit()
    else:
        db.flush()


def _recompute_regime_scores(db: Session, config: dict, *, commit: bool = True) -> None:
    series_lookup = {series.key: series for series in db.query(IndicatorSeries).all()}
    timelines: dict[str, list[tuple[datetime, float]]] = {}
    for key, series in series_lookup.items():
        values = db.execute(
            select(IndicatorValue.timestamp, IndicatorValue.value)
            .where(IndicatorValue.series_id == series.id)
            .order_by(IndicatorValue.timestamp.asc())
        ).all()
        if values:
            timelines[key] = [(row[0], float(row[1])) for row in values]

    db.query(RegimeScore).delete()
    db.flush()
    history = build_regime_history(timelines, get_manual_inputs_lookup(db), config)
    for row in history:
        db.add(
            RegimeScore(
                timestamp=row['timestamp'],
                sticky_score=row['sticky_score'],
                convex_score=row['convex_score'],
                break_score=row['break_score'],
                explanation_json=row['explanation'],
            )
        )
    if commit:
        db.commit()
    else:
        db.flush()


def _recompute_alerts(db: Session, config: dict, *, commit: bool = True) -> None:
    latest_values: dict[str, float] = {}
    recent_history: dict[str, list[float]] = {}
    for series in db.query(IndicatorSeries).all():
        values = (
            db.query(IndicatorValue)
            .filter(IndicatorValue.series_id == series.id)
            .order_by(IndicatorValue.timestamp.asc())
            .all()
        )
        if values:
            latest_values[series.key] = float(values[-1].value)
            recent_history[series.key] = [float(item.value) for item in values[-5:]]

    crisis_keys = ['treasury_liquidity_proxy', 'sofr_spread', 'treasury_basis_proxy', 'jpy_usd_basis', 'brent_prompt_spread']
    systemic_warning_count = sum(
        1
        for key in crisis_keys
        if determine_status(latest_values.get(key, 0.0), config['thresholds'].get(key)) in {'orange', 'red'}
    )
    alerts = build_alerts(
        latest_values=latest_values,
        recent_history=recent_history,
        config=config,
        generated_at=datetime.now(timezone.utc),
        systemic_warning_count=systemic_warning_count,
    )

    db.query(Alert).delete()
    db.flush()
    for alert in alerts:
        db.add(Alert(**alert))
    if commit:
        db.commit()
    else:
        db.flush()


def _upsert_manual_overlay(db: Session, key: str, value: float, notes: str, *, commit: bool = True) -> None:
    latest = (
        db.query(ManualInput)
        .filter(ManualInput.key == key)
        .order_by(ManualInput.timestamp.desc())
        .first()
    )
    if latest and round(float(latest.value), 2) == round(float(value), 2) and latest.notes == notes:
        return

    db.add(
        ManualInput(
            timestamp=datetime.now(timezone.utc),
            key=key,
            value=value,
            notes=notes,
        )
    )
    if commit:
        db.commit()
    else:
        db.flush()


def _refresh_public_overlays(
    db: Session,
    status_callback: Callable[[str], None] | None = None,
    *,
    commit: bool = True,
) -> str:
    messages: list[str] = []

    try:
        if status_callback:
            status_callback('Refreshing overlay: marine_insurance_stress')
        marine = collect_marine_insurance_assessment(timeout_seconds=8.0)
        _upsert_manual_overlay(db, 'marine_insurance_stress', marine.score, marine.notes, commit=commit)
        messages.append('Marine insurance overlay refreshed from Beinsure site scan.')
    except Exception:
        messages.append('Marine insurance overlay remains manual/demo; site scan unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: tanker_disruption_score')
        tanker = collect_tanker_disruption_assessment(settings.aishub_username, timeout_seconds=8.0)
        _upsert_manual_overlay(db, 'tanker_disruption_score', tanker.score, tanker.notes, commit=commit)
        messages.append('Tanker disruption overlay refreshed from public shipping sources.')
    except Exception:
        messages.append('Tanker disruption overlay remains manual/demo; public shipping sources unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: private_credit_stress')
        private_credit = collect_private_credit_stress(timeout_seconds=8.0)
        _upsert_manual_overlay(db, private_credit.key, private_credit.value, private_credit.notes, commit=commit)
        messages.append('Private credit overlay refreshed from public market proxies.')
    except Exception:
        messages.append('Private credit overlay remains manual/demo; public market proxies unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: geopolitical_escalation_toggle')
        geopolitical = collect_geopolitical_escalation_signal(timeout_seconds=8.0)
        _upsert_manual_overlay(db, geopolitical.key, geopolitical.value, geopolitical.notes, commit=commit)
        messages.append('Geopolitical escalation toggle refreshed from public news scan.')
    except Exception:
        messages.append('Geopolitical escalation toggle remains manual/demo; public news scan unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: central_bank_intervention_toggle')
        intervention = collect_central_bank_intervention_signal(timeout_seconds=8.0)
        _upsert_manual_overlay(db, intervention.key, intervention.value, intervention.notes, commit=commit)
        messages.append('Central bank intervention toggle refreshed from official Fed feeds.')
    except Exception:
        messages.append('Central bank intervention toggle remains manual/demo; official Fed feeds unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: p_and_i_circular_stress')
        pni = collect_p_and_i_circular_stress(timeout_seconds=8.0)
        _upsert_manual_overlay(db, pni.key, pni.value, pni.notes, commit=commit)
        messages.append('P&I circular stress refreshed from official club notices.')
    except Exception:
        messages.append('P&I circular stress remains manual/demo; official club notices unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: iaea_nuclear_ambiguity')
        iaea = collect_iaea_nuclear_ambiguity(timeout_seconds=8.0)
        _upsert_manual_overlay(db, iaea.key, iaea.value, iaea.notes, commit=commit)
        messages.append('IAEA nuclear ambiguity refreshed from official verification statements.')
    except Exception:
        messages.append('IAEA nuclear ambiguity remains manual/demo; official verification statements unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: interceptor_depletion')
        interceptor = collect_interceptor_depletion_signal(timeout_seconds=8.0)
        _upsert_manual_overlay(db, interceptor.key, interceptor.value, interceptor.notes, commit=commit)
        messages.append('Interceptor depletion refreshed from operational reporting.')
    except Exception:
        messages.append('Interceptor depletion remains manual/demo; operational reporting unavailable on this refresh.')

    try:
        if status_callback:
            status_callback('Refreshing overlay: governance_fragmentation')
        fragmentation = collect_governance_fragmentation_signal(timeout_seconds=8.0)
        _upsert_manual_overlay(db, fragmentation.key, fragmentation.value, fragmentation.notes, commit=commit)
        messages.append('Governance fragmentation refreshed from conflict and statement scans.')
    except Exception:
        messages.append('Governance fragmentation remains manual/demo; conflict and statement scans unavailable on this refresh.')

    return ' '.join(messages)


def _build_demo_baseline(end_date: date | None = None) -> dict[str, list[tuple[datetime, float]]]:
    return generate_demo_history(days=LIVE_HISTORY_DAYS, end_date=end_date)


def _build_series_payloads(
    end_date: date | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[dict[str, list[tuple[datetime, float]]], dict[str, str], dict[str, str], str]:
    baseline = _build_demo_baseline(end_date=end_date)
    source_map = {definition.key: definition.source for definition in SERIES_DEFINITIONS}
    provider_messages = {
        'market_data': 'Seeded demo data active. Add API keys or import CSVs for live extensions.',
        'treasury': 'Demo adapter in use; public API connectors can be added without breaking the app.',
        'manual_overlays': 'Persisted in SQLite and included in regime scoring.',
        'futures_market': 'Direct futures chain layer is inactive; demo/proxy fallback remains in place.',
        'shipping_data': 'Demo shipping chokepoint data active; PortWatch integration can override Hormuz transit stress when available.',
    }
    data_mode = 'demo'

    try:
        collection = PublicDataCollector(timeout_seconds=12.0).collect(
            days=LIVE_HISTORY_DAYS,
            end_date=end_date,
            status_callback=status_callback,
        )
    except Exception:
        return baseline, source_map, provider_messages, data_mode

    for key, collected in collection.series.items():
        baseline[key] = collected.history
        source_map[key] = collected.source

    provider_messages['market_data'] = collection.provider_status.get(
        'fred',
        provider_messages['market_data'],
    )
    if collection.provider_status.get('ecb'):
        provider_messages['market_data'] = f"{provider_messages['market_data']} {collection.provider_status['ecb']}"
    if collection.provider_status.get('support'):
        provider_messages['market_data'] = f"{provider_messages['market_data']} {collection.provider_status['support']}"
    provider_messages['treasury'] = collection.provider_status.get(
        'treasury',
        provider_messages['treasury'],
    )
    provider_messages['futures_market'] = collection.provider_status.get(
        'yahoo_market',
        provider_messages['futures_market'],
    )
    for key, message in collection.provider_status.items():
        if key in {'fred', 'ecb', 'treasury', 'yahoo_market', 'support'}:
            provider_messages[f'{key}_status'] = message
    try:
        if status_callback:
            status_callback('shipping_data: portwatch_hormuz')
        hormuz = collect_hormuz_transit_assessment(timeout_seconds=8.0)
        baseline['hormuz_tanker_transit_stress'] = hormuz.history
        source_map['hormuz_tanker_transit_stress'] = hormuz.source
        provider_messages['shipping_data'] = 'PortWatch Strait of Hormuz tanker transit data is live.'
        if hormuz.traffic_stats is not None:
            _upsert_hormuz_traffic_stats(db, hormuz.traffic_stats)
    except Exception:
        provider_messages['shipping_data'] = 'PortWatch Hormuz transit data unavailable on this refresh; demo fallback remains active.'

    live_count = sum(1 for source in source_map.values() if not source.startswith('demo/'))
    if live_count == 0:
        data_mode = 'demo'
    elif live_count == len(source_map):
        data_mode = 'live'
    else:
        data_mode = 'mixed'
    return baseline, source_map, provider_messages, data_mode


def seed_demo_data(db: Session) -> None:
    config = load_file_config()
    series_lookup = ensure_series_registry(db)
    existing_value_count = db.query(IndicatorValue).count()

    if existing_value_count > 0:
        missing_definitions = [
            definition
            for definition in SERIES_DEFINITIONS
            if db.query(IndicatorValue).filter(IndicatorValue.series_id == series_lookup[definition.key].id).count() == 0
        ]
        if not missing_definitions:
            added_manuals = seed_manual_inputs(db)
            if added_manuals:
                source_status = get_source_status(db)
                providers = dict(source_status.get('providers', {}))
                providers['manual_overlays'] = _refresh_public_overlays(db)
                save_source_status(db, source_status.get('data_mode', 'mixed'), providers)
                _recompute_regime_scores(db, config)
                _recompute_alerts(db, config)
            seed_events(db)
            return

        history_map, source_map, provider_messages, data_mode = _build_series_payloads()
        for definition in missing_definitions:
            history = history_map[definition.key]
            records = compute_series_metrics(history, config['thresholds'].get(definition.key))
            _replace_series_values(db, series_lookup[definition.key], records, source_override=source_map.get(definition.key))

        seed_manual_inputs(db)
        provider_messages['manual_overlays'] = _refresh_public_overlays(db)
        seed_events(db)
        save_source_status(db, data_mode, provider_messages)
        _recompute_regime_scores(db, config)
        _recompute_alerts(db, config)
        return

    history_map, source_map, provider_messages, data_mode = _build_series_payloads()

    for definition in SERIES_DEFINITIONS:
        history = history_map[definition.key]
        records = compute_series_metrics(history, config['thresholds'].get(definition.key))
        _replace_series_values(db, series_lookup[definition.key], records, source_override=source_map.get(definition.key))

    seed_manual_inputs(db)
    provider_messages['manual_overlays'] = _refresh_public_overlays(db)
    seed_events(db)
    save_source_status(db, data_mode, provider_messages)
    _recompute_regime_scores(db, config)
    _recompute_alerts(db, config)


def bootstrap_demo_only(db: Session) -> None:
    config = load_file_config()
    series_lookup = ensure_series_registry(db)
    existing_value_count = db.query(IndicatorValue).count()

    if existing_value_count > 0:
        seed_manual_inputs(db)
        seed_events(db)
        return

    history_map = generate_demo_history(days=LIVE_HISTORY_DAYS)
    for definition in SERIES_DEFINITIONS:
        history = history_map[definition.key]
        records = compute_series_metrics(history, config['thresholds'].get(definition.key))
        source_override = definition.source if definition.source.startswith('demo/') else f'demo/{definition.source}'
        _replace_series_values(db, series_lookup[definition.key], records, source_override=source_override)

    seed_manual_inputs(db)
    seed_events(db)
    save_source_status(
        db,
        'demo',
        {
            'market_data': 'Startup bootstrap seeded deterministic demo baseline.',
            'treasury': 'Startup bootstrap seeded deterministic demo baseline.',
            'manual_overlays': 'Startup bootstrap seeded deterministic manual defaults.',
            'futures_market': 'Startup bootstrap seeded deterministic demo baseline.',
            'shipping_data': 'Startup bootstrap seeded deterministic demo baseline.',
        },
    )
    _recompute_regime_scores(db, config)
    _recompute_alerts(db, config)


def ensure_bootstrap_state(db: Session) -> None:
    ensure_series_registry(db)
    seed_manual_inputs(db)
    seed_events(db)
    existing_status = db.query(IndicatorValue.id).first()
    if existing_status is None:
        save_source_status(
            db,
            'initializing',
            {
                'market_data': 'Awaiting first live refresh.',
                'treasury': 'Awaiting first live refresh.',
                'manual_overlays': 'Manual defaults seeded; overlay refresh pending.',
                'futures_market': 'Awaiting first live refresh.',
                'shipping_data': 'Awaiting first live refresh.',
                'refresh_status': 'Awaiting first live refresh.',
            },
        )


def refresh_market_data(db: Session, config: dict) -> None:
    series_lookup = ensure_series_registry(db)
    seed_manual_inputs(db)
    imported_series_keys = get_imported_series_keys(db)
    def _set_refresh_phase(message: str) -> None:
        save_source_status(
            db,
            get_source_status(db).get('data_mode', 'mixed'),
            {**dict(get_source_status(db).get('providers', {})), 'refresh_status': message},
            commit=False,
        )

    history_map, source_map, provider_messages, data_mode = _build_series_payloads(
        status_callback=_set_refresh_phase,
    )

    _set_refresh_phase('Applying refreshed series to database')

    for definition in SERIES_DEFINITIONS:
        if definition.key in imported_series_keys:
            continue
        history = history_map[definition.key]
        records = compute_series_metrics(history, config['thresholds'].get(definition.key))
        _replace_series_values(
            db,
            series_lookup[definition.key],
            records,
            source_override=source_map.get(definition.key),
            commit=False,
        )

    _set_refresh_phase('Refreshing manual overlays')
    provider_messages['manual_overlays'] = _refresh_public_overlays(
        db,
        status_callback=_set_refresh_phase,
        commit=False,
    )
    if imported_series_keys:
        provider_messages['manual_overlays'] = (
            f"{provider_messages['manual_overlays']} Imported series preserved: {', '.join(sorted(imported_series_keys))}."
        ).strip()

    _set_refresh_phase('Saving source status')
    save_source_status(db, data_mode, provider_messages, commit=False)

    _set_refresh_phase('Recomputing regime scores')
    _recompute_regime_scores(db, config, commit=False)

    _set_refresh_phase('Recomputing alerts')
    _recompute_alerts(db, config, commit=False)
    db.commit()

