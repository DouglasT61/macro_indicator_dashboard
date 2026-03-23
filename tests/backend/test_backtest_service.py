from __future__ import annotations

from app.services.backtest_service import build_backtest_overview


def _snapshot(value: float) -> dict[str, float]:
    return {'normalized_value': value}


def _regime(sticky: float, convex: float, break_score: float) -> dict[str, dict[str, float]]:
    return {
        'sticky': {'score': sticky},
        'convex': {'score': convex},
        'break': {'score': break_score},
    }


def test_backtest_prefers_shipping_episode_for_shipping_heavy_profile() -> None:
    snapshots = {
        'brent_prompt_spread': _snapshot(80.0),
        'jpy_usd_basis': _snapshot(36.0),
        'sofr_spread': _snapshot(18.0),
        'move_index': _snapshot(44.0),
        'auction_stress': _snapshot(30.0),
        'treasury_liquidity_proxy': _snapshot(32.0),
        'fima_repo_usage': _snapshot(22.0),
        'marine_insurance_stress': _snapshot(88.0),
        'private_credit_stress': _snapshot(34.0),
    }
    regime = _regime(74.0, 42.0, 20.0)
    state_space = {'current_probability': 68.0}

    result = build_backtest_overview(snapshots, regime, state_space)

    assert result['episodes'][0]['key'] == 'red_sea_shipping_2024'
    assert result['dominant_cluster'] == 'shipping'
    assert 'Red Sea Shipping Shock' in result['summary']


def test_backtest_prefers_plumbing_break_episode_for_treasury_dysfunction_profile() -> None:
    snapshots = {
        'brent_prompt_spread': _snapshot(16.0),
        'jpy_usd_basis': _snapshot(84.0),
        'sofr_spread': _snapshot(72.0),
        'move_index': _snapshot(96.0),
        'auction_stress': _snapshot(60.0),
        'treasury_liquidity_proxy': _snapshot(96.0),
        'fima_repo_usage': _snapshot(86.0),
        'marine_insurance_stress': _snapshot(20.0),
        'private_credit_stress': _snapshot(56.0),
    }
    regime = _regime(30.0, 52.0, 90.0)
    state_space = {'current_probability': 82.0}

    result = build_backtest_overview(snapshots, regime, state_space)
    top_key = result['episodes'][0]['key']

    assert top_key in {'dash_for_cash_2020', 'uk_gilt_ldi_2022'}
    assert result['dominant_cluster'] == 'plumbing'
    assert result['episodes'][0]['similarity'] >= result['episodes'][1]['similarity']



def test_backtest_prefers_funding_squeeze_episode_for_basis_and_swap_stress_profile() -> None:
    snapshots = {
        'brent_prompt_spread': _snapshot(42.0),
        'wti_prompt_spread': _snapshot(38.0),
        'jpy_usd_basis': _snapshot(74.0),
        'eur_usd_basis': _snapshot(82.0),
        'sofr_spread': _snapshot(54.0),
        'move_index': _snapshot(70.0),
        'auction_stress': _snapshot(56.0),
        'treasury_liquidity_proxy': _snapshot(60.0),
        'treasury_basis_proxy': _snapshot(58.0),
        'fima_repo_usage': _snapshot(34.0),
        'fed_swap_line_usage': _snapshot(66.0),
        'marine_insurance_stress': _snapshot(10.0),
        'private_credit_stress': _snapshot(42.0),
        'central_bank_intervention_toggle': _snapshot(100.0),
    }
    regime = _regime(24.0, 80.0, 52.0)
    state_space = {'current_probability': 76.0}

    result = build_backtest_overview(snapshots, regime, state_space)

    assert result['episodes'][0]['key'] == 'eurozone_dollar_shortage_2011'
    assert result['dominant_cluster'] == 'funding'
    assert result['clusters'][0]['key'] == 'funding'
