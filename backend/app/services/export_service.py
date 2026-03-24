from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.dashboard_service import get_dashboard_overview


def build_daily_summary_markdown(db: Session) -> str:
    overview = get_dashboard_overview(db)
    regime = overview['regime']
    state_space = overview['state_space']
    diagnostics = state_space['diagnostics']
    forecast = state_space['forecast']
    calibration = state_space['calibration']
    backtest = overview['backtest']
    ordering = overview['ordering_framework']
    stagflation = overview['stagflation_overview']
    migration = overview['migration_overview']

    lines = [
        '# Macro Stress Dashboard Daily Summary',
        '',
        f"Generated: {overview['generated_at'].isoformat()}",
        f"Current rule regime: **{regime['current_regime']}**",
        f"Current latent-state regime: **{state_space['current_regime'].replace('_', ' ').title()}** ({state_space['current_probability']:.1f}% relative confidence)",
        '',
        '## Executive Interpretation',
        f"- Ordering discipline: {ordering['summary']}",
        f"- Lead stage: {ordering['lead_stage']} ({ordering['lead_score']:.1f})",
        f"- Stagflation: {stagflation['summary']}",
        f"- Physical vs financial migration: {migration['summary']}",
        '',
        '## Regime Scores',
        f"- Sticky Inflation: {regime['sticky']['score']:.1f} ({regime['sticky']['change_7d']:+.1f} over 7d)",
        f"- Convex Inflation / Funding Stress: {regime['convex']['score']:.1f} ({regime['convex']['change_7d']:+.1f} over 7d)",
        f"- Break / Repression: {regime['break']['score']:.1f} ({regime['break']['change_7d']:+.1f} over 7d)",
        '',
        '## Latent-State Layer',
        f"- Agreement with rule engine: {'yes' if state_space['rule_agreement'] else 'no'}",
        f"- Observation coverage: {state_space['observation_coverage']:.1f}%",
        f"- Innovation stress: {state_space['innovation_stress']:.2f}",
        f"- Confidence band: {diagnostics['confidence_band']}",
        f"- Tracking quality: {diagnostics['tracking_quality']}",
        f"- Regime flips in sample: {diagnostics['dominant_regime_flips']}",
        '',
        '## Model Notes',
        f"- {calibration['summary']}",
        f"- Configured regime: {calibration['configured_regime'].replace('_', ' ').title()} {calibration['configured_probability']:.1f}% relative confidence",
        f"- Comparison regime: {calibration['calibrated_regime'].replace('_', ' ').title()} {calibration['calibrated_probability']:.1f}% relative confidence",
        f"- Episode subfamily focus: {calibration['cluster_focus']['summary']}",
        f"- Validation trust gate: {calibration['trust_gate']['summary']}",
        f"- Transition fit: {calibration['transition']['summary']}",
        f"- Transition persistence: configured {calibration['transition']['configured_persistence']:.2f} / fitted {calibration['transition']['fitted_persistence']:.2f} / blended {calibration['transition']['blended_persistence']:.2f}",
        f"- Filter fit: {calibration['filter']['summary']}",
        f"- Observation weighting: {calibration['filter']['observation_conditioning']['summary']}",
        f"- Filter noise: floor configured {calibration['filter']['configured_noise_floor']:.1f} / fitted {calibration['filter']['fitted_noise_floor']:.1f} / blended {calibration['filter']['blended_noise_floor']:.1f}",
        f"- Iterative estimation: {calibration['iteration']['summary']}",
        f"- Validation: {calibration['validation']['summary']}",
        '',
        '## Forward Confidence',
        f"- {forecast['summary']}",
        f"- Forecast conditioning: {forecast['conditioning_summary']}",
    ]
    for horizon in forecast['horizons']:
        lines.append(
            f"- {horizon['days']}d: {horizon['dominant_regime'].replace('_', ' ').title()} {horizon['dominant_probability']:.1f}% relative confidence "
            f"(Sticky {horizon['sticky']:.1f} / Convex {horizon['convex']:.1f} / Break {horizon['break']:.1f})"
        )

    lines.extend([
        '',
        '## Historical Analogs',
        f"- {backtest['summary']}",
        f"- Dominant episode family: {backtest['dominant_cluster_label']} ({backtest['cluster_confidence'] * 100:.0f}% confidence)",
        '',
        '## Latent States',
    ])
    for state in state_space['states']:
        lines.append(
            f"- {state['label']}: {state['value']:.1f} ({state['change_7d']:+.1f} over 7d, uncertainty {state['uncertainty']:.1f})"
        )

    lines.extend([
        '',
        '## Top Drivers',
    ])
    for driver in regime['explanation']['summary'][regime['explanation']['current_regime']][:5]:
        lines.append(f'- {driver}')

    lines.extend([
        '',
        '## Daily Narrative',
        overview['narratives']['daily'],
        '',
        '## Stress Alerts',
    ])
    if overview['alerts']:
        for alert in overview['alerts'][:8]:
            lines.append(f"- [{alert['severity'].upper()}] {alert['title']}: {alert['body']}")
    else:
        lines.append('- No active alerts.')

    lines.extend([
        '',
        '## Crisis Monitor',
    ])
    for signal in overview['crisis_monitor']:
        lines.append(f"- {signal['label']}: {signal['value']:.2f} ({signal['status']})")

    return '\n'.join(lines) + '\n'
