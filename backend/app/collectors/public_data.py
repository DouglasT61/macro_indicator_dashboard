from __future__ import annotations

import csv
import io
import math
import re
from urllib.parse import quote
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Iterable

import httpx


FRED_BASE_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
TREASURY_AUCTIONS_URL = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query'
TREASURY_DTS_URL = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash'
TREASURY_DEBT_TO_PENNY_URL = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny'
TREASURY_YIELD_CSV_URL = 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all'
NYFED_SOFR_URL = 'https://markets.newyorkfed.org/api/rates/secured/sofr/search.json'
NYFED_EFFR_URL = 'https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json'
FED_H41_URL = 'https://www.federalreserve.gov/releases/h41/{stamp}/h41.htm'
YAHOO_CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
TRADINGVIEW_SYMBOL_URL = 'https://www.tradingview.com/symbols/{symbol}/'
FYICENTER_MOVE_URL = 'https://finance.fyicenter.com/1000140_NYSE_%5EMOVE-ICE_BofAML_MOVE_Index.html'
GME_DATA_URL = 'https://www.gulfmerc.com/gme-product-services/gme-data'
TREASURY_HISTORY_DAYS = 730

MONTH_CODES = {
    1: 'F',
    2: 'G',
    3: 'H',
    4: 'J',
    5: 'K',
    6: 'M',
    7: 'N',
    8: 'Q',
    9: 'U',
    10: 'V',
    11: 'X',
    12: 'Z',
}

FRED_DIRECT_SERIES: dict[str, tuple[str, Callable[[float], float]]] = {
    'tips_vs_nominals': ('T10YIE', lambda value: value * 100.0),
    'oil_price': ('DCOILBRENTEU', lambda value: value),
    'credit_spreads': ('BAMLH0A0HYM2', lambda value: value * 100.0),
    'usd_index_proxy': ('DTWEXBGS', lambda value: value),
    'consumer_credit_stress': ('DRCCLACBS', lambda value: value * 20.0),
    'japan_short_rate': ('IRSTCI01JPM156N', lambda value: value),
    'unemployment_rate': ('UNRATE', lambda value: value),
    'tanker_freight_proxy': ('TSIFRGHT', lambda value: max(10.0, min(100.0, (value - 80.0) * 1.3))),
    'lng_proxy': ('PNGASJPUSDM', lambda value: max(10.0, min(100.0, value * 6.0))),
}


@dataclass(slots=True)
class CollectedSeries:
    key: str
    source: str
    history: list[tuple[datetime, float]]


@dataclass(slots=True)
class CollectionResult:
    series: dict[str, CollectedSeries]
    provider_status: dict[str, str]


@dataclass(slots=True)
class YahooBar:
    timestamp: datetime
    close: float
    high: float
    low: float
    volume: float


@dataclass(slots=True)
class ContractSpec:
    symbol: str
    delivery_month: date
    roll_date: date


class PublicDataCollector:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.fred_timeout_seconds = min(timeout_seconds, 6.0)

    def collect(
        self,
        days: int = 180,
        end_date: date | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> CollectionResult:
        end = end_date or date.today()
        start = end - timedelta(days=days - 1)
        treasury_start = end - timedelta(days=max(days, TREASURY_HISTORY_DAYS) - 1)
        collected: dict[str, CollectedSeries] = {}
        statuses: dict[str, str] = {}

        with httpx.Client(timeout=self.timeout_seconds, headers={'User-Agent': 'Mozilla/5.0 macro-stress-dashboard/0.1'}) as client:
            try:
                if status_callback:
                    status_callback('market_data: fred')
                fred_series, fred_status = self._collect_fred_series(client, start, end)
            except Exception as exc:
                fred_series, fred_status = {}, f'FRED collector failed: {exc.__class__.__name__}.'
            collected.update(fred_series)
            statuses['fred'] = fred_status

            try:
                if status_callback:
                    status_callback('market_data: nyfed')
                nyfed_series, nyfed_status = self._collect_nyfed_series(client, start, end)
            except Exception as exc:
                nyfed_series, nyfed_status = {}, f'NY Fed collector failed: {exc.__class__.__name__}.'
            collected.update(nyfed_series)
            statuses['nyfed'] = nyfed_status

            try:
                if status_callback:
                    status_callback('market_data: ecb')
                ecb_series, ecb_status = self._collect_ecb_series(client, start, end)
            except Exception as exc:
                ecb_series, ecb_status = {}, f'ECB collector failed: {exc.__class__.__name__}.'
            collected.update(ecb_series)
            statuses['ecb'] = ecb_status

            try:
                if status_callback:
                    status_callback('market_data: fed_h41')
                fed_h41_series, fed_h41_status = self._collect_fed_h41_series(client, start, end)
            except Exception as exc:
                fed_h41_series, fed_h41_status = {}, f'Fed H.4.1 collector failed: {exc.__class__.__name__}.'
            collected.update(fed_h41_series)
            statuses['fed_h41'] = fed_h41_status

            try:
                if status_callback:
                    status_callback('market_data: treasury')
                treasury_series, treasury_status = self._collect_treasury_series(client, treasury_start, end)
            except Exception as exc:
                treasury_series, treasury_status = {}, f'Treasury collector failed: {exc.__class__.__name__}.'
            collected.update(treasury_series)
            statuses['treasury'] = treasury_status

            try:
                if status_callback:
                    status_callback('market_data: yahoo_market')
                yahoo_series, yahoo_status = self._collect_yahoo_futures_series(client, start, end)
            except Exception as exc:
                yahoo_series, yahoo_status = {}, f'Yahoo market collector failed: {exc.__class__.__name__}.'
            collected.update(yahoo_series)
            statuses['yahoo_market'] = yahoo_status

        try:
            if status_callback:
                status_callback('market_data: support')
            support_series, support_status = self._collect_support_series(start, end, collected)
        except Exception as exc:
            support_series, support_status = {}, f'Support collector failed: {exc.__class__.__name__}.'
        collected.update(support_series)
        statuses['support'] = support_status

        return CollectionResult(series=collected, provider_status=statuses)

    def _collect_fred_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> tuple[dict[str, CollectedSeries], str]:
        raw_cache: dict[str, list[tuple[date, float]]] = {}
        collected: dict[str, CollectedSeries] = {}
        failures: list[str] = []

        def _record_failure(label: str, exc: Exception) -> None:
            failures.append(f'{label}({exc.__class__.__name__})')

        for key, (series_id, transform) in FRED_DIRECT_SERIES.items():
            try:
                observations = self._fetch_fred_csv(client, series_id, start, end, transform=transform)
                history = _densify_daily(observations, start, end)
                if history:
                    collected[key] = CollectedSeries(key=key, source=f'fred/{series_id}', history=history)
                    raw_cache[series_id] = observations
            except Exception as exc:
                _record_failure(series_id, exc)

        try:
            sofr = raw_cache.get('SOFR') or self._fetch_fred_csv(client, 'SOFR', start, end)
            dff = raw_cache.get('DFF') or self._fetch_fred_csv(client, 'DFF', start, end)
            sofr_history = _build_pointwise_series(
                start,
                end,
                {'SOFR': sofr, 'DFF': dff},
                lambda values: round((values['SOFR'] - values['DFF']) * 100.0, 6),
            )
            if sofr_history:
                collected['sofr_spread'] = CollectedSeries('sofr_spread', 'fred/SOFR-DFF', sofr_history)
        except Exception as exc:
            _record_failure('SOFR-DFF', exc)

        try:
            dgs10 = raw_cache.get('DGS10') or self._fetch_fred_csv(client, 'DGS10', start, end)
            dgs2 = raw_cache.get('DGS2') or self._fetch_fred_csv(client, 'DGS2', start, end)
            term_history = _build_pointwise_series(
                start,
                end,
                {'DGS10': dgs10, 'DGS2': dgs2},
                lambda values: round((values['DGS10'] - values['DGS2']) * 100.0, 6),
            )
            if term_history:
                collected['term_premium_proxy'] = CollectedSeries('term_premium_proxy', 'fred/DGS10-DGS2', term_history)
        except Exception as exc:
            _record_failure('DGS10-DGS2', exc)

        try:
            move_history = self._build_move_proxy_history(client, start, end, raw_cache)
            if move_history:
                collected['move_index'] = CollectedSeries('move_index', 'proxy/fred-rates-vol', move_history)
        except Exception as exc:
            _record_failure('MOVE_PROXY', exc)

        try:
            eur_basis, jpy_basis = self._build_basis_proxy_histories(client, start, end, raw_cache)
            if eur_basis:
                collected['eur_usd_basis'] = CollectedSeries('eur_usd_basis', 'proxy/fred-eur-basis', eur_basis)
            if jpy_basis:
                collected['jpy_usd_basis'] = CollectedSeries('jpy_usd_basis', 'proxy/fred-jpy-basis', jpy_basis)
        except Exception as exc:
            _record_failure('BASIS_PROXY', exc)

        try:
            labor_series = self._build_labor_module_histories(client, start, end, raw_cache)
            collected.update(labor_series)
        except Exception as exc:
            _record_failure('BLS_LABOR', exc)

        try:
            expectations_series = self._build_inflation_expectations_histories(client, start, end, raw_cache)
            collected.update(expectations_series)
        except Exception as exc:
            _record_failure('EXPECTATIONS_CURVE', exc)

        live_count = len(collected)
        if live_count == 0:
            detail = '; '.join(failures[:8]) if failures else 'no FRED responses returned'
            return {}, f'FRED live download unavailable; using demo fallback for market series. Failures: {detail}.'
        if failures:
            detail = '; '.join(failures[:8])
            return collected, (
                f'FRED live and proxy series active for {live_count} indicators; '
                f'demo fallback remains for unavailable series. Failures: {detail}.'
            )
        return collected, f'FRED live and proxy series active for {live_count} indicators.'

    def _collect_ecb_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> tuple[dict[str, CollectedSeries], str]:
        try:
            history = self._fetch_ecb_deposit_rate_history(client, start - timedelta(days=720), end)
            dense = _densify_daily(history, start, end)
            if not dense:
                return {}, 'ECB official rates page reachable, but no deposit-rate history was parsed.'
            return {
                'ecb_deposit_rate': CollectedSeries(
                    key='ecb_deposit_rate',
                    source='ecb/key-rates-deposit-facility',
                    history=dense,
                )
            }, 'ECB official deposit facility rate is live.'
        except Exception:
            return {}, 'ECB official euro-rate feed unavailable; support layer will fall back to other public sources.'

    def _collect_nyfed_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> tuple[dict[str, CollectedSeries], str]:
        collected: dict[str, CollectedSeries] = {}
        failures: list[str] = []
        try:
            sofr = self._fetch_nyfed_rate_history(client, NYFED_SOFR_URL, start, end, 'SOFR')
            sofr_dense = _densify_daily(sofr, start, end)
            if sofr_dense:
                collected['sofr_rate'] = CollectedSeries(
                    key='sofr_rate',
                    source='nyfed/sofr',
                    history=sofr_dense,
                )
            effr_midpoint = self._fetch_nyfed_effr_midpoint_history(client, start, end)
            sofr_spread = _build_pointwise_series(
                start,
                end,
                {'SOFR': sofr, 'EFFR_MID': effr_midpoint},
                lambda values: round((values['SOFR'] - values['EFFR_MID']) * 100.0, 6),
            )
            if sofr_spread:
                collected['sofr_spread'] = CollectedSeries(
                    key='sofr_spread',
                    source='nyfed/sofr-target-midpoint',
                    history=sofr_spread,
                )
        except Exception:
            failures.append('SOFR_EFFR')

        live_count = len(collected)
        if live_count == 0:
            return {}, 'NY Fed SOFR/EFFR feeds unavailable; SOFR spread will fall back to demo values.'
        if failures:
            return collected, f'NY Fed rates live for {live_count} indicators; fallback remains for unavailable NY Fed series.'
        return collected, f'NY Fed rates live for {live_count} indicators.'

    def _collect_fed_h41_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> tuple[dict[str, CollectedSeries], str]:
        collected: dict[str, CollectedSeries] = {}
        failures: list[str] = []

        try:
            fima = self._fetch_h41_weekly_series(client, start, end, 'Foreign official and international accounts')
            fima_dense = _densify_daily(fima, start, end)
            if fima_dense:
                collected['fima_repo_usage'] = CollectedSeries(
                    key='fima_repo_usage',
                    source='fed/h41-foreign-official-accounts',
                    history=fima_dense,
                )
        except Exception:
            failures.append('FIMA')

        try:
            swap_lines = self._fetch_h41_weekly_series(client, start, end, 'Central bank liquidity swaps')
            swap_dense = _densify_daily(swap_lines, start, end)
            if swap_dense:
                collected['fed_swap_line_usage'] = CollectedSeries(
                    key='fed_swap_line_usage',
                    source='fed/h41-central-bank-liquidity-swaps',
                    history=swap_dense,
                )
        except Exception:
            failures.append('SWAP_LINES')

        live_count = len(collected)
        if live_count == 0:
            return {}, 'Federal Reserve H.4.1 feeds unavailable; FIMA and swap-line metrics will fall back if needed.'
        if failures:
            return collected, f'Federal Reserve H.4.1 feeds live for {live_count} indicators; fallback remains for unavailable H.4.1 series.'
        return collected, f'Federal Reserve H.4.1 feeds live for {live_count} indicators.'

    def _collect_support_series(
        self,
        start: date,
        end: date,
        collected: dict[str, CollectedSeries],
    ) -> tuple[dict[str, CollectedSeries], str]:
        support: dict[str, CollectedSeries] = {}
        status_parts: list[str] = []

        eurusd = collected.get('eur_usd_spot')
        usdjpy = collected.get('usd_jpy_spot')
        usdcny = collected.get('usd_cny_spot')
        sofr = collected.get('sofr_rate')
        ecb = collected.get('ecb_deposit_rate')
        jpy = collected.get('japan_short_rate')
        oil = collected.get('oil_price')
        expectations = collected.get('expectations_entrenchment_score')
        tax_base = collected.get('employment_tax_base_proxy')
        payroll = collected.get('payroll_momentum')
        receipts = collected.get('federal_receipts_quality')
        spx = collected.get('spx_equal_weight')
        vix = collected.get('vix_index')

        if all([eurusd, usdjpy, sofr, ecb, jpy]):
            history = _build_synthetic_usd_funding_pressure_history(
                eurusd.history,
                usdjpy.history,
                sofr.history,
                ecb.history,
                jpy.history,
                start,
                end,
            )
            if history:
                support['synthetic_usd_funding_pressure'] = CollectedSeries(
                    key='synthetic_usd_funding_pressure',
                    source='synthetic/yahoo-ecb-fred-funding-pressure',
                    history=history,
                )
                status_parts.append('synthetic USD funding pressure')

        if usdjpy and sofr:
            jpy_local_rate_history = jpy.history if jpy else _build_constant_history(start, end, 0.5)
            history = _build_basis_proxy_series(
                start=start,
                end=end,
                fx_observations=_history_to_dated_observations(usdjpy.history),
                usd_rate_observations=_history_to_dated_observations(sofr.history),
                local_rate_observations=_history_to_dated_observations(jpy_local_rate_history),
                rate_multiplier=7.5,
                vol_multiplier=2.2,
                floor_value=8.0,
                ceiling_value=90.0,
            )
            if history:
                support['jpy_usd_basis'] = CollectedSeries(
                    key='jpy_usd_basis',
                    source='support/jpy-usd-funding-stress',
                    history=history,
                )
                status_parts.append('JPY funding-stress support')

        if oil and usdjpy:
            history = _build_local_currency_oil_stress_history(oil.history, usdjpy.history, start, end, mode='multiply')
            if history:
                support['oil_in_yen_stress'] = CollectedSeries(
                    key='oil_in_yen_stress',
                    source='support/brent-usdjpy-local-cost',
                    history=history,
                )
                status_parts.append('oil-in-yen stress')

        if oil and eurusd:
            history = _build_local_currency_oil_stress_history(oil.history, eurusd.history, start, end, mode='divide')
            if history:
                support['oil_in_eur_stress'] = CollectedSeries(
                    key='oil_in_eur_stress',
                    source='support/brent-eurusd-local-cost',
                    history=history,
                )
                status_parts.append('oil-in-euro stress')

        if oil and usdcny:
            history = _build_local_currency_oil_stress_history(oil.history, usdcny.history, start, end, mode='multiply')
            if history:
                support['oil_in_cny_stress'] = CollectedSeries(
                    key='oil_in_cny_stress',
                    source='support/brent-usdcny-local-cost',
                    history=history,
                )
                status_parts.append('oil-in-yuan stress')

        importer_history = _build_weighted_composite_history(
            [
                (support.get('oil_in_yen_stress').history if support.get('oil_in_yen_stress') else [], 0.45),
                (support.get('oil_in_eur_stress').history if support.get('oil_in_eur_stress') else [], 0.35),
                (support.get('oil_in_cny_stress').history if support.get('oil_in_cny_stress') else [], 0.20),
            ],
            start,
            end,
        )
        if importer_history:
            support['external_importer_stress'] = CollectedSeries(
                key='external_importer_stress',
                source='support/japan-europe-china-importer-stress',
                history=importer_history,
            )
            status_parts.append('external importer stress')

        if importer_history and tax_base:
            tax_base_stress = _build_threshold_stress_history(tax_base.history, warning=3.0, critical=0.0, direction='low', start=start, end=end)
            payroll_stress = (
                _build_threshold_stress_history(payroll.history, warning=100.0, critical=0.0, direction='low', start=start, end=end)
                if payroll
                else []
            )
            receipts_stress = (
                _build_threshold_stress_history(receipts.history, warning=45.0, critical=35.0, direction='low', start=start, end=end)
                if receipts
                else []
            )
            household_history = _build_weighted_composite_history(
                [
                    (support.get('external_importer_stress').history if support.get('external_importer_stress') else [], 0.55),
                    (tax_base_stress, 0.25),
                    (receipts_stress, 0.10),
                    (payroll_stress, 0.10),
                ],
                start,
                end,
            )
            if household_history:
                support['household_real_income_squeeze'] = CollectedSeries(
                    key='household_real_income_squeeze',
                    source='support/income-energy-squeeze',
                    history=household_history,
                )
                status_parts.append('household real-income squeeze')

        if vix and spx and receipts:
            vix_stress = _build_threshold_stress_history(vix.history, warning=22.0, critical=30.0, direction='high', start=start, end=end)
            equity_stress = _build_threshold_stress_history(spx.history, warning=470.0, critical=430.0, direction='low', start=start, end=end)
            receipts_stress = _build_threshold_stress_history(receipts.history, warning=45.0, critical=35.0, direction='low', start=start, end=end)
            receipts_market_history = _build_weighted_composite_history(
                [
                    (vix_stress, 0.45),
                    (equity_stress, 0.25),
                    (receipts_stress, 0.30),
                ],
                start,
                end,
            )
            if receipts_market_history:
                support['tax_receipts_market_stress'] = CollectedSeries(
                    key='tax_receipts_market_stress',
                    source='synthetic/vix-equity-receipts-stress',
                    history=receipts_market_history,
                )
                status_parts.append('tax-receipts market stress')

        if not support:
            return {}, 'FX support layer incomplete; synthetic funding, importer, and receipts composites were unavailable on this refresh.'
        return support, f"Support layer is live for {', '.join(status_parts)}."

    def _collect_treasury_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> tuple[dict[str, CollectedSeries], str]:
        collected: dict[str, CollectedSeries] = {}
        failures: list[str] = []

        try:
            rows = self._fetch_treasury_auctions(client, start - timedelta(days=365), end)
            auction_histories = _compute_auction_stress_histories(rows, start, end)
            if auction_histories:
                for key, history in auction_histories.items():
                    collected[key] = CollectedSeries(
                        key=key,
                        source='treasury/auctions_query',
                        history=history,
                    )
            else:
                failures.append('AUCTIONS_EMPTY')
        except Exception:
            failures.append('AUCTIONS')

        try:
            receipts = self._fetch_treasury_dts_series(
                client,
                start - timedelta(days=420),
                end,
                category='Taxes - Withheld Individual/FICA',
            )
            receipts_quality = _build_receipts_quality_history(receipts, start, end)
            if receipts_quality:
                collected['federal_receipts_quality'] = CollectedSeries(
                    key='federal_receipts_quality',
                    source='treasury/dts-withheld-fica-quality',
                    history=receipts_quality,
                )
            tax_base = _build_trailing_sum_yoy_growth_history(receipts, start, end, window=20, lag=252)
            if tax_base:
                collected['employment_tax_base_proxy'] = CollectedSeries(
                    key='employment_tax_base_proxy',
                    source='treasury/dts-withheld-fica-yoy',
                    history=tax_base,
                )
        except Exception:
            failures.append('RECEIPTS')

        try:
            debt = self._fetch_treasury_debt_to_penny(client, start - timedelta(days=420), end)
            deficit_history = _build_debt_trend_stress_history(debt, start, end, lag=252)
            if deficit_history:
                collected['deficit_trend'] = CollectedSeries(
                    key='deficit_trend',
                    source='treasury/debt-to-penny',
                    history=deficit_history,
                )
        except Exception:
            failures.append('DEBT')

        try:
            ten_year, thirty_year = self._fetch_treasury_yield_curve_history(client, start, end)
            ten_dense = _densify_daily(ten_year, start, end)
            thirty_dense = _densify_daily(thirty_year, start, end)
            if ten_dense:
                collected['ten_year_yield'] = CollectedSeries(
                    key='ten_year_yield',
                    source='treasury/daily-yield-curve-10y',
                    history=ten_dense,
                )
            if thirty_dense:
                collected['thirty_year_yield'] = CollectedSeries(
                    key='thirty_year_yield',
                    source='treasury/daily-yield-curve-30y',
                    history=thirty_dense,
                )
        except Exception:
            failures.append('YIELD_CURVE')

        live_count = len(collected)
        if live_count == 0:
            return {}, 'Treasury auction and fiscal APIs unavailable; using demo fallback for fiscal indicators.'
        if failures:
            return collected, f'Treasury auction and fiscal data live for {live_count} indicators; fallback remains for unavailable Treasury series.'
        return collected, f'Treasury auction and fiscal data live for {live_count} indicators.'

    def _collect_yahoo_futures_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> tuple[dict[str, CollectedSeries], str]:
        collected: dict[str, CollectedSeries] = {}
        failures: list[str] = []
        try:
            wti_specs = _generate_contract_specs('CL', '.NYM', start, end, monthly=True, roll_lead_days=35)
            wti_bars = self._fetch_contract_bar_map(client, wti_specs, start, end)
            history = _build_calendar_spread_history(wti_specs, wti_bars, start, end, months_out=6)
            if history:
                collected['wti_prompt_spread'] = CollectedSeries('wti_prompt_spread', 'market/yahoo-cl-calendar', history)
        except Exception:
            failures.append('WTI_CALENDAR')

        try:
            brent_specs = _generate_contract_specs('BZ', '.NYM', start, end, monthly=True, roll_lead_days=35)
            brent_bars = self._fetch_contract_bar_map(client, brent_specs, start, end)
            history = _build_calendar_spread_history(brent_specs, brent_bars, start, end, months_out=6)
            if history:
                collected['brent_prompt_spread'] = CollectedSeries('brent_prompt_spread', 'market/yahoo-bz-calendar', history)
        except Exception:
            failures.append('BRENT_CALENDAR')

        try:
            wti_front_history = _build_direct_yahoo_history(client, 'CL=F', start, end)
            if wti_front_history:
                collected['oil_price'] = CollectedSeries('oil_price', 'market/yahoo-wti-front-fallback', wti_front_history)
                try:
                    murban_history = _build_tradingview_single_value_history(client, 'ICEAD-ADM1!', end, end)
                    murban_spread = _build_latest_relative_spread_history(murban_history, wti_front_history)
                    if murban_spread:
                        collected['murban_wti_spread'] = CollectedSeries('murban_wti_spread', 'spread/tradingview-murban-vs-yahoo-wti', murban_spread)
                except Exception:
                    failures.append('MURBAN_WTI')
                try:
                    oman_history = _build_gme_oman_marker_history(client)
                    oman_spread = _build_latest_relative_spread_history(oman_history, wti_front_history)
                    if oman_spread:
                        collected['oman_wti_spread'] = CollectedSeries('oman_wti_spread', 'spread/gme-oman-vs-yahoo-wti', oman_spread)
                except Exception:
                    failures.append('OMAN_WTI')
                gulf_dislocation = _build_gulf_crude_dislocation_history(
                    collected.get('murban_wti_spread').history if collected.get('murban_wti_spread') else [],
                    collected.get('oman_wti_spread').history if collected.get('oman_wti_spread') else [],
                )
                if gulf_dislocation:
                    collected['gulf_crude_dislocation'] = CollectedSeries('gulf_crude_dislocation', 'spread/direct-gulf-crude-dislocation', gulf_dislocation)
            else:
                failures.extend(['MURBAN_WTI', 'OMAN_WTI', 'GULF_CRUDE_DISLOCATION'])
        except Exception:
            failures.extend(['WTI_FRONT_DIRECT', 'MURBAN_WTI', 'OMAN_WTI', 'GULF_CRUDE_DISLOCATION'])

        try:
            brent_front_history = _build_direct_yahoo_history(client, 'BZ=F', start, end)
            if brent_front_history:
                collected['oil_price'] = CollectedSeries('oil_price', 'market/yahoo-brent-front', brent_front_history)
        except Exception:
            failures.append('BRENT_FRONT_DIRECT')

        try:
            move_bars = _fetch_yahoo_bars(client, '^MOVE', start, end)
            if move_bars:
                move_history = _forward_fill_history(
                    _dedupe_history_points((bar.timestamp, round(bar.close, 6)) for bar in move_bars),
                    start,
                    end,
                )
                move_source = 'market/yahoo-move'
                try:
                    tradingview_move = _build_tradingview_single_value_history(client, 'TVC-MOVE', end, end)
                    move_history = _merge_move_histories(tradingview_move, move_history, start, end)
                    move_source = 'market/yahoo-move+tradingview-latest'
                except Exception:
                    pass
                collected['move_index'] = CollectedSeries('move_index', move_source, move_history)
            else:
                raise ValueError('No Yahoo MOVE bars returned')
        except Exception:
            try:
                fyi_history = _build_fyicenter_move_history(client, start, end)
                move_history = _forward_fill_history(fyi_history, start, end)
                move_source = 'reference/fyicenter-move-backfill'
                try:
                    tradingview_move = _build_tradingview_single_value_history(client, 'TVC-MOVE', end, end)
                    move_history = _merge_move_histories(tradingview_move, move_history, start, end)
                    move_source = 'reference/fyicenter-move-backfill+tradingview-latest'
                except Exception:
                    pass
                collected['move_index'] = CollectedSeries('move_index', move_source, move_history)
            except Exception:
                failures.append('MOVE_DIRECT')

        try:
            zn_specs = _generate_contract_specs('ZN', '.CBT', start, end, monthly=False, roll_lead_days=20)
            zn_bars = self._fetch_contract_bar_map(client, zn_specs, start, end)
            front_history = _build_front_contract_history(zn_specs, zn_bars, start, end)
            if front_history:
                depth_history = _build_treasury_depth_history(front_history)
                if depth_history:
                    collected['treasury_liquidity_proxy'] = CollectedSeries(
                        'treasury_liquidity_proxy',
                        'market/yahoo-zn-depth',
                        depth_history,
                    )
        except Exception:
            failures.append('TREASURY_DEPTH')

        try:
            zn_specs = _generate_contract_specs('ZN', '.CBT', start, end, monthly=False, roll_lead_days=20)
            zn_bars = self._fetch_contract_bar_map(client, zn_specs, start, end)
            front_history = _build_front_contract_history(zn_specs, zn_bars, start, end)
            dgs10 = self._fetch_fred_csv(client, 'DGS10', start, end)
            basis_history = _build_treasury_basis_history(front_history, _densify_daily(dgs10, start, end))
            if basis_history:
                collected['treasury_basis_proxy'] = CollectedSeries(
                    'treasury_basis_proxy',
                    'market/yahoo-zn-basis',
                    basis_history,
                )
        except Exception:
            failures.append('TREASURY_BASIS')

        try:
            gold_history = _build_direct_yahoo_history(client, 'GC=F', start, end)
            if gold_history:
                collected['gold_price'] = CollectedSeries('gold_price', 'market/yahoo-gc-futures', gold_history)
        except Exception:
            failures.append('GOLD')

        try:
            rsp_history = _build_direct_yahoo_history(client, 'RSP', start, end)
            if rsp_history:
                collected['spx_equal_weight'] = CollectedSeries('spx_equal_weight', 'market/yahoo-rsp', rsp_history)
        except Exception:
            failures.append('RSP')

        try:
            eurusd_history = _build_direct_yahoo_history(client, 'EURUSD=X', start, end)
            if eurusd_history:
                collected['eur_usd_spot'] = CollectedSeries('eur_usd_spot', 'market/yahoo-eurusd', eurusd_history)
        except Exception:
            failures.append('EURUSD_SPOT')

        try:
            usdjpy_history = _build_direct_yahoo_history(client, 'USDJPY=X', start, end)
            if usdjpy_history:
                collected['usd_jpy_spot'] = CollectedSeries('usd_jpy_spot', 'market/yahoo-usdjpy', usdjpy_history)
        except Exception:
            failures.append('USDJPY_SPOT')

        try:
            usdcny_history = _build_direct_yahoo_history(client, 'USDCNY=X', start, end)
            if usdcny_history:
                collected['usd_cny_spot'] = CollectedSeries('usd_cny_spot', 'market/yahoo-usdcny', usdcny_history)
        except Exception:
            failures.append('USDCNY_SPOT')

        try:
            vix_history = _build_direct_yahoo_history(client, '^VIX', start, end)
            if vix_history:
                collected['vix_index'] = CollectedSeries('vix_index', 'market/yahoo-vix', vix_history)
        except Exception:
            failures.append('VIX_DIRECT')

        live_count = len(collected)
        if live_count == 0:
            return {}, 'Yahoo futures market layer unavailable; using existing demo/proxy fallback for crude spreads and Treasury futures metrics.'
        if failures:
            return collected, f'Yahoo futures market layer active for {live_count} indicators; fallback remains for unavailable contracts.'
        return collected, f'Yahoo futures market layer active for {live_count} indicators.'

    def _build_move_proxy_history(
        self,
        client: httpx.Client,
        start: date,
        end: date,
        raw_cache: dict[str, list[tuple[date, float]]],
    ) -> list[tuple[datetime, float]]:
        dgs2 = raw_cache.get('DGS2') or self._fetch_fred_csv(client, 'DGS2', start, end)
        dgs10 = raw_cache.get('DGS10') or self._fetch_fred_csv(client, 'DGS10', start, end)
        dgs30 = raw_cache.get('DGS30') or self._fetch_fred_csv(client, 'DGS30', start, end)
        series = {
            'DGS2': _densify_daily(dgs2, start, end),
            'DGS10': _densify_daily(dgs10, start, end),
            'DGS30': _densify_daily(dgs30, start, end),
        }
        weights = {'DGS2': 0.2, 'DGS10': 0.5, 'DGS30': 0.3}
        window = 20
        history: list[tuple[datetime, float]] = []
        for index in range(len(series['DGS10'])):
            if index == 0:
                weighted_realized_vol = 0.0
            else:
                vol_components: list[float] = []
                for name, dense in series.items():
                    start_index = max(1, index - window + 1)
                    changes_bps = [
                        (dense[position][1] - dense[position - 1][1]) * 100.0
                        for position in range(start_index, index + 1)
                    ]
                    std_dev = _sample_stddev(changes_bps)
                    annualized = std_dev * math.sqrt(252.0)
                    vol_components.append(weights[name] * annualized)
                weighted_realized_vol = sum(vol_components)
            proxy_value = max(55.0, min(220.0, 60.0 + 1.5 * weighted_realized_vol))
            history.append((series['DGS10'][index][0], round(proxy_value, 6)))
        return history

    def _build_labor_module_histories(
        self,
        client: httpx.Client,
        start: date,
        end: date,
        raw_cache: dict[str, list[tuple[date, float]]],
    ) -> dict[str, CollectedSeries]:
        payems = raw_cache.get('PAYEMS') or self._fetch_fred_csv(client, 'PAYEMS', start - timedelta(days=550), end)
        wages = raw_cache.get('CES0500000003') or self._fetch_fred_csv(client, 'CES0500000003', start - timedelta(days=550), end)
        hours = raw_cache.get('AWHAETP') or self._fetch_fred_csv(client, 'AWHAETP', start - timedelta(days=550), end)
        temp_help = raw_cache.get('TEMPHELPS') or self._fetch_fred_csv(client, 'TEMPHELPS', start - timedelta(days=550), end)
        unemployment = raw_cache.get('UNRATE') or self._fetch_fred_csv(client, 'UNRATE', start - timedelta(days=550), end)

        collected: dict[str, CollectedSeries] = {}

        payroll_momentum = _build_period_change_history(payems, start, end, periods_back=3, pct=False, divisor=3.0)
        if payroll_momentum:
            collected['payroll_momentum'] = CollectedSeries('payroll_momentum', 'fred/PAYEMS-3MAVG', payroll_momentum)

        wage_stickiness = _build_period_change_history(wages, start, end, periods_back=12, pct=True)
        if wage_stickiness:
            collected['wage_stickiness'] = CollectedSeries('wage_stickiness', 'fred/CES0500000003-YOY', wage_stickiness)

        hours_momentum = _build_period_change_history(hours, start, end, periods_back=3, pct=False)
        if hours_momentum:
            collected['hours_worked_momentum'] = CollectedSeries('hours_worked_momentum', 'fred/AWHAETP-3MCHANGE', hours_momentum)

        temp_help_stress = _build_period_change_history(temp_help, start, end, periods_back=12, pct=True)
        if temp_help_stress:
            collected['temp_help_stress'] = CollectedSeries('temp_help_stress', 'fred/TEMPHELPS-YOY', temp_help_stress)

        employment_tax_base = _build_payroll_tax_base_history(payems, wages, hours, start, end)
        if employment_tax_base:
            collected['employment_tax_base_proxy'] = CollectedSeries('employment_tax_base_proxy', 'proxy/fred-payroll-tax-base', employment_tax_base)

        unemployment_dense = _densify_daily(unemployment, start, end)
        if unemployment_dense:
            collected['unemployment_rate'] = CollectedSeries('unemployment_rate', 'fred/UNRATE', unemployment_dense)

        return collected

    def _build_inflation_expectations_histories(
        self,
        client: httpx.Client,
        start: date,
        end: date,
        raw_cache: dict[str, list[tuple[date, float]]],
    ) -> dict[str, CollectedSeries]:
        fetch_start = start - timedelta(days=1100)
        series_ids = {
            'EXPINF1YR': 'EXPINF1YR',
            'EXPINF2YR': 'EXPINF2YR',
            'EXPINF5YR': 'EXPINF5YR',
            'EXPINF10YR': 'EXPINF10YR',
            'EXPINF20YR': 'EXPINF20YR',
            'EXPINF30YR': 'EXPINF30YR',
            'T5YIFRM': 'T5YIFRM',
            'MICH': 'MICH',
        }
        raw: dict[str, list[tuple[date, float]]] = {}
        for series_id in series_ids:
            raw[series_id] = raw_cache.get(series_id) or self._fetch_fred_csv(client, series_id, fetch_start, end)

        curve_inputs = {key: raw[key] for key in ('EXPINF1YR', 'EXPINF2YR', 'EXPINF5YR', 'EXPINF10YR', 'EXPINF20YR', 'EXPINF30YR')}
        level_history = _build_pointwise_series(
            start,
            end,
            curve_inputs,
            lambda values: round(
                0.16 * values['EXPINF1YR']
                + 0.14 * values['EXPINF2YR']
                + 0.2 * values['EXPINF5YR']
                + 0.2 * values['EXPINF10YR']
                + 0.15 * values['EXPINF20YR']
                + 0.15 * values['EXPINF30YR'],
                6,
            ),
        )
        slope_history = _build_pointwise_series(
            start,
            end,
            {'EXPINF1YR': raw['EXPINF1YR'], 'EXPINF10YR': raw['EXPINF10YR']},
            lambda values: round((values['EXPINF1YR'] - values['EXPINF10YR']) * 100.0, 6),
        )
        curvature_history = _build_pointwise_series(
            start,
            end,
            {'EXPINF2YR': raw['EXPINF2YR'], 'EXPINF5YR': raw['EXPINF5YR'], 'EXPINF10YR': raw['EXPINF10YR']},
            lambda values: round(((2.0 * values['EXPINF5YR']) - values['EXPINF2YR'] - values['EXPINF10YR']) * 100.0, 6),
        )
        survey_gap_history = _build_pointwise_series(
            start,
            end,
            {'MICH': raw['MICH'], 'EXPINF1YR': raw['EXPINF1YR']},
            lambda values: round((values['MICH'] - values['EXPINF1YR']) * 100.0, 6),
        )
        forward_history = _densify_daily(raw['T5YIFRM'], start, end)
        entrenchment_history = _build_expectations_entrenchment_history(
            level_history,
            forward_history,
            slope_history,
            curvature_history,
            survey_gap_history,
            start,
            end,
        )

        collected: dict[str, CollectedSeries] = {}
        if forward_history:
            collected['expected_inflation_5y5y'] = CollectedSeries('expected_inflation_5y5y', 'fred/T5YIFRM', forward_history)
        if level_history:
            collected['inflation_expectations_level'] = CollectedSeries('inflation_expectations_level', 'fred/EXPINF-curve-level', level_history)
        if slope_history:
            collected['inflation_expectations_slope'] = CollectedSeries('inflation_expectations_slope', 'fred/EXPINF-curve-slope', slope_history)
        if curvature_history:
            collected['inflation_expectations_curvature'] = CollectedSeries('inflation_expectations_curvature', 'fred/EXPINF-curve-curvature', curvature_history)
        if survey_gap_history:
            collected['survey_market_expectations_gap'] = CollectedSeries('survey_market_expectations_gap', 'fred/MICH-vs-EXPINF1YR', survey_gap_history)
        if entrenchment_history:
            collected['expectations_entrenchment_score'] = CollectedSeries('expectations_entrenchment_score', 'fred/expectations-entrenchment-composite', entrenchment_history)
        return collected

    def _build_basis_proxy_histories(
        self,
        client: httpx.Client,
        start: date,
        end: date,
        raw_cache: dict[str, list[tuple[date, float]]],
    ) -> tuple[list[tuple[datetime, float]], list[tuple[datetime, float]]]:
        sofr = raw_cache.get('SOFR') or self._fetch_fred_csv(client, 'SOFR', start, end)
        eur_policy = self._fetch_fred_csv(client, 'ECBDFR', start, end)
        jpy_policy = self._fetch_fred_csv(client, 'IRSTCI01JPM156N', start, end)
        eurusd = self._fetch_fred_csv(client, 'DEXUSEU', start, end)
        usdjpy = self._fetch_fred_csv(client, 'DEXJPUS', start, end)

        eur_history = _build_basis_proxy_series(
            start=start,
            end=end,
            fx_observations=eurusd,
            usd_rate_observations=sofr,
            local_rate_observations=eur_policy,
            rate_multiplier=6.5,
            vol_multiplier=2.5,
            floor_value=5.0,
            ceiling_value=80.0,
        )
        jpy_history = _build_basis_proxy_series(
            start=start,
            end=end,
            fx_observations=usdjpy,
            usd_rate_observations=sofr,
            local_rate_observations=jpy_policy,
            rate_multiplier=7.5,
            vol_multiplier=2.2,
            floor_value=8.0,
            ceiling_value=90.0,
        )
        return eur_history, jpy_history

    def _fetch_fred_csv(
        self,
        client: httpx.Client,
        series_id: str,
        start: date,
        end: date,
        transform: Callable[[float], float] | None = None,
    ) -> list[tuple[date, float]]:
        response = client.get(
            FRED_BASE_URL,
            params={
                'id': series_id,
                'cosd': start.isoformat(),
                'coed': end.isoformat(),
            },
            timeout=self.fred_timeout_seconds,
        )
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        observations: list[tuple[date, float]] = []
        value_field = series_id
        for row in reader:
            value = row.get(value_field)
            observed_at = row.get('observation_date')
            if value in {None, '', '.'} or observed_at in {None, ''}:
                continue
            numeric_value = float(value)
            observations.append((date.fromisoformat(observed_at), transform(numeric_value) if transform else numeric_value))
        if not observations:
            raise ValueError(f'No observations returned for {series_id}')
        return observations

    def _fetch_ecb_deposit_rate_history(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> list[tuple[date, float]]:
        response = client.get('https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html')
        response.raise_for_status()
        text = response.text
        rows = re.findall(
            r'<tr>\s*<td class="number"><strong>(\d{4})</strong></td>\s*<td class="number">([^<]+)</td>\s*<td class="number">([^<]+)</td>',
            text,
            flags=re.IGNORECASE,
        )
        observations: list[tuple[date, float]] = []
        month_lookup = {
            'jan': 1,
            'feb': 2,
            'mar': 3,
            'apr': 4,
            'may': 5,
            'jun': 6,
            'jul': 7,
            'aug': 8,
            'sep': 9,
            'oct': 10,
            'nov': 11,
            'dec': 12,
        }
        for year_raw, day_month_raw, deposit_raw in rows:
            cleaned = day_month_raw.replace('.', '').strip()
            parts = cleaned.split()
            if len(parts) != 2:
                continue
            day = int(parts[0])
            month = month_lookup.get(parts[1][:3].lower())
            value = _safe_float(deposit_raw)
            if month is None or value is None:
                continue
            observed_at = date(int(year_raw), month, day)
            if observed_at <= end and observed_at >= start:
                observations.append((observed_at, value))
            elif observed_at < start:
                observations.append((observed_at, value))
        if not observations:
            raise ValueError('No ECB deposit-rate observations parsed')
        observations = sorted({observed_at: value for observed_at, value in observations}.items(), key=lambda item: item[0])
        return observations

    def _fetch_treasury_auctions(self, client: httpx.Client, start: date, end: date) -> list[dict[str, str]]:
        response = client.get(
            TREASURY_AUCTIONS_URL,
            params={
                'page[size]': 500,
                'sort': 'auction_date',
                'filter': f'auction_date:gte:{start.isoformat()},auction_date:lte:{end.isoformat()}',
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get('data', [])

    def _fetch_treasury_dts_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
        *,
        category: str,
    ) -> list[tuple[date, float]]:
        response = client.get(
            TREASURY_DTS_URL,
            params={
                'page[size]': 5000,
                'sort': 'record_date',
                'filter': f'record_date:gte:{start.isoformat()},record_date:lte:{end.isoformat()},transaction_type:in:(Deposits),transaction_catg:in:({category})',
            },
        )
        response.raise_for_status()
        payload = response.json()
        observations: list[tuple[date, float]] = []
        for row in payload.get('data', []):
            observed_at = row.get('record_date')
            value = _safe_float(row.get('transaction_today_amt'))
            if observed_at and value is not None:
                observations.append((date.fromisoformat(observed_at), value))
        if not observations:
            raise ValueError(f'No DTS observations returned for {category}')
        return observations

    def _fetch_treasury_debt_to_penny(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> list[tuple[date, float]]:
        response = client.get(
            TREASURY_DEBT_TO_PENNY_URL,
            params={
                'page[size]': 5000,
                'sort': 'record_date',
                'filter': f'record_date:gte:{start.isoformat()},record_date:lte:{end.isoformat()}',
                'format': 'json',
            },
        )
        response.raise_for_status()
        payload = response.json()
        observations: list[tuple[date, float]] = []
        for row in payload.get('data', []):
            observed_at = row.get('record_date')
            value = _safe_float(row.get('tot_pub_debt_out_amt'))
            if observed_at and value is not None:
                observations.append((date.fromisoformat(observed_at), value))
        if not observations:
            raise ValueError('No debt-to-penny observations returned')
        return observations

    def _fetch_treasury_yield_curve_history(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> tuple[list[tuple[date, float]], list[tuple[date, float]]]:
        ten_year: list[tuple[date, float]] = []
        thirty_year: list[tuple[date, float]] = []
        for year in range(start.year, end.year + 1):
            response = client.get(
                TREASURY_YIELD_CSV_URL.format(year=year),
                params={'type': 'daily_treasury_yield_curve'},
            )
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            for row in reader:
                observed_at = row.get('Date')
                if not observed_at:
                    continue
                day = datetime.strptime(observed_at, '%m/%d/%Y').date()
                if day < start or day > end:
                    continue
                ten = _safe_float(row.get('10 Yr'))
                thirty = _safe_float(row.get('30 Yr'))
                if ten is not None:
                    ten_year.append((day, ten))
                if thirty is not None:
                    thirty_year.append((day, thirty))
        if not ten_year and not thirty_year:
            raise ValueError('No Treasury yield-curve observations returned')
        return ten_year, thirty_year

    def _fetch_nyfed_rate_history(
        self,
        client: httpx.Client,
        url: str,
        start: date,
        end: date,
        expected_type: str,
    ) -> list[tuple[date, float]]:
        response = client.get(
            url,
            params={
                'startDate': start.isoformat(),
                'endDate': end.isoformat(),
                'type': 'rate',
            },
            timeout=min(self.timeout_seconds, 8.0),
        )
        response.raise_for_status()
        payload = response.json()
        observations: list[tuple[date, float]] = []
        for row in payload.get('refRates', []):
            if row.get('type') != expected_type:
                continue
            observed_at = row.get('effectiveDate')
            value = _safe_float(row.get('percentRate'))
            if observed_at and value is not None:
                observations.append((date.fromisoformat(observed_at), value))
        if not observations:
            raise ValueError(f'No NY Fed observations returned for {expected_type}')
        return observations

    def _fetch_nyfed_effr_midpoint_history(
        self,
        client: httpx.Client,
        start: date,
        end: date,
    ) -> list[tuple[date, float]]:
        response = client.get(
            NYFED_EFFR_URL,
            params={
                'startDate': start.isoformat(),
                'endDate': end.isoformat(),
                'type': 'rate',
            },
            timeout=min(self.timeout_seconds, 8.0),
        )
        response.raise_for_status()
        payload = response.json()
        observations: list[tuple[date, float]] = []
        for row in payload.get('refRates', []):
            observed_at = row.get('effectiveDate')
            floor = _safe_float(row.get('targetRateFrom'))
            cap = _safe_float(row.get('targetRateTo'))
            if observed_at and floor is not None and cap is not None:
                observations.append((date.fromisoformat(observed_at), (floor + cap) / 2.0))
        if not observations:
            raise ValueError('No NY Fed EFFR midpoint observations returned')
        return observations

    def _fetch_h41_weekly_series(
        self,
        client: httpx.Client,
        start: date,
        end: date,
        label: str,
    ) -> list[tuple[date, float]]:
        observations: list[tuple[date, float]] = []
        current = end
        while current.weekday() != 3:
            current -= timedelta(days=1)
        while current >= start:
            response = client.get(
                FED_H41_URL.format(stamp=current.strftime('%Y%m%d')),
                timeout=min(self.timeout_seconds, 8.0),
            )
            if response.status_code == 404:
                current -= timedelta(days=7)
                continue
            response.raise_for_status()
            value = _parse_h41_label_value(response.text, label)
            if value is not None:
                observations.append((current, value))
            current -= timedelta(days=7)
        if not observations:
            raise ValueError(f'No H.4.1 observations returned for {label}')
        observations.sort(key=lambda item: item[0])
        return observations

    def _fetch_contract_bar_map(
        self,
        client: httpx.Client,
        specs: list[ContractSpec],
        start: date,
        end: date,
    ) -> dict[str, dict[date, YahooBar]]:
        bar_map: dict[str, dict[date, YahooBar]] = {}
        for spec in specs:
            bars = _fetch_yahoo_bars(client, spec.symbol, start, end)
            if bars:
                bar_map[spec.symbol] = {bar.timestamp.date(): bar for bar in bars}
        if not bar_map:
            raise ValueError('No contract bars fetched')
        return bar_map


def _timestamp_for_day(day: date) -> datetime:
    return datetime.combine(day, time(hour=12), tzinfo=timezone.utc)


def _history_to_dated_observations(history: list[tuple[datetime, float]]) -> list[tuple[date, float]]:
    return [(timestamp.date(), float(value)) for timestamp, value in history]


def _build_constant_history(start: date, end: date, value: float) -> list[tuple[datetime, float]]:
    history: list[tuple[datetime, float]] = []
    current = start
    while current <= end:
        history.append((_timestamp_for_day(current), round(float(value), 6)))
        current += timedelta(days=1)
    return history


def _densify_daily(observations: list[tuple[date, float]], start: date, end: date) -> list[tuple[datetime, float]]:
    if not observations:
        return []
    observations = sorted(observations, key=lambda item: item[0])
    cursor = 0
    last_value = observations[0][1]
    dense: list[tuple[datetime, float]] = []
    current = start
    while current <= end:
        while cursor < len(observations) and observations[cursor][0] <= current:
            last_value = observations[cursor][1]
            cursor += 1
        dense.append((_timestamp_for_day(current), last_value))
        current += timedelta(days=1)
    return dense


def _build_pointwise_series(
    start: date,
    end: date,
    inputs: dict[str, list[tuple[date, float]]],
    formula: Callable[[dict[str, float]], float],
) -> list[tuple[datetime, float]]:
    if not inputs:
        return []
    value_maps = {name: {observed_at: value for observed_at, value in series} for name, series in inputs.items()}
    latest_values: dict[str, float | None] = {name: None for name in inputs}
    history: list[tuple[datetime, float]] = []
    current = start
    while current <= end:
        for name in inputs:
            if current in value_maps[name]:
                latest_values[name] = value_maps[name][current]
        if all(value is not None for value in latest_values.values()):
            values = {name: float(value) for name, value in latest_values.items() if value is not None}
            history.append((_timestamp_for_day(current), formula(values)))
        current += timedelta(days=1)
    return history


def _generate_contract_specs(
    root: str,
    suffix: str,
    start: date,
    end: date,
    *,
    monthly: bool,
    roll_lead_days: int,
) -> list[ContractSpec]:
    specs: list[ContractSpec] = []
    cursor = date(start.year, start.month, 1) - timedelta(days=62)
    limit = date(end.year, end.month, 1) + timedelta(days=365)
    while cursor <= limit:
        if monthly or cursor.month in {3, 6, 9, 12}:
            code = MONTH_CODES[cursor.month]
            year_code = str(cursor.year)[-2:]
            symbol = f'{root}{code}{year_code}{suffix}'
            roll_date = cursor - timedelta(days=roll_lead_days)
            specs.append(ContractSpec(symbol=symbol, delivery_month=cursor, roll_date=roll_date))
        next_month = cursor.month + 1
        next_year = cursor.year + (1 if next_month == 13 else 0)
        cursor = date(next_year, 1 if next_month == 13 else next_month, 1)
    return specs


def _fetch_yahoo_bars(client: httpx.Client, symbol: str, start: date, end: date) -> list[YahooBar]:
    period1 = int(datetime.combine(start - timedelta(days=5), time.min, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.combine(end + timedelta(days=1), time.max, tzinfo=timezone.utc).timestamp())
    response = client.get(YAHOO_CHART_URL.format(symbol=quote(symbol, safe='')), params={'period1': period1, 'period2': period2, 'interval': '1d', 'includePrePost': 'false'})
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    result = payload.get('chart', {}).get('result') or []
    if not result:
        return []
    entry = result[0]
    timestamps = entry.get('timestamp') or []
    quote_data = (entry.get('indicators', {}).get('quote') or [{}])[0]
    closes = quote_data.get('close') or []
    highs = quote_data.get('high') or []
    lows = quote_data.get('low') or []
    volumes = quote_data.get('volume') or []
    bars: list[YahooBar] = []
    for ts, close, high, low, volume in zip(timestamps, closes, highs, lows, volumes):
        if close is None or high is None or low is None:
            continue
        timestamp = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        bars.append(YahooBar(timestamp=timestamp, close=float(close), high=float(high), low=float(low), volume=float(volume or 0.0)))
    return bars


def _build_direct_yahoo_history(client: httpx.Client, symbol: str, start: date, end: date) -> list[tuple[datetime, float]]:
    bars = _fetch_yahoo_bars(client, symbol, start, end)
    return _forward_fill_history([(bar.timestamp, round(bar.close, 6)) for bar in bars], start, end)


def _build_tradingview_single_value_history(client: httpx.Client, symbol: str, start: date, end: date) -> list[tuple[datetime, float]]:
    response = client.get(
        TRADINGVIEW_SYMBOL_URL.format(symbol=symbol),
        headers={'Referer': 'https://www.tradingview.com/'},
    )
    response.raise_for_status()
    text = response.text
    match = re.search(r'"trade":\{"price":([0-9.]+)\}.*?"daily_bar":\{"close":"([0-9.]+)".*?"time":"([0-9]+)"', text)
    if not match:
        raise ValueError(f'Unable to extract TradingView value for {symbol}')
    _, close_value, raw_ts = match.groups()
    day = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc).date()
    direct_history = [(datetime.fromtimestamp(int(raw_ts), tz=timezone.utc), round(float(close_value), 6))]
    if day < start:
        start = day
    return _forward_fill_history(direct_history, start, end)


def _dedupe_history_points(history: Iterable[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    value_map: dict[date, float] = {}
    for timestamp, value in history:
        value_map[timestamp.date()] = value
    return [(_timestamp_for_day(day), round(float(value), 6)) for day, value in sorted(value_map.items())]


def _build_gme_oman_marker_history(client: httpx.Client) -> list[tuple[datetime, float]]:
    response = client.get(GME_DATA_URL, headers={'Referer': 'https://www.gulfmerc.com/'})
    response.raise_for_status()
    text = response.text
    match = re.search(r'OQD Marker Price\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+is\s*</span>\s*([0-9.]+)\s*<span', text, flags=re.IGNORECASE)
    if not match:
        raise ValueError('Unable to extract Oman marker price from GME data page')
    observed_at, value = match.groups()
    day = datetime.strptime(observed_at, '%B %d, %Y').date()
    return [(_timestamp_for_day(day), round(float(value), 6))]


def _build_latest_relative_spread_history(
    lhs_history: list[tuple[datetime, float]],
    rhs_history: list[tuple[datetime, float]],
) -> list[tuple[datetime, float]]:
    if not lhs_history or not rhs_history:
        return []
    lhs_ts, lhs_value = lhs_history[-1]
    rhs_candidates = [value for timestamp, value in rhs_history if timestamp.date() <= lhs_ts.date()]
    if not rhs_candidates:
        return []
    return [(lhs_ts, round(lhs_value - rhs_candidates[-1], 6))]


def _build_gulf_crude_dislocation_history(
    murban_spread_history: list[tuple[datetime, float]],
    oman_spread_history: list[tuple[datetime, float]],
) -> list[tuple[datetime, float]]:
    latest_points: list[tuple[datetime, float]] = []
    if murban_spread_history:
        latest_points.append(murban_spread_history[-1])
    if oman_spread_history:
        latest_points.append(oman_spread_history[-1])
    if not latest_points:
        return []
    timestamp = max(point[0] for point in latest_points)
    value = sum(point[1] for point in latest_points) / len(latest_points)
    return [(timestamp, round(value, 6))]


def _build_fyicenter_move_history(client: httpx.Client, start: date, end: date) -> list[tuple[datetime, float]]:
    response = client.get(FYICENTER_MOVE_URL, headers={'Referer': 'https://finance.fyicenter.com/'})
    response.raise_for_status()
    text = response.text
    block_match = re.search(r'Historical values in Point:.*?<pre>(.*?)</pre>', text, flags=re.IGNORECASE | re.DOTALL)
    if not block_match:
        raise ValueError('Unable to locate FYIcenter MOVE history block')
    block = re.sub(r'<[^>]+>', '', block_match.group(1))
    observations: list[tuple[datetime, float]] = []
    for line in block.splitlines():
        match = re.match(r'\s*(\d{4}-\d{2}-\d{2})\s+([0-9.]+)', line)
        if not match:
            continue
        observed_at, value = match.groups()
        day = date.fromisoformat(observed_at)
        if start <= day <= end:
            observations.append((_timestamp_for_day(day), round(float(value), 6)))
    if not observations:
        raise ValueError('No FYIcenter MOVE observations parsed in range')
    return observations


def _merge_move_histories(
    primary_history: list[tuple[datetime, float]],
    fallback_history: list[tuple[datetime, float]],
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    value_map: dict[date, float] = {timestamp.date(): value for timestamp, value in fallback_history}
    value_map.update({timestamp.date(): value for timestamp, value in primary_history})
    merged = sorted(((_timestamp_for_day(day), value) for day, value in value_map.items() if start <= day <= end), key=lambda item: item[0])
    return _forward_fill_history(merged, start, end) if merged else []


def _active_contract_window_for_day(specs: list[ContractSpec], day: date, months_out: int) -> tuple[ContractSpec, ContractSpec] | None:
    ordered = sorted([spec for spec in specs if spec.roll_date > day], key=lambda spec: spec.delivery_month)
    if len(ordered) < months_out:
        ordered = sorted(specs, key=lambda spec: spec.delivery_month)
    if len(ordered) < months_out:
        return None
    return ordered[0], ordered[months_out - 1]


def _build_calendar_spread_history(
    specs: list[ContractSpec],
    bar_map: dict[str, dict[date, YahooBar]],
    start: date,
    end: date,
    *,
    months_out: int = 2,
) -> list[tuple[datetime, float]]:
    history: list[tuple[datetime, float]] = []
    current = start
    while current <= end:
        contract_window = _active_contract_window_for_day(specs, current, months_out)
        if contract_window is None:
            current += timedelta(days=1)
            continue
        first_bar = bar_map.get(contract_window[0].symbol, {}).get(current)
        later_bar = bar_map.get(contract_window[1].symbol, {}).get(current)
        if first_bar and later_bar:
            history.append((_timestamp_for_day(current), round(first_bar.close - later_bar.close, 6)))
        current += timedelta(days=1)
    return _forward_fill_history(history, start, end)


def _active_contracts_for_day(specs: list[ContractSpec], day: date) -> tuple[ContractSpec, ContractSpec]:
    selected = _active_contract_window_for_day(specs, day, 2)
    if selected is None:
        ordered = sorted(specs, key=lambda spec: spec.delivery_month)
        if len(ordered) < 2:
            raise ValueError('Insufficient contracts available for active contract selection')
        return ordered[0], ordered[1]
    return selected


def _build_front_contract_history(
    specs: list[ContractSpec],
    bar_map: dict[str, dict[date, YahooBar]],
    start: date,
    end: date,
) -> list[YahooBar]:
    history: list[YahooBar] = []
    current = start
    last_bar: YahooBar | None = None
    while current <= end:
        contract_window = _active_contract_window_for_day(specs, current, 1)
        if contract_window is None:
            current += timedelta(days=1)
            continue
        front = contract_window[0]
        bar = bar_map.get(front.symbol, {}).get(current)
        if bar is not None:
            last_bar = bar
        if last_bar is not None:
            history.append(YahooBar(timestamp=_timestamp_for_day(current), close=last_bar.close, high=last_bar.high, low=last_bar.low, volume=last_bar.volume))
        current += timedelta(days=1)
    return history


def _build_treasury_depth_history(front_history: list[YahooBar], window: int = 20) -> list[tuple[datetime, float]]:
    raw_values: list[float] = []
    for bar in front_history:
        intraday_range_bps = abs(bar.high - bar.low) * 100.0
        liquidity = intraday_range_bps / max(math.sqrt(max(bar.volume, 1.0)), 1.0)
        raw_values.append(liquidity)
    stress_values = _rolling_percentile_series(raw_values, window=window)
    return [(bar.timestamp, round(value, 6)) for bar, value in zip(front_history, stress_values)]


def _build_treasury_basis_history(
    front_history: list[YahooBar],
    ten_year_yield_history: list[tuple[datetime, float]],
    window: int = 20,
) -> list[tuple[datetime, float]]:
    cash_price_proxy = [100.0 - 8.0 * item[1] for item in ten_year_yield_history]
    futures_prices = [bar.close for bar in front_history]
    divergence: list[float] = []
    for index in range(len(front_history)):
        start_index = max(0, index - window + 1)
        future_slice = futures_prices[start_index:index + 1]
        cash_slice = cash_price_proxy[start_index:index + 1]
        future_z = _trailing_zscore(future_slice)
        cash_z = _trailing_zscore(cash_slice)
        divergence.append(abs(future_z - cash_z) * 25.0)
    stress_values = _rolling_percentile_series(divergence, window=window)
    return [(front_history[index].timestamp, round(stress_values[index], 6)) for index in range(len(front_history))]


def _forward_fill_history(
    history: list[tuple[datetime, float]],
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    if not history:
        return []
    value_map = {timestamp.date(): value for timestamp, value in history}
    current = start
    last_value = history[0][1]
    dense: list[tuple[datetime, float]] = []
    while current <= end:
        if current in value_map:
            last_value = value_map[current]
        dense.append((_timestamp_for_day(current), last_value))
        current += timedelta(days=1)
    return dense


def _build_period_change_history(
    observations: list[tuple[date, float]],
    start: date,
    end: date,
    *,
    periods_back: int,
    pct: bool,
    divisor: float = 1.0,
) -> list[tuple[datetime, float]]:
    if len(observations) <= periods_back:
        return []
    derived: list[tuple[date, float]] = []
    ordered = sorted(observations, key=lambda item: item[0])
    for index in range(periods_back, len(ordered)):
        current_day, current_value = ordered[index]
        prior_value = ordered[index - periods_back][1]
        if pct:
            if prior_value == 0:
                continue
            value = ((current_value / prior_value) - 1.0) * 100.0
        else:
            value = (current_value - prior_value) / divisor
        derived.append((current_day, round(value, 6)))
    return _densify_daily(derived, start, end)


def _parse_h41_label_value(text: str, label: str) -> float | None:
    index = text.lower().find(label.lower())
    if index == -1:
        return None
    snippet = text[index:index + 1200]
    match = re.search(r"font-weight:bold\">(?:&#xa0;|\s)*([0-9,]+)</span>", snippet, flags=re.IGNORECASE)
    if not match:
        return None
    return round(float(match.group(1).replace(',', '')) / 1000.0, 6)


def _build_payroll_tax_base_history(
    payrolls: list[tuple[date, float]],
    wages: list[tuple[date, float]],
    hours: list[tuple[date, float]],
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    payroll_map = {observed_at: value for observed_at, value in payrolls}
    wage_map = {observed_at: value for observed_at, value in wages}
    hour_map = {observed_at: value for observed_at, value in hours}
    common_dates = sorted(set(payroll_map) & set(wage_map) & set(hour_map))
    if len(common_dates) < 13:
        return []

    monthly_tax_base: list[tuple[date, float]] = []
    for observed_at in common_dates:
        monthly_tax_base.append((observed_at, payroll_map[observed_at] * wage_map[observed_at] * hour_map[observed_at]))

    return _build_period_change_history(monthly_tax_base, start, end, periods_back=12, pct=True)


def _build_basis_proxy_series(
    *,
    start: date,
    end: date,
    fx_observations: list[tuple[date, float]],
    usd_rate_observations: list[tuple[date, float]],
    local_rate_observations: list[tuple[date, float]],
    rate_multiplier: float,
    vol_multiplier: float,
    floor_value: float,
    ceiling_value: float,
    vol_window: int = 20,
) -> list[tuple[datetime, float]]:
    fx_dense = _densify_daily(fx_observations, start, end)
    usd_dense = _densify_daily(usd_rate_observations, start, end)
    local_dense = _densify_daily(local_rate_observations, start, end)
    history: list[tuple[datetime, float]] = []

    for index, (timestamp, fx_value) in enumerate(fx_dense):
        if index == 0:
            fx_vol = 0.0
        else:
            start_index = max(1, index - vol_window + 1)
            returns = []
            for position in range(start_index, index + 1):
                prior = fx_dense[position - 1][1]
                current = fx_dense[position][1]
                if prior <= 0 or current <= 0:
                    continue
                returns.append(math.log(current / prior))
            fx_vol = _sample_stddev(returns) * math.sqrt(252.0) * 100.0

        rate_diff = max(0.0, usd_dense[index][1] - local_dense[index][1])
        stress = rate_multiplier * rate_diff + vol_multiplier * fx_vol
        proxy_value = -max(floor_value, min(ceiling_value, stress))
        history.append((timestamp, round(proxy_value, 6)))
    return history


def _rolling_percentile_series(values: list[float], window: int) -> list[float]:
    output: list[float] = []
    for index, current in enumerate(values):
        start_index = max(0, index - window + 1)
        sample = values[start_index:index + 1]
        output.append(_percentile_rank(sample, current))
    return output


def _trailing_zscore(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    std_dev = _sample_stddev(values)
    if std_dev == 0:
        return 0.0
    return (values[-1] - mean) / std_dev


def _build_trailing_sum_yoy_growth_history(
    observations: list[tuple[date, float]],
    start: date,
    end: date,
    *,
    window: int = 20,
    lag: int = 252,
) -> list[tuple[datetime, float]]:
    ordered = sorted(observations, key=lambda item: item[0])
    if len(ordered) < window + lag:
        return []
    values = [float(value) for _, value in ordered]
    derived: list[tuple[date, float]] = []
    for index in range(window + lag - 1, len(ordered)):
        current_sum = sum(values[index - window + 1:index + 1])
        prior_end = index - lag
        prior_sum = sum(values[prior_end - window + 1:prior_end + 1])
        if prior_sum <= 0:
            continue
        growth = ((current_sum / prior_sum) - 1.0) * 100.0
        derived.append((ordered[index][0], round(growth, 6)))
    return _densify_daily(derived, start, end)


def _build_receipts_quality_history(
    observations: list[tuple[date, float]],
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    growth_history = _build_trailing_sum_yoy_growth_history(observations, start, end, window=20, lag=252)
    quality: list[tuple[datetime, float]] = []
    for timestamp, growth in growth_history:
        score = max(0.0, min(100.0, 50.0 + float(growth) * 4.0))
        quality.append((timestamp, round(score, 6)))
    return quality


def _build_expectations_entrenchment_history(
    level_history: list[tuple[datetime, float]],
    forward_history: list[tuple[datetime, float]],
    slope_history: list[tuple[datetime, float]],
    curvature_history: list[tuple[datetime, float]],
    survey_gap_history: list[tuple[datetime, float]],
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    if not all([level_history, forward_history, slope_history, curvature_history, survey_gap_history]):
        return []

    level_map = {timestamp.date(): value for timestamp, value in level_history}
    forward_map = {timestamp.date(): value for timestamp, value in forward_history}
    slope_map = {timestamp.date(): value for timestamp, value in slope_history}
    curvature_map = {timestamp.date(): value for timestamp, value in curvature_history}
    survey_gap_map = {timestamp.date(): value for timestamp, value in survey_gap_history}

    history: list[tuple[datetime, float]] = []
    current = start
    while current <= end:
        if current in level_map and current in forward_map and current in slope_map and current in curvature_map and current in survey_gap_map:
            level_component = max(0.0, min(100.0, ((level_map[current] - 2.2) / 1.2) * 100.0))
            forward_component = max(0.0, min(100.0, ((forward_map[current] - 2.3) / 1.1) * 100.0))
            slope_component = max(0.0, min(100.0, slope_map[current] / 1.2))
            curvature_component = max(0.0, min(100.0, curvature_map[current] / 0.7))
            survey_gap_component = max(0.0, min(100.0, survey_gap_map[current] / 1.1))
            score = (
                0.28 * level_component
                + 0.24 * forward_component
                + 0.18 * slope_component
                + 0.12 * curvature_component
                + 0.18 * survey_gap_component
            )
            history.append((_timestamp_for_day(current), round(score, 6)))
        current += timedelta(days=1)
    return history


def _build_synthetic_usd_funding_pressure_history(
    eurusd_history: list[tuple[datetime, float]],
    usdjpy_history: list[tuple[datetime, float]],
    sofr_history: list[tuple[datetime, float]],
    ecb_history: list[tuple[datetime, float]],
    jpy_rate_history: list[tuple[datetime, float]],
    start: date,
    end: date,
    *,
    lookback: int = 20,
) -> list[tuple[datetime, float]]:
    if not all([eurusd_history, usdjpy_history, sofr_history, ecb_history, jpy_rate_history]):
        return []
    eur_values = [float(value) for _, value in eurusd_history]
    jpy_values = [float(value) for _, value in usdjpy_history]
    sofr_values = [float(value) for _, value in sofr_history]
    ecb_values = [float(value) for _, value in ecb_history]
    jpy_rate_values = [float(value) for _, value in jpy_rate_history]
    timestamps = [timestamp for timestamp, _ in eurusd_history]
    history: list[tuple[datetime, float]] = []
    for index in range(len(timestamps)):
        if index < lookback:
            continue
        eurusd_now = eur_values[index]
        eurusd_then = eur_values[index - lookback]
        usdjpy_now = jpy_values[index]
        usdjpy_then = jpy_values[index - lookback]
        if eurusd_then == 0 or usdjpy_then == 0:
            continue
        eurusd_change_pct = ((eurusd_now / eurusd_then) - 1.0) * 100.0
        usdjpy_change_pct = ((usdjpy_now / usdjpy_then) - 1.0) * 100.0
        usd_eur_diff_bps = (sofr_values[index] - ecb_values[index]) * 100.0
        usd_jpy_diff_bps = (sofr_values[index] - jpy_rate_values[index]) * 100.0
        eur_component = max(0.0, -eurusd_change_pct * 10.0)
        jpy_component = max(0.0, usdjpy_change_pct * 3.5)
        eur_rate_component = max(0.0, (usd_eur_diff_bps - 125.0) / 6.0)
        jpy_rate_component = max(0.0, (usd_jpy_diff_bps - 250.0) / 10.0)
        score = min(100.0, max(0.0, 0.30 * eur_component + 0.25 * jpy_component + 0.20 * eur_rate_component + 0.25 * jpy_rate_component))
        history.append((timestamps[index], round(score, 6)))
    return [item for item in history if start <= item[0].date() <= end]


def _build_local_currency_oil_stress_history(
    oil_history: list[tuple[datetime, float]],
    fx_history: list[tuple[datetime, float]],
    start: date,
    end: date,
    *,
    mode: str,
    window: int = 60,
) -> list[tuple[datetime, float]]:
    if not oil_history or not fx_history:
        return []
    oil_map = {timestamp.date(): float(value) for timestamp, value in oil_history}
    fx_map = {timestamp.date(): float(value) for timestamp, value in fx_history}
    common_days = sorted(set(oil_map) & set(fx_map))
    if not common_days:
        return []

    local_costs: list[float] = []
    values: list[tuple[datetime, float]] = []
    for day in common_days:
        oil_value = oil_map[day]
        fx_value = fx_map[day]
        if fx_value <= 0:
            continue
        local_cost = oil_value * fx_value if mode == 'multiply' else oil_value / fx_value
        local_costs.append(local_cost)
        sample = local_costs[max(0, len(local_costs) - window):]
        stress = _percentile_rank(sample, local_cost)
        values.append((_timestamp_for_day(day), round(stress, 6)))
    return _forward_fill_history(values, start, end)


def _build_threshold_stress_history(
    history: list[tuple[datetime, float]],
    *,
    warning: float,
    critical: float,
    direction: str,
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    if not history:
        return []
    values: list[tuple[datetime, float]] = []
    for timestamp, raw_value in history:
        value = float(raw_value)
        if direction == 'high':
            span = critical - warning if critical != warning else 1.0
            stress = 50.0 + ((value - warning) / span) * 50.0
        else:
            span = warning - critical if critical != warning else 1.0
            stress = 50.0 + ((warning - value) / span) * 50.0
        values.append((timestamp, round(max(0.0, min(100.0, stress)), 6)))
    return _forward_fill_history(values, start, end)


def _build_weighted_composite_history(
    weighted_histories: list[tuple[list[tuple[datetime, float]], float]],
    start: date,
    end: date,
) -> list[tuple[datetime, float]]:
    usable = [(history, weight) for history, weight in weighted_histories if history and weight > 0]
    if not usable:
        return []
    maps = [({timestamp.date(): float(value) for timestamp, value in history}, weight) for history, weight in usable]
    common_days = set.intersection(*(set(history_map) for history_map, _ in maps))
    if not common_days:
        return []
    values: list[tuple[datetime, float]] = []
    for day in sorted(common_days):
        numerator = 0.0
        denominator = 0.0
        for history_map, weight in maps:
            numerator += history_map[day] * weight
            denominator += weight
        values.append((_timestamp_for_day(day), round(numerator / denominator, 6)))
    return _forward_fill_history(values, start, end)


def _build_debt_trend_stress_history(
    observations: list[tuple[date, float]],
    start: date,
    end: date,
    *,
    lag: int = 252,
) -> list[tuple[datetime, float]]:
    ordered = sorted(observations, key=lambda item: item[0])
    if len(ordered) <= lag:
        return []
    derived: list[tuple[date, float]] = []
    for index in range(lag, len(ordered)):
        current_day, current_value = ordered[index]
        prior_value = ordered[index - lag][1]
        if prior_value <= 0:
            continue
        yoy_growth = ((float(current_value) / float(prior_value)) - 1.0) * 100.0
        stress = max(0.0, min(100.0, yoy_growth * 15.0))
        derived.append((current_day, round(stress, 6)))
    return _densify_daily(derived, start, end)


def _sample_stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _safe_float(value: object) -> float | None:
    if value in {None, '', 'null', 'None'}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_term_years(term: str | None) -> int | None:
    if not term:
        return None
    match = re.search(r'(\d+)', term)
    return int(match.group(1)) if match else None


def _percentile_rank(values: list[float], current: float, *, inverse: bool = False) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return 50.0
    ordered = sorted(values)
    less = sum(1 for item in ordered if item < current)
    equal = sum(1 for item in ordered if item == current)
    rank = (less + 0.5 * equal) / len(ordered)
    percentile = rank * 100.0
    return 100.0 - percentile if inverse else percentile


def _compute_auction_stress_histories(rows: list[dict[str, str]], start: date, end: date) -> dict[str, list[tuple[datetime, float]]]:
    auctions: list[dict[str, float | str | date]] = []
    for row in rows:
        auction_date_raw = row.get('auction_date')
        if not auction_date_raw:
            continue
        auction_day = date.fromisoformat(auction_date_raw)
        if auction_day > end:
            continue

        security_type = row.get('security_type') or ''
        term_years = _parse_term_years(row.get('security_term'))
        bid_to_cover = _safe_float(row.get('bid_to_cover_ratio'))
        high_yield = _safe_float(row.get('high_yield'))

        offering_amt = _safe_float(row.get('offering_amt')) or _safe_float(row.get('currently_outstanding'))
        indirect_accepted = _safe_float(row.get('indirect_bidder_accepted'))
        direct_accepted = _safe_float(row.get('direct_bidder_accepted'))
        dealer_accepted = _safe_float(row.get('primary_dealer_accepted'))
        allotment_total = sum(
            amount
            for amount in [indirect_accepted, direct_accepted, dealer_accepted]
            if amount is not None and amount > 0
        )
        share_denominator = allotment_total or offering_amt
        indirect_share = None
        direct_share = None
        dealer_share = None
        if share_denominator and share_denominator > 0 and indirect_accepted is not None:
            indirect_share = indirect_accepted / share_denominator
        if share_denominator and share_denominator > 0 and direct_accepted is not None:
            direct_share = direct_accepted / share_denominator
        if share_denominator and share_denominator > 0 and dealer_accepted is not None:
            dealer_share = dealer_accepted / share_denominator

        auctions.append(
            {
                'auction_date': auction_day,
                'security_type': security_type,
                'term_years': float(term_years) if term_years is not None else 0.0,
                'offering_amt': float(offering_amt) if offering_amt is not None else 0.0,
                'bid_to_cover': bid_to_cover,
                'high_yield': high_yield if high_yield is not None else 0.0,
                'indirect_share': indirect_share if indirect_share is not None else 0.0,
                'direct_share': direct_share if direct_share is not None else 0.0,
                'dealer_share': dealer_share if dealer_share is not None else 0.0,
            }
        )

    if not auctions:
        return {}

    long_end_auctions = [
        item
        for item in auctions
        if str(item['security_type']) in {'Note', 'Bond'}
        and float(item['term_years']) >= 7.0
        and item['bid_to_cover'] is not None
    ]
    if not long_end_auctions:
        return {}

    long_end_auctions = sorted(long_end_auctions, key=lambda item: item['auction_date'])  # type: ignore[arg-type]

    clearing_points: list[tuple[date, float]] = []
    sponsorship_points: list[tuple[date, float]] = []
    btc_values: list[float] = []
    yield_values: list[float] = []
    indirect_values: list[float] = []
    dealer_values: list[float] = []
    for item in long_end_auctions:
        bid_to_cover = float(item['bid_to_cover'])
        high_yield = float(item['high_yield'])
        btc_values.append(bid_to_cover)
        yield_values.append(high_yield)

        btc_stress = _percentile_rank(btc_values, bid_to_cover, inverse=True)
        yield_stress = _percentile_rank(yield_values, high_yield)
        indirect_share = float(item['indirect_share'])
        dealer_share = float(item['dealer_share'])
        if indirect_share > 0:
            indirect_values.append(indirect_share)
            indirect_stress = _percentile_rank(indirect_values, indirect_share, inverse=True)
        else:
            indirect_stress = 50.0
        if dealer_share > 0:
            dealer_values.append(dealer_share)
            dealer_stress = _percentile_rank(dealer_values, dealer_share)
        else:
            dealer_stress = 50.0

        clearing_score = round(0.45 * btc_stress + 0.30 * yield_stress + 0.25 * dealer_stress, 4)
        sponsorship_score = round(0.65 * indirect_stress + 0.35 * dealer_stress, 4)
        clearing_points.append((item['auction_date'], clearing_score))
        sponsorship_points.append((item['auction_date'], sponsorship_score))

    issuance_points: list[tuple[date, float]] = []
    issuance_gaps: list[float] = []
    ordered_auctions = sorted(auctions, key=lambda item: item['auction_date'])  # type: ignore[arg-type]
    for item in ordered_auctions:
        auction_day = item['auction_date']
        if not isinstance(auction_day, date):
            continue
        window_start = auction_day - timedelta(days=90)
        window_items = [
            candidate
            for candidate in ordered_auctions
            if isinstance(candidate['auction_date'], date)
            and window_start <= candidate['auction_date'] <= auction_day
        ]
        total_amt = sum(max(float(candidate['offering_amt']), 0.0) for candidate in window_items)
        if total_amt <= 0:
            continue
        front_end_amt = 0.0
        long_end_amt = 0.0
        for candidate in window_items:
            security_type = str(candidate['security_type'])
            term_years = float(candidate['term_years'])
            offering_amt = max(float(candidate['offering_amt']), 0.0)
            if security_type == 'Bill' or security_type == 'CMB' or security_type == 'FRN' or (security_type == 'Note' and term_years < 7.0):
                front_end_amt += offering_amt
            elif security_type in {'Note', 'Bond'} and term_years >= 7.0:
                long_end_amt += offering_amt
        front_end_share = front_end_amt / total_amt
        long_end_share = long_end_amt / total_amt if total_amt > 0 else 0.0
        issuance_gap = front_end_share - long_end_share
        issuance_gaps.append(issuance_gap)
        issuance_stress = _percentile_rank(issuance_gaps, issuance_gap)
        issuance_points.append((auction_day, round(issuance_stress, 4)))

    clearing_history = _densify_daily(clearing_points, start, end)
    sponsorship_history = _densify_daily(sponsorship_points, start, end)
    issuance_history = _densify_daily(issuance_points, start, end)
    composite_history = _build_weighted_composite_history(
        [
            (clearing_history, 0.50),
            (sponsorship_history, 0.30),
            (issuance_history, 0.20),
        ],
        start,
        end,
    )

    return {
        'auction_stress': composite_history,
        'auction_clearing_stress': clearing_history,
        'auction_foreign_sponsorship_stress': sponsorship_history,
        'auction_issuance_mix_stress': issuance_history,
    }


def _compute_auction_stress_history(rows: list[dict[str, str]], start: date, end: date) -> list[tuple[datetime, float]]:
    histories = _compute_auction_stress_histories(rows, start, end)
    return histories.get('auction_stress', [])




