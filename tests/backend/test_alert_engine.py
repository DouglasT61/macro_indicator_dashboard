from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.alerts.engine import build_alerts

CONFIG = json.loads(Path('backend/config/regime_config.json').read_text(encoding='utf-8'))
NOW = datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc)


def test_systemic_and_combination_alerts_fire_on_joint_stress() -> None:
    latest_values = {
        'brent_prompt_spread': 4.6,
        'jpy_usd_basis': -56,
        'sofr_spread': 54,
        'move_index': 154,
        'auction_stress': 79,
        'fima_repo_usage': 36,
        'fed_swap_line_usage': 18,
        'treasury_basis_proxy': 75,
        'treasury_liquidity_proxy': 78,
        'consumer_credit_stress': 70,
    }
    recent_history = {
        'fima_repo_usage': [18, 22, 26, 31, 36],
        'fed_swap_line_usage': [3, 5, 8, 12, 18],
    }

    alerts = build_alerts(
        latest_values=latest_values,
        recent_history=recent_history,
        config=CONFIG,
        generated_at=NOW,
        systemic_warning_count=5,
    )

    titles = {alert['title'] for alert in alerts}
    severities = {alert['severity'] for alert in alerts}

    assert 'Systemic stress monitor triggered' in titles
    assert 'JPY basis widening while SOFR stress rises' in titles
    assert 'Repo stress, basis unwind, and weak auctions are aligning' in titles
    assert 'critical' in severities


def test_threshold_only_warning_is_generated_for_single_warning_breach() -> None:
    alerts = build_alerts(
        latest_values={'brent_prompt_spread': 5.0},
        recent_history={},
        config=CONFIG,
        generated_at=NOW,
        systemic_warning_count=0,
    )

    assert len(alerts) == 1
    assert alerts[0]['severity'] == 'warning'
    assert 'Brent Prompt Spread' in alerts[0]['title']



def test_state_space_alerts_fire_on_break_risk_and_latent_acceleration() -> None:
    state_space = {
        'diagnostics': {'confidence_band': 'Watch'},
        'states': [
            {'key': 'treasury_stress', 'value': 68.0, 'change_7d': 8.2},
            {'key': 'funding_stress', 'value': 61.0, 'change_7d': 6.4},
        ],
        'forecast': {
            'conditioning_cluster': 'plumbing',
            'conditioning_label': 'Treasury Plumbing Break',
            'horizons': [
                {'days': 1, 'break': 28.0},
                {'days': 5, 'break': 34.0},
                {'days': 10, 'break': 46.0},
            ],
            'scenarios': [
                {'key': 'treasury_plumbing_break', 'label': 'Treasury Plumbing Break', 'break': 54.0},
            ],
        },
        'calibration': {
            'cluster_focus': {'confidence': 0.61},
            'trust_gate': {'status': 'Open', 'summary': 'Trust gate open.'},
        },
    }
    backtest = {
        'dominant_cluster': 'plumbing',
        'dominant_cluster_label': 'Treasury Plumbing Break',
        'cluster_confidence': 0.61,
    }

    from app.alerts.engine import build_state_space_alerts

    alerts = build_state_space_alerts(state_space, backtest, NOW)
    titles = {alert['title'] for alert in alerts}

    assert 'Econometric break-risk transition is building' in titles
    assert 'Latent Treasury stress is accelerating' in titles
    assert 'Stress scenario points to a break-risk path' in titles


def test_state_space_alerts_emit_info_when_validation_guardrail_binds() -> None:
    state_space = {
        'diagnostics': {'confidence_band': 'Fragile'},
        'states': [],
        'forecast': {'conditioning_cluster': 'energy', 'conditioning_label': 'Energy / Inflation Shock', 'horizons': [], 'scenarios': []},
        'calibration': {
            'cluster_focus': {'confidence': 0.2},
            'trust_gate': {'status': 'Reduced', 'summary': 'Validation reduced the live blend.'},
        },
    }
    backtest = {
        'dominant_cluster': 'energy',
        'dominant_cluster_label': 'Energy / Inflation Shock',
        'cluster_confidence': 0.2,
    }

    from app.alerts.engine import build_state_space_alerts

    alerts = build_state_space_alerts(state_space, backtest, NOW)

    assert any(alert['severity'] == 'info' for alert in alerts)
    assert any(alert['title'] == 'Econometric confidence is constrained by validation guardrails' for alert in alerts)


def test_employment_transmission_alerts_fire_on_labor_and_tax_stress() -> None:
    latest_values = {
        'payroll_momentum': 40.0,
        'employment_tax_base_proxy': 1.5,
        'temp_help_stress': -9.5,
        'consumer_credit_stress': 76.0,
        'unemployment_rate': 5.2,
        'auction_stress': 62.0,
        'treasury_liquidity_proxy': 76.0,
        'treasury_basis_proxy': 73.0,
        'fima_repo_usage': 22.0,
    }
    recent_history = {
        'unemployment_rate': [4.4, 4.6, 4.8, 5.0, 5.2],
    }

    alerts = build_alerts(
        latest_values=latest_values,
        recent_history=recent_history,
        config=CONFIG,
        generated_at=NOW,
        systemic_warning_count=0,
    )

    titles = {alert['title'] for alert in alerts}

    assert 'Payroll slowdown is feeding tax-base erosion' in titles
    assert 'Temp-help deterioration is leaking into household credit' in titles
    assert 'Unemployment is rising as break-risk signals accelerate' in titles
