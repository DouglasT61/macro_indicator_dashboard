from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone

from app.seed.catalog import SERIES_DEFINITIONS


SERIES_KEYS = {definition.key for definition in SERIES_DEFINITIONS}


def _stress_wave(index: int, total_days: int) -> float:
    progress = index / max(total_days - 1, 1)
    return max(0.0, (progress - 0.55) / 0.45)


def _value_for_key(key: str, index: int, total_days: int) -> float:
    wave = _stress_wave(index, total_days)
    pulse = math.sin(index / 8.5)
    pulse_fast = math.sin(index / 4.2)
    drift = index / max(total_days, 1)

    formulas: dict[str, float] = {
        "brent_prompt_spread": 1.2 + 0.35 * pulse + 3.8 * wave**1.4,
        "wti_prompt_spread": 0.9 + 0.25 * pulse + 2.7 * wave**1.35,
        "murban_wti_spread": 1.4 + 0.5 * pulse_fast + 6.8 * wave**1.32,
        "oman_wti_spread": 0.9 + 0.45 * pulse + 5.9 * wave**1.28,
        "gulf_crude_dislocation": 24 + 4.5 * pulse_fast + 42 * wave**1.3,
        "tanker_freight_proxy": 42 + 6 * pulse + 42 * wave**1.35,
        "hormuz_tanker_transit_stress": 34 + 4 * pulse_fast + 47 * wave**1.38,
        "gfw_red_sea_port_stress": 30 + 3.8 * pulse_fast + 39 * wave**1.3,
        "lng_proxy": 44 + 5 * pulse_fast + 35 * wave**1.25,
        "iea_oil_cover_days": 148 - 2.2 * pulse - 28 * wave**1.12,
        "iea_public_stock_share": 46 + 0.8 * pulse - 10 * wave**1.08,
        "oil_buffer_depletion_stress": 30 + 3.8 * pulse_fast + 42 * wave**1.3,
        "eur_usd_basis": -12 - 3.5 * pulse - 22 * wave**1.25,
        "jpy_usd_basis": -18 - 5 * pulse_fast - 35 * wave**1.35,
        "synthetic_usd_funding_pressure": 28 + 4.5 * pulse_fast + 38 * wave**1.28,
        "vix_index": 16 + 2.8 * pulse_fast + 16 * wave**1.32,
        "oil_in_yen_stress": 34 + 4.0 * pulse_fast + 40 * wave**1.3,
        "oil_in_eur_stress": 30 + 3.2 * pulse + 33 * wave**1.26,
        "oil_in_cny_stress": 26 + 2.5 * pulse_fast + 28 * wave**1.22,
        "iea_importer_oil_cover_stress": 31 + 3.6 * pulse + 36 * wave**1.27,
        "world_bank_importer_vulnerability": 36 + 0.8 * pulse + 6 * drift**1.08,
        "external_importer_stress": 31 + 3.4 * pulse_fast + 36 * wave**1.28,
        "expected_inflation_5y5y": 2.3 + 0.04 * pulse + 0.72 * wave**1.2,
        "inflation_expectations_level": 2.25 + 0.03 * pulse + 0.58 * wave**1.18,
        "inflation_expectations_slope": 12 + 5.5 * pulse_fast + 55 * wave**1.22,
        "inflation_expectations_curvature": 4 + 4.0 * pulse + 26 * wave**1.26,
        "survey_market_expectations_gap": 10 + 3.5 * pulse_fast + 38 * wave**1.3,
        "expectations_entrenchment_score": 34 + 3.5 * pulse + 44 * wave**1.28,
        "eur_usd_spot": 1.09 + 0.012 * pulse - 0.035 * wave**1.15,
        "usd_jpy_spot": 147 + 1.6 * pulse_fast + 9.5 * wave**1.12,
        "usd_cny_spot": 7.05 + 0.03 * pulse + 0.48 * wave**1.1,
        "sofr_rate": 4.65 + 0.04 * pulse - 0.95 * drift,
        "ecb_deposit_rate": 4.0 + 0.02 * pulse - 1.75 * drift,
        "japan_short_rate": 0.08 + 0.01 * pulse + 0.72 * drift,
        "sofr_spread": 8 + 2.2 * pulse + 44 * wave**1.45,
        "move_index": 96 + 8 * pulse + 58 * wave**1.3,
        "treasury_liquidity_proxy": 38 + 7 * pulse_fast + 42 * wave**1.3,
        "treasury_basis_proxy": 34 + 6 * pulse + 41 * wave**1.32,
        "auction_clearing_stress": 34 + 6 * pulse_fast + 46 * wave**1.33,
        "auction_belly_clearing_stress": 32 + 5.5 * pulse_fast + 43 * wave**1.31,
        "auction_foreign_sponsorship_stress": 29 + 5 * pulse + 42 * wave**1.28,
        "auction_issuance_mix_stress": 24 + 4 * pulse_fast + 36 * wave**1.24,
        "auction_coupon_cluster_stress": 22 + 3.8 * pulse_fast + 34 * wave**1.26,
        "auction_stress": 31 + 5 * pulse_fast + 44 * wave**1.31,
        "fima_repo_usage": 2.5 + 1.4 * max(0, pulse) + 31 * max(0.0, wave - 0.15) ** 1.65,
        "fed_swap_line_usage": 0.4 + 0.8 * max(0, pulse_fast) + 18 * max(0.0, wave - 0.35) ** 1.8,
        "ten_year_yield": 3.82 + 0.08 * pulse + 0.82 * wave**1.25,
        "thirty_year_yield": 4.08 + 0.09 * pulse_fast + 0.9 * wave**1.25,
        "term_premium_proxy": 28 + 6 * pulse + 52 * wave**1.3,
        "bea_net_iip_burden": 22.8 + 0.9 * drift + 4.4 * wave**1.18,
        "bea_foreign_financing_support": 520 + 35 * pulse - 330 * wave**1.22,
        "foreign_duration_sponsorship_stress": 29 + 4.4 * pulse_fast + 44 * wave**1.31,
        "consumer_credit_stress": 41 + 2 * pulse_fast + 33 * drift**1.4,
        "payroll_momentum": 185 + 24 * pulse - 235 * wave**1.35,
        "unemployment_rate": 3.7 + 0.08 * pulse_fast + 1.65 * wave**1.45,
        "wage_stickiness": 3.2 + 0.12 * pulse + 1.45 * wave**1.18,
        "hours_worked_momentum": 0.18 * pulse - 0.52 * wave**1.3,
        "temp_help_stress": 1.5 * pulse - 9.5 * wave**1.4,
        "employment_tax_base_proxy": 4.8 + 0.2 * pulse - 6.0 * wave**1.32,
        "household_real_income_squeeze": 28 + 2.0 * pulse_fast + 40 * wave**1.26,
        "federal_receipts_quality": 56 - 2.4 * pulse - 16 * drift**1.1,
        "deficit_trend": 44 + 2.5 * pulse + 31 * drift**1.2,
        "tax_receipts_market_stress": 26 + 3.0 * pulse_fast + 38 * wave**1.28,
        "spx_equal_weight": 520 + 11 * pulse - 55 * wave**1.2,
        "tips_vs_nominals": 12 + 2.2 * pulse + 29 * wave**1.25,
        "gold_price": 2190 + 14 * pulse_fast + 360 * wave**1.1,
        "oil_price": 80 + 2.5 * pulse + 28 * wave**1.25,
        "credit_spreads": 118 + 6 * pulse + 73 * wave**1.22,
        "usd_index_proxy": 101.5 + 0.5 * pulse_fast + 7.5 * wave**1.2,
    }
    value = formulas.get(key)
    if value is None:
        import warnings
        warnings.warn(f"demo_collector: no formula for key '{key}', returning 50.0", stacklevel=2)
        return 50.0
    return round(value, 3)


def generate_demo_history(days: int = 180, end_date: date | None = None) -> dict[str, list[tuple[datetime, float]]]:
    end = end_date or date.today()
    start = end - timedelta(days=days - 1)
    history: dict[str, list[tuple[datetime, float]]] = {key: [] for key in SERIES_KEYS}

    for index in range(days):
        current = start + timedelta(days=index)
        timestamp = datetime.combine(current, time(hour=12), tzinfo=timezone.utc)
        for key in SERIES_KEYS:
            history[key].append((timestamp, _value_for_key(key, index, days)))

    return history


def value_for_offset(key: str, start_date: date, current_date: date) -> tuple[datetime, float]:
    total_days = (current_date - start_date).days + 1
    index = total_days - 1
    timestamp = datetime.combine(current_date, time(hour=12), tzinfo=timezone.utc)
    return timestamp, _value_for_key(key, index, max(total_days, 180))
