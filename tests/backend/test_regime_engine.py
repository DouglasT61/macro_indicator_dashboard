from __future__ import annotations

import copy
import json
from pathlib import Path

from app.regime_engine.engine import evaluate_regimes

CONFIG = json.loads(Path('backend/config/regime_config.json').read_text(encoding='utf-8'))


def test_convex_regime_outscores_sticky_when_funding_and_oil_stress_align() -> None:
    values = {
        'brent_prompt_spread': 8.8,
        'tanker_freight_proxy': 82,
        'jpy_usd_basis': -57,
        'eur_usd_basis': -34,
        'sofr_spread': 42,
        'move_index': 151,
        'auction_stress': 77,
        'treasury_basis_proxy': 73,
        'fima_repo_usage': 14,
        'fed_swap_line_usage': 4,
        'consumer_credit_stress': 61,
        'oil_price': 102,
        'tips_vs_nominals': 38,
    }
    manual_inputs = {
        'marine_insurance_stress': 74,
        'private_credit_stress': 64,
        'central_bank_intervention_toggle': 0,
        'geopolitical_escalation_toggle': 1,
    }

    result = evaluate_regimes(values, manual_inputs, CONFIG)

    assert result['scores']['convex'] > result['scores']['sticky']
    assert result['scores']['convex'] > result['scores']['break'] - 12
    assert result['current_regime'] in {'convex', 'break'}
    assert result['propagation']['node_states']['repo_basis_stress']['propagated_score'] >= result['propagation']['node_states']['repo_basis_stress']['base_score']


def test_break_regime_wins_when_plumbing_backstops_engage() -> None:
    values = {
        'auction_stress': 86,
        'sofr_spread': 58,
        'fima_repo_usage': 38,
        'fed_swap_line_usage': 19,
        'treasury_liquidity_proxy': 81,
        'treasury_basis_proxy': 79,
        'move_index': 162,
        'consumer_credit_stress': 75,
    }
    manual_inputs = {
        'private_credit_stress': 81,
        'central_bank_intervention_toggle': 1,
    }

    result = evaluate_regimes(values, manual_inputs, CONFIG)

    assert result['current_regime'] == 'break'
    assert result['scores']['break'] > 75
    assert result['drivers']['break'][0]['contribution'] >= result['drivers']['break'][1]['contribution']


def test_recursive_propagation_adds_second_order_break_pressure() -> None:
    values = {
        'brent_prompt_spread': 9.5,
        'wti_prompt_spread': 8.3,
        'tanker_freight_proxy': 84,
        'jpy_usd_basis': -46,
        'eur_usd_basis': -31,
        'sofr_spread': 38,
        'auction_stress': 61,
        'treasury_basis_proxy': 52,
        'treasury_liquidity_proxy': 49,
        'move_index': 132,
        'fima_repo_usage': 17,
        'fed_swap_line_usage': 3,
        'consumer_credit_stress': 63,
        'tips_vs_nominals': 33,
        'oil_price': 97,
    }
    manual_inputs = {
        'marine_insurance_stress': 77,
        'tanker_disruption_score': 78,
        'private_credit_stress': 68,
        'geopolitical_escalation_toggle': 1,
        'central_bank_intervention_toggle': 0,
    }

    no_propagation = copy.deepcopy(CONFIG)
    no_propagation.pop('propagation', None)

    static_result = evaluate_regimes(values, manual_inputs, no_propagation)
    propagated_result = evaluate_regimes(values, manual_inputs, CONFIG)

    repo_node = propagated_result['propagation']['node_states']['repo_basis_stress']
    break_effect = propagated_result['propagation']['regime_effects']['break']['total']

    assert repo_node['propagated_score'] > repo_node['base_score']
    assert break_effect > 0
    assert propagated_result['scores']['break'] > static_result['scores']['break']
