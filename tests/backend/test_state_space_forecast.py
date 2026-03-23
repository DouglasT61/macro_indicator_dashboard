from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from app.services.state_space_service import evaluate_state_space

CONFIG = json.loads(Path('backend/config/regime_config.json').read_text(encoding='utf-8'))


def _series(start: datetime, values: list[float]) -> list[dict[str, float | datetime]]:
    return [
        {'timestamp': start + timedelta(days=index), 'value': value}
        for index, value in enumerate(values)
    ]


def test_forecast_layer_builds_horizons_and_scenarios() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    snapshots = {
        'brent_prompt_spread': {'history': _series(start, [5.1, 5.4, 5.9, 6.3, 6.8, 7.2, 7.6, 8.0, 8.4, 8.8])},
        'wti_prompt_spread': {'history': _series(start, [4.6, 4.9, 5.2, 5.5, 5.9, 6.1, 6.3, 6.5, 6.7, 6.9])},
        'tanker_freight_proxy': {'history': _series(start, [58, 60, 63, 66, 69, 72, 74, 77, 80, 83])},
        'jpy_usd_basis': {'history': _series(start, [-24, -27, -29, -32, -35, -38, -41, -44, -46, -48])},
        'eur_usd_basis': {'history': _series(start, [-16, -18, -19, -21, -23, -25, -27, -28, -29, -30])},
        'sofr_spread': {'history': _series(start, [14, 16, 18, 20, 24, 28, 31, 34, 37, 40])},
        'move_index': {'history': _series(start, [110, 114, 118, 123, 127, 132, 136, 140, 145, 149])},
        'auction_stress': {'history': _series(start, [45, 47, 50, 53, 56, 59, 62, 65, 68, 71])},
        'treasury_liquidity_proxy': {'history': _series(start, [42, 44, 47, 50, 53, 57, 60, 64, 68, 72])},
        'treasury_basis_proxy': {'history': _series(start, [39, 41, 44, 47, 50, 53, 57, 60, 64, 68])},
        'fima_repo_usage': {'history': _series(start, [8, 9, 10, 11, 12, 13, 15, 17, 19, 22])},
        'fed_swap_line_usage': {'history': _series(start, [1, 1, 2, 2, 3, 4, 5, 6, 7, 8])},
        'consumer_credit_stress': {'history': _series(start, [48, 49, 50, 52, 54, 56, 58, 60, 62, 64])},
        'private_credit_stress': {'history': _series(start, [46, 47, 49, 51, 54, 57, 60, 63, 66, 69])},
        'tips_vs_nominals': {'history': _series(start, [17, 18, 19, 21, 23, 25, 27, 29, 31, 33])},
        'gold_price': {'history': _series(start, [2290, 2300, 2310, 2325, 2340, 2355, 2370, 2390, 2410, 2430])},
        'oil_price': {'history': _series(start, [84, 85, 87, 89, 91, 93, 95, 97, 99, 101])},
        'marine_insurance_stress': {'history': _series(start, [58, 60, 63, 66, 69, 72, 75, 78, 80, 83])},
        'tanker_disruption_score': {'history': _series(start, [54, 56, 59, 62, 65, 68, 71, 74, 77, 80])},
        'geopolitical_escalation_toggle': {'history': _series(start, [0, 0, 0, 0, 1, 1, 1, 1, 1, 1])},
        'central_bank_intervention_toggle': {'history': _series(start, [0, 0, 0, 0, 0, 0, 0, 1, 1, 1])},
        'lng_proxy': {'history': _series(start, [53, 54, 55, 56, 57, 58, 59, 60, 61, 62])},
        'ten_year_yield': {'history': _series(start, [4.0, 4.02, 4.05, 4.08, 4.12, 4.17, 4.22, 4.28, 4.34, 4.4])},
        'thirty_year_yield': {'history': _series(start, [4.2, 4.22, 4.24, 4.27, 4.31, 4.36, 4.42, 4.48, 4.54, 4.6])},
        'term_premium_proxy': {'history': _series(start, [42, 44, 46, 48, 50, 53, 56, 59, 62, 65])},
    }

    result = evaluate_state_space(snapshots, CONFIG, 'Convex Inflation / Funding Stress')

    assert result['forecast']['summary']
    assert result['forecast']['conditioning_cluster'] in {'shipping', 'funding', 'plumbing', 'energy'}
    assert result['forecast']['conditioning_label']
    assert result['forecast']['conditioning_confidence'] >= 0
    assert result['forecast']['conditioning_summary']
    assert [row['days'] for row in result['forecast']['horizons']] == [1, 5, 10]
    assert len(result['forecast']['baseline_path']) == 10
    assert len(result['forecast']['scenarios']) == 3
    assert result['forecast']['scenarios'][0]['break'] >= result['forecast']['scenarios'][-1]['break']
    assert all('state_impulse_summary' in scenario for scenario in result['forecast']['scenarios'])
