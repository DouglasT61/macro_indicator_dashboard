from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from app.services.state_space_service import evaluate_state_space

CONFIG = json.loads(Path('backend/config/regime_config.json').read_text(encoding='utf-8'))


def _series(start: datetime, values: list[float]) -> list[dict[str, float | datetime]]:
    return [{'timestamp': start + timedelta(days=index), 'value': value} for index, value in enumerate(values)]


def test_latent_state_layer_uses_configured_monitor_and_descriptive_cluster_context() -> None:
    start = datetime(2026, 2, 1, tzinfo=timezone.utc)
    snapshots = {
        'brent_prompt_spread': {'history': _series(start, [4.8, 5.0, 5.4, 5.9, 6.4, 6.9, 7.3, 7.7])},
        'wti_prompt_spread': {'history': _series(start, [4.2, 4.4, 4.7, 5.0, 5.4, 5.8, 6.0, 6.2])},
        'tanker_freight_proxy': {'history': _series(start, [56, 58, 61, 64, 68, 71, 74, 77])},
        'jpy_usd_basis': {'history': _series(start, [-24, -27, -30, -34, -37, -40, -43, -46])},
        'eur_usd_basis': {'history': _series(start, [-16, -18, -20, -22, -24, -26, -27, -28])},
        'sofr_spread': {'history': _series(start, [14, 16, 18, 21, 25, 29, 33, 37])},
        'move_index': {'history': _series(start, [110, 114, 118, 123, 128, 134, 140, 146])},
        'auction_stress': {'history': _series(start, [44, 47, 50, 54, 58, 62, 66, 70])},
        'treasury_liquidity_proxy': {'history': _series(start, [42, 45, 48, 52, 56, 61, 66, 71])},
        'treasury_basis_proxy': {'history': _series(start, [39, 42, 45, 49, 53, 58, 63, 68])},
        'fima_repo_usage': {'history': _series(start, [8, 9, 10, 12, 14, 17, 20, 24])},
        'fed_swap_line_usage': {'history': _series(start, [1, 1, 2, 3, 4, 5, 6, 8])},
        'consumer_credit_stress': {'history': _series(start, [48, 49, 51, 53, 55, 58, 61, 64])},
        'private_credit_stress': {'history': _series(start, [46, 47, 49, 52, 56, 60, 64, 69])},
        'tips_vs_nominals': {'history': _series(start, [18, 19, 20, 22, 24, 27, 30, 33])},
        'gold_price': {'history': _series(start, [2290, 2305, 2320, 2340, 2360, 2385, 2410, 2440])},
        'oil_price': {'history': _series(start, [84, 85, 87, 89, 92, 95, 98, 101])},
        'marine_insurance_stress': {'history': _series(start, [58, 60, 63, 67, 71, 75, 79, 83])},
        'tanker_disruption_score': {'history': _series(start, [54, 56, 59, 63, 67, 71, 75, 79])},
        'geopolitical_escalation_toggle': {'history': _series(start, [0, 0, 0, 1, 1, 1, 1, 1])},
        'central_bank_intervention_toggle': {'history': _series(start, [0, 0, 0, 0, 0, 0, 1, 1])},
        'lng_proxy': {'history': _series(start, [53, 54, 55, 56, 57, 58, 59, 60])},
        'ten_year_yield': {'history': _series(start, [4.0, 4.02, 4.05, 4.09, 4.14, 4.2, 4.27, 4.35])},
        'thirty_year_yield': {'history': _series(start, [4.2, 4.22, 4.25, 4.29, 4.34, 4.4, 4.47, 4.55])},
        'term_premium_proxy': {'history': _series(start, [42, 44, 46, 49, 52, 56, 60, 64])},
    }

    result = evaluate_state_space(snapshots, CONFIG, 'Convex Inflation / Funding Stress')

    assert result['calibration']['method'] == 'configured latent-state monitor'
    assert result['calibration']['blend_weight'] == 0.0
    assert result['calibration']['base_blend_weight'] == 0.0
    assert result['calibration']['trust_gate']['status'] == 'Disabled'
    assert result['calibration']['transition']['quality'] == 'Configured'
    assert result['calibration']['filter']['quality'] == 'Configured'
    assert result['calibration']['iteration']['iterations_run'] == 0
    assert result['calibration']['cluster_focus']['key'] in {'shipping', 'funding', 'plumbing', 'energy'}
    assert result['calibration']['cluster_focus']['supporting_episodes']
    assert len(result['calibration']['configured_probability_history']) == len(result['probability_history'])
