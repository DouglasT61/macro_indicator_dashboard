from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.state_space_service import evaluate_state_space

CONFIG = json.loads(Path('backend/config/regime_config.json').read_text(encoding='utf-8'))


def _series(start: datetime, values: list[float]) -> list[dict[str, float | datetime]]:
    return [
        {'timestamp': start + timedelta(days=index), 'value': value}
        for index, value in enumerate(values)
    ]


def test_state_space_flags_convex_when_oil_and_funding_stress_align() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    snapshots = {
        'brent_prompt_spread': {'history': _series(start, [4.8, 5.2, 5.9, 6.4, 7.1, 7.8, 8.5, 8.7, 8.9, 9.1])},
        'wti_prompt_spread': {'history': _series(start, [4.4, 4.7, 5.0, 5.3, 5.8, 6.0, 6.1, 6.3, 6.5, 6.7])},
        'tanker_freight_proxy': {'history': _series(start, [55, 58, 60, 64, 67, 70, 72, 74, 77, 80])},
        'jpy_usd_basis': {'history': _series(start, [-24, -27, -30, -34, -37, -40, -42, -45, -47, -49])},
        'eur_usd_basis': {'history': _series(start, [-16, -18, -20, -22, -24, -26, -28, -29, -30, -31])},
        'sofr_spread': {'history': _series(start, [12, 14, 16, 18, 22, 25, 27, 30, 33, 36])},
        'move_index': {'history': _series(start, [105, 109, 114, 118, 123, 128, 132, 136, 141, 145])},
        'auction_stress': {'history': _series(start, [42, 45, 48, 50, 53, 55, 58, 60, 62, 64])},
        'treasury_liquidity_proxy': {'history': _series(start, [38, 39, 41, 43, 44, 45, 46, 47, 48, 49])},
        'treasury_basis_proxy': {'history': _series(start, [35, 37, 40, 42, 45, 47, 49, 52, 54, 56])},
        'fima_repo_usage': {'history': _series(start, [8, 8, 9, 9, 10, 10, 11, 11, 12, 12])},
        'fed_swap_line_usage': {'history': _series(start, [1, 1, 1, 2, 2, 2, 2, 3, 3, 3])},
        'consumer_credit_stress': {'history': _series(start, [48, 49, 50, 51, 52, 54, 55, 56, 57, 58])},
        'private_credit_stress': {'history': _series(start, [46, 47, 48, 49, 50, 51, 52, 53, 54, 55])},
        'tips_vs_nominals': {'history': _series(start, [16, 18, 19, 20, 22, 24, 25, 27, 29, 31])},
        'gold_price': {'history': _series(start, [2290, 2300, 2315, 2330, 2340, 2355, 2370, 2385, 2400, 2415])},
        'oil_price': {'history': _series(start, [84, 86, 88, 90, 92, 95, 97, 99, 100, 101])},
        'marine_insurance_stress': {'history': _series(start, [58, 60, 61, 63, 66, 68, 70, 72, 74, 76])},
        'tanker_disruption_score': {'history': _series(start, [54, 56, 58, 60, 62, 65, 68, 70, 72, 74])},
        'geopolitical_escalation_toggle': {'history': _series(start, [0, 0, 0, 0, 0, 1, 1, 1, 1, 1])},
        'central_bank_intervention_toggle': {'history': _series(start, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])},
        'lng_proxy': {'history': _series(start, [52, 53, 54, 55, 56, 57, 58, 59, 60, 61])},
        'ten_year_yield': {'history': _series(start, [4.0, 4.02, 4.05, 4.08, 4.12, 4.18, 4.24, 4.3, 4.36, 4.41])},
        'thirty_year_yield': {'history': _series(start, [4.2, 4.22, 4.25, 4.28, 4.32, 4.38, 4.44, 4.5, 4.55, 4.6])},
        'term_premium_proxy': {'history': _series(start, [42, 44, 46, 48, 50, 52, 54, 57, 60, 63])},
    }

    result = evaluate_state_space(snapshots, CONFIG, 'Sticky Inflation')

    assert result['states']
    assert result['current_regime'] in {'convex', 'break'}
    assert result['current_probability'] >= 35
    latent = {state['key']: state['value'] for state in result['states']}
    assert latent['oil_shock'] > 55
    assert latent['funding_stress'] > 50
    assert result['diagnostics']['confidence_band'] in {'Watch', 'Dominant', 'Fragile'}
    assert result['calibration']['method'] == 'configured latent-state monitor'
    assert result['calibration']['trust_gate']['status'] == 'Disabled'


def test_state_space_break_probability_rises_when_plumbing_and_intervention_deteriorate() -> None:
    start = datetime(2026, 2, 1, tzinfo=timezone.utc)
    calm = {
        'auction_stress': {'history': _series(start, [40, 41, 42, 43, 44, 45])},
        'treasury_liquidity_proxy': {'history': _series(start, [40, 41, 42, 43, 44, 45])},
        'treasury_basis_proxy': {'history': _series(start, [38, 39, 40, 41, 42, 43])},
        'fima_repo_usage': {'history': _series(start, [9, 9, 9, 10, 10, 10])},
        'fed_swap_line_usage': {'history': _series(start, [1, 1, 1, 1, 1, 1])},
        'central_bank_intervention_toggle': {'history': _series(start, [0, 0, 0, 0, 0, 0])},
        'sofr_spread': {'history': _series(start, [10, 10, 11, 11, 12, 12])},
        'move_index': {'history': _series(start, [96, 98, 99, 100, 102, 103])},
        'jpy_usd_basis': {'history': _series(start, [-18, -18, -19, -19, -20, -20])},
        'eur_usd_basis': {'history': _series(start, [-12, -12, -13, -13, -14, -14])},
        'brent_prompt_spread': {'history': _series(start, [4.1, 4.1, 4.2, 4.2, 4.3, 4.3])},
        'wti_prompt_spread': {'history': _series(start, [3.9, 3.9, 4.0, 4.0, 4.1, 4.1])},
        'oil_price': {'history': _series(start, [82, 82, 83, 83, 84, 84])},
        'consumer_credit_stress': {'history': _series(start, [50, 50, 51, 51, 52, 52])},
        'private_credit_stress': {'history': _series(start, [47, 47, 48, 48, 49, 49])},
        'tips_vs_nominals': {'history': _series(start, [18, 18, 18, 19, 19, 19])},
        'gold_price': {'history': _series(start, [2280, 2280, 2285, 2285, 2290, 2290])},
    }
    stressed = dict(calm)
    stressed.update(
        {
            'auction_stress': {'history': _series(start, [50, 56, 62, 68, 76, 84])},
            'treasury_liquidity_proxy': {'history': _series(start, [44, 50, 56, 62, 70, 78])},
            'treasury_basis_proxy': {'history': _series(start, [42, 46, 52, 58, 66, 74])},
            'fima_repo_usage': {'history': _series(start, [10, 12, 14, 18, 24, 32])},
            'fed_swap_line_usage': {'history': _series(start, [1, 2, 3, 5, 8, 12])},
            'central_bank_intervention_toggle': {'history': _series(start, [0, 0, 0, 1, 1, 1])},
            'sofr_spread': {'history': _series(start, [12, 18, 24, 30, 38, 48])},
            'move_index': {'history': _series(start, [104, 112, 121, 130, 142, 156])},
            'jpy_usd_basis': {'history': _series(start, [-20, -22, -25, -30, -38, -46])},
            'eur_usd_basis': {'history': _series(start, [-14, -15, -17, -20, -24, -28])},
        }
    )

    calm_result = evaluate_state_space(calm, CONFIG, 'Sticky Inflation')
    stressed_result = evaluate_state_space(stressed, CONFIG, 'Sticky Inflation')

    calm_break = calm_result['probability_history'][-1]['break']
    stressed_break = stressed_result['probability_history'][-1]['break']

    assert stressed_break > calm_break
    assert stressed_result['innovation_stress'] >= calm_result['innovation_stress']
    assert stressed_result['diagnostics']['dominant_regime_flips'] >= 0


def test_state_space_uses_configured_layer_without_live_calibration_blend() -> None:
    start = datetime(2026, 3, 1, tzinfo=timezone.utc)
    snapshots = {
        'auction_stress': {'history': _series(start, [65, 70, 74, 78, 82, 86, 88])},
        'treasury_liquidity_proxy': {'history': _series(start, [60, 63, 67, 71, 75, 78, 82])},
        'treasury_basis_proxy': {'history': _series(start, [55, 58, 62, 66, 70, 74, 77])},
        'fima_repo_usage': {'history': _series(start, [15, 18, 21, 24, 28, 31, 34])},
        'fed_swap_line_usage': {'history': _series(start, [2, 3, 5, 7, 9, 12, 15])},
        'central_bank_intervention_toggle': {'history': _series(start, [0, 0, 1, 1, 1, 1, 1])},
        'sofr_spread': {'history': _series(start, [18, 24, 30, 35, 40, 45, 50])},
        'move_index': {'history': _series(start, [120, 128, 136, 144, 151, 156, 160])},
        'jpy_usd_basis': {'history': _series(start, [-25, -29, -33, -37, -41, -45, -49])},
        'eur_usd_basis': {'history': _series(start, [-18, -20, -22, -24, -26, -28, -31])},
        'brent_prompt_spread': {'history': _series(start, [5.2, 5.5, 5.7, 5.9, 6.1, 6.3, 6.5])},
        'wti_prompt_spread': {'history': _series(start, [4.6, 4.8, 5.0, 5.2, 5.4, 5.6, 5.8])},
        'oil_price': {'history': _series(start, [86, 87, 88, 89, 90, 92, 93])},
        'consumer_credit_stress': {'history': _series(start, [56, 58, 60, 62, 64, 66, 68])},
        'private_credit_stress': {'history': _series(start, [52, 55, 58, 62, 66, 70, 74])},
        'tips_vs_nominals': {'history': _series(start, [22, 24, 26, 29, 32, 35, 38])},
        'gold_price': {'history': _series(start, [2380, 2400, 2420, 2450, 2480, 2510, 2540])},
    }

    result = evaluate_state_space(snapshots, CONFIG, 'Sticky Inflation')

    assert result['current_regime'] == 'convex'
    assert result['diagnostics']['confidence_band'] == 'Watch'  # real softmax (temp=18) amplifies score gaps vs old broken linear normalisation
    assert result['calibration']['method'] == 'configured latent-state monitor'
    assert result['calibration']['blend_weight'] == 0.0
    assert result['calibration']['base_blend_weight'] == 0.0
    assert result['calibration']['trust_gate']['status'] == 'Disabled'
    assert result['calibration']['cluster_focus']['key'] in {'shipping', 'energy', 'funding', 'plumbing'}
    assert result['calibration']['cluster_focus']['confidence'] >= 0
    assert result['calibration']['transition']['quality'] == 'Configured'
    assert result['calibration']['filter']['quality'] == 'Configured'
    assert result['calibration']['iteration']['iterations_run'] == 0
    assert result['disagreement_history'][-1]['aligned_with_rule'] is False



def test_state_space_payload_exposes_observation_conditioning_and_forecast_conditioning() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    snapshots = {
        'brent_prompt_spread': {'history': _series(start, [5.1, 5.4, 5.8, 6.2, 6.8, 7.4, 7.9])},
        'wti_prompt_spread': {'history': _series(start, [4.6, 4.8, 5.1, 5.4, 5.8, 6.1, 6.4])},
        'tanker_freight_proxy': {'history': _series(start, [60, 63, 66, 70, 74, 78, 82])},
        'marine_insurance_stress': {'history': _series(start, [62, 66, 70, 74, 78, 82, 86])},
        'tanker_disruption_score': {'history': _series(start, [58, 62, 66, 70, 75, 79, 83])},
        'jpy_usd_basis': {'history': _series(start, [-22, -24, -27, -30, -33, -36, -39])},
        'eur_usd_basis': {'history': _series(start, [-16, -18, -20, -22, -24, -26, -28])},
        'sofr_spread': {'history': _series(start, [14, 16, 18, 21, 24, 27, 30])},
        'move_index': {'history': _series(start, [108, 112, 118, 124, 130, 136, 142])},
        'auction_stress': {'history': _series(start, [42, 45, 48, 51, 54, 58, 62])},
        'treasury_liquidity_proxy': {'history': _series(start, [40, 43, 46, 50, 54, 58, 62])},
        'treasury_basis_proxy': {'history': _series(start, [38, 41, 44, 47, 51, 55, 59])},
        'fima_repo_usage': {'history': _series(start, [8, 9, 10, 11, 12, 14, 16])},
        'fed_swap_line_usage': {'history': _series(start, [1, 1, 2, 2, 3, 4, 5])},
        'private_credit_stress': {'history': _series(start, [44, 46, 48, 51, 54, 58, 62])},
        'consumer_credit_stress': {'history': _series(start, [48, 49, 50, 52, 54, 56, 58])},
        'tips_vs_nominals': {'history': _series(start, [18, 19, 21, 23, 25, 28, 31])},
        'gold_price': {'history': _series(start, [2290, 2305, 2320, 2340, 2360, 2385, 2410])},
        'oil_price': {'history': _series(start, [84, 86, 88, 91, 94, 97, 100])},
    }

    result = evaluate_state_space(snapshots, CONFIG, 'Sticky Inflation')

    assert result['forecast']['conditioning_label']
    assert result['forecast']['conditioning_summary']
    observation_conditioning = result['calibration']['filter']['observation_conditioning']
    assert observation_conditioning['boosted_indicators']
    assert observation_conditioning['average_trust'] > 0
