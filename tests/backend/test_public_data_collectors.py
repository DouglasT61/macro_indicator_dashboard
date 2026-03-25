from __future__ import annotations

from datetime import date, datetime, timezone

from app.collectors.public_data import (
    YahooBar,
    _active_contracts_for_day,
    _build_basis_proxy_series,
    _build_front_contract_history,
    _build_period_change_history,
    _build_payroll_tax_base_history,
    _build_pointwise_series,
    _build_synthetic_ctd_basis_history,
    _build_treasury_depth_history,
    _compute_auction_stress_histories,
    _compute_auction_stress_history,
    _densify_daily,
    _generate_contract_specs,
)


def test_densify_daily_carries_last_observation_forward() -> None:
    history = _densify_daily(
        [(date(2026, 3, 10), 1.0), (date(2026, 3, 12), 3.0)],
        start=date(2026, 3, 10),
        end=date(2026, 3, 13),
    )

    assert [point[1] for point in history] == [1.0, 1.0, 3.0, 3.0]


def test_build_pointwise_series_uses_latest_available_inputs() -> None:
    history = _build_pointwise_series(
        start=date(2026, 3, 10),
        end=date(2026, 3, 12),
        inputs={
            'SOFR': [(date(2026, 3, 10), 4.50)],
            'DFF': [(date(2026, 3, 10), 4.20), (date(2026, 3, 12), 4.25)],
        },
        formula=lambda values: round((values['SOFR'] - values['DFF']) * 100.0, 2),
    )

    assert [point[1] for point in history] == [30.0, 30.0, 25.0]


def test_compute_auction_stress_history_generates_daily_step_series() -> None:
    rows = [
        {
            'auction_date': '2026-03-10',
            'security_type': 'Note',
            'security_term': '10-Year',
            'bid_to_cover_ratio': '2.70',
            'high_yield': '4.55',
            'offering_amt': '39000000000',
            'indirect_bidder_accepted': '25000000000',
        },
        {
            'auction_date': '2026-03-12',
            'security_type': 'Bond',
            'security_term': '30-Year',
            'bid_to_cover_ratio': '2.25',
            'high_yield': '4.88',
            'offering_amt': '22000000000',
            'indirect_bidder_accepted': '12000000000',
        },
    ]

    history = _compute_auction_stress_history(rows, start=date(2026, 3, 10), end=date(2026, 3, 13))

    assert len(history) == 4
    assert history[0][1] < history[-1][1]
    assert history[2][1] == history[3][1]


def test_auction_stress_history_uses_trailing_distribution_without_future_lookahead() -> None:
    rows = [
        {
            'auction_date': '2026-01-10',
            'security_type': 'Note',
            'security_term': '10-Year',
            'bid_to_cover_ratio': '2.70',
            'high_yield': '4.20',
            'offering_amt': '39000000000',
            'indirect_bidder_accepted': '25000000000',
            'primary_dealer_accepted': '9000000000',
        },
        {
            'auction_date': '2026-02-10',
            'security_type': 'Note',
            'security_term': '10-Year',
            'bid_to_cover_ratio': '2.60',
            'high_yield': '4.25',
            'offering_amt': '40000000000',
            'indirect_bidder_accepted': '24000000000',
            'primary_dealer_accepted': '10000000000',
        },
        {
            'auction_date': '2026-03-10',
            'security_type': 'Bond',
            'security_term': '30-Year',
            'bid_to_cover_ratio': '1.80',
            'high_yield': '5.10',
            'offering_amt': '22000000000',
            'indirect_bidder_accepted': '8000000000',
            'primary_dealer_accepted': '11000000000',
        },
    ]

    histories = _compute_auction_stress_histories(rows, start=date(2026, 1, 10), end=date(2026, 3, 12))
    clearing_history = histories['auction_clearing_stress']

    jan10 = next(value for timestamp, value in clearing_history if timestamp.date() == date(2026, 1, 10))
    feb10 = next(value for timestamp, value in clearing_history if timestamp.date() == date(2026, 2, 10))
    mar10 = next(value for timestamp, value in clearing_history if timestamp.date() == date(2026, 3, 10))

    assert jan10 == 50.0
    assert feb10 > jan10
    assert mar10 > feb10


def test_basis_proxy_series_becomes_more_negative_with_wider_rate_gap_and_fx_vol() -> None:
    fx = [
        (date(2026, 3, 10), 1.10),
        (date(2026, 3, 11), 1.11),
        (date(2026, 3, 12), 1.08),
        (date(2026, 3, 13), 1.13),
        (date(2026, 3, 14), 1.09),
    ]
    usd_rate = [(date(2026, 3, 10), 4.4), (date(2026, 3, 14), 4.5)]
    local_rate = [(date(2026, 3, 10), 1.5), (date(2026, 3, 14), 1.0)]

    history = _build_basis_proxy_series(
        start=date(2026, 3, 10),
        end=date(2026, 3, 14),
        fx_observations=fx,
        usd_rate_observations=usd_rate,
        local_rate_observations=local_rate,
        rate_multiplier=6.5,
        vol_multiplier=2.5,
        floor_value=5.0,
        ceiling_value=80.0,
        vol_window=3,
    )

    assert history[0][1] < 0
    assert history[-1][1] < history[0][1]


def test_active_contract_selection_rolls_to_next_month() -> None:
    specs = _generate_contract_specs('CL', '.NYM', start=date(2026, 1, 1), end=date(2026, 3, 31), monthly=True, roll_lead_days=35)
    selected = _active_contracts_for_day(specs, date(2026, 3, 5))
    assert selected[0].symbol.endswith('.NYM')
    assert selected[0].delivery_month <= selected[1].delivery_month


def test_front_contract_history_and_treasury_metrics_build() -> None:
    specs = _generate_contract_specs('ZN', '.CBT', start=date(2026, 3, 1), end=date(2026, 3, 5), monthly=False, roll_lead_days=20)
    first, second = _active_contracts_for_day(specs, date(2026, 3, 1))
    bar_map = {
        first.symbol: {
            date(2026, 3, 1): YahooBar(timestamp=None, close=111.0, high=111.2, low=110.8, volume=100000.0),
            date(2026, 3, 2): YahooBar(timestamp=None, close=110.8, high=111.0, low=110.4, volume=120000.0),
            date(2026, 3, 3): YahooBar(timestamp=None, close=110.6, high=111.1, low=110.3, volume=90000.0),
            date(2026, 3, 4): YahooBar(timestamp=None, close=110.9, high=111.3, low=110.5, volume=95000.0),
            date(2026, 3, 5): YahooBar(timestamp=None, close=111.1, high=111.4, low=110.7, volume=98000.0),
        },
        second.symbol: {
            date(2026, 3, 1): YahooBar(timestamp=None, close=110.7, high=110.9, low=110.5, volume=80000.0),
            date(2026, 3, 2): YahooBar(timestamp=None, close=110.6, high=110.8, low=110.4, volume=81000.0),
            date(2026, 3, 3): YahooBar(timestamp=None, close=110.4, high=110.7, low=110.2, volume=82000.0),
            date(2026, 3, 4): YahooBar(timestamp=None, close=110.6, high=110.9, low=110.3, volume=83000.0),
            date(2026, 3, 5): YahooBar(timestamp=None, close=110.8, high=111.0, low=110.5, volume=84000.0),
        },
    }
    front_history = _build_front_contract_history(specs, bar_map, start=date(2026, 3, 1), end=date(2026, 3, 5))
    depth = _build_treasury_depth_history(front_history, window=3)
    seven_year = [(bar.timestamp, 4.05 + index * 0.02) for index, bar in enumerate(front_history)]
    ten_year = [(bar.timestamp, 4.20 + index * 0.02) for index, bar in enumerate(front_history)]
    basis = _build_synthetic_ctd_basis_history(front_history, seven_year, ten_year, window=3)

    assert len(front_history) == 5
    assert len(depth) == 5
    assert len(basis) == 5
    assert all(value >= 0 for _, value in depth)
    assert all(value >= 0 for _, value in basis)


def test_synthetic_ctd_basis_history_rises_with_larger_futures_cash_yield_gap() -> None:
    front_history = [
        YahooBar(timestamp=datetime(2026, 3, day, tzinfo=timezone.utc), close=110.9 + offset, high=111.0, low=110.5, volume=90000.0)
        for offset, day in enumerate(range(1, 6))
    ]
    seven_year = [
        (datetime(2026, 3, day, tzinfo=timezone.utc), 4.00 + 0.01 * index)
        for index, day in enumerate(range(1, 6))
    ]
    ten_year = [
        (datetime(2026, 3, day, tzinfo=timezone.utc), 4.20 + 0.01 * index)
        for index, day in enumerate(range(1, 6))
    ]

    calm = _build_synthetic_ctd_basis_history(front_history, seven_year, ten_year, window=3)
    stressed_front_history = [
        YahooBar(timestamp=bar.timestamp, close=bar.close + 2.5, high=bar.high + 2.5, low=bar.low + 2.5, volume=bar.volume)
        for bar in front_history
    ]
    stressed = _build_synthetic_ctd_basis_history(stressed_front_history, seven_year, ten_year, window=3)

    assert len(calm) == len(stressed) == 5
    assert stressed[-1][1] > calm[-1][1]



def test_period_change_history_supports_average_change_and_yoy_percent() -> None:
    observations = [
        (date(2025 + ((month - 1) // 12), ((month - 1) % 12) + 1, 1), 100.0 + month * 10.0)
        for month in range(1, 16)
    ]

    average_change = _build_period_change_history(observations, start=date(2026, 1, 1), end=date(2026, 3, 31), periods_back=3, pct=False, divisor=3.0)
    yoy_change = _build_period_change_history(observations, start=date(2026, 1, 1), end=date(2026, 3, 31), periods_back=12, pct=True)

    assert round(average_change[0][1], 2) == 10.0
    assert round(yoy_change[0][1], 2) == 109.09


def test_payroll_tax_base_history_combines_payrolls_wages_and_hours() -> None:
    payrolls = [(date(2025 + ((month - 1) // 12), ((month - 1) % 12) + 1, 1), 1000.0 + month * 10.0) for month in range(1, 16)]
    wages = [(date(2025 + ((month - 1) // 12), ((month - 1) % 12) + 1, 1), 20.0 + month * 0.1) for month in range(1, 16)]
    hours = [(date(2025 + ((month - 1) // 12), ((month - 1) % 12) + 1, 1), 34.0 + month * 0.05) for month in range(1, 16)]

    history = _build_payroll_tax_base_history(payrolls, wages, hours, start=date(2026, 1, 1), end=date(2026, 3, 31))

    assert len(history) >= 1
    assert history[0][1] > 0
