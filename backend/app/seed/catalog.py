from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesDefinition:
    key: str
    name: str
    category: str
    source: str
    frequency: str
    unit: str
    description: str


SERIES_DEFINITIONS: list[SeriesDefinition] = [
    SeriesDefinition("brent_prompt_spread", "Brent M1-M6 Spread", "oil_shipping", "demo/eia_stub", "daily", "USD/bbl", "Brent M1-M6 backwardation as a medium-horizon proxy for physical oil scarcity expectations."),
    SeriesDefinition("wti_prompt_spread", "WTI M1-M6 Spread", "oil_shipping", "demo/eia_stub", "daily", "USD/bbl", "WTI M1-M6 backwardation as a secondary crude scarcity expectations signal."),
    SeriesDefinition("murban_wti_spread", "Murban-WTI Spread", "oil_shipping", "demo/eia_stub", "daily", "USD/bbl", "Direct Middle East versus U.S. crude spread using Murban and WTI front prices."),
    SeriesDefinition("oman_wti_spread", "Oman-WTI Spread", "oil_shipping", "demo/eia_stub", "daily", "USD/bbl", "Direct Oman versus U.S. crude spread using Oman marker and WTI front prices."),
    SeriesDefinition("gulf_crude_dislocation", "Gulf Crude Dislocation", "oil_shipping", "demo/eia_stub", "daily", "USD/bbl", "Composite dislocation level built from direct Murban-WTI and Oman-WTI spreads."),
    SeriesDefinition("tanker_freight_proxy", "VLCC Freight Proxy", "oil_shipping", "demo/shipping_stub", "daily", "index", "Dirty tanker freight proxy for shipping disruption."),
    SeriesDefinition("hormuz_tanker_transit_stress", "Hormuz Tanker Transit Stress", "oil_shipping", "demo/shipping_stub", "daily", "index", "PortWatch-derived stress from Strait of Hormuz tanker transit and tanker-capacity deterioration."),
    SeriesDefinition("lng_proxy", "LNG Stress Proxy", "oil_shipping", "demo/shipping_stub", "daily", "index", "Proxy for LNG-related physical stress."),
    SeriesDefinition("eur_usd_basis", "EUR/USD Cross-Currency Basis", "funding", "demo/funding_stub", "daily", "bps", "Offshore dollar funding stress for EUR borrowers."),
    SeriesDefinition("jpy_usd_basis", "JPY/USD Cross-Currency Basis", "funding", "demo/funding_stub", "daily", "bps", "Offshore dollar funding stress for JPY borrowers."),
    SeriesDefinition("synthetic_usd_funding_pressure", "Synthetic USD Funding Pressure", "funding", "demo/funding_stub", "daily", "index", "Composite of direct FX spot moves and short-rate differentials for broad dollar funding pressure."),
    SeriesDefinition("vix_index", "VIX Index", "funding", "demo/vol_stub", "daily", "index", "Equity volatility and risk-premium expansion signal used for financial tightening and receipts sensitivity."),
    SeriesDefinition("oil_in_yen_stress", "Oil In Yen Stress", "funding", "demo/funding_stub", "daily", "index", "Compound local-currency oil stress using Brent-style oil pricing and USD/JPY."),
    SeriesDefinition("oil_in_eur_stress", "Oil In EUR Stress", "funding", "demo/funding_stub", "daily", "index", "Compound local-currency oil stress using Brent-style oil pricing and EUR/USD."),
    SeriesDefinition("oil_in_cny_stress", "Oil In CNY Stress", "funding", "demo/funding_stub", "daily", "index", "Compound local-currency oil stress using Brent-style oil pricing and USD/CNY."),
    SeriesDefinition("external_importer_stress", "External Importer Stress", "funding", "demo/funding_stub", "daily", "index", "Weighted importer stress composite for Japan, Europe, and China energy-balance-sheet pressure."),
    SeriesDefinition("expected_inflation_5y5y", "5Y5Y Inflation Expectation", "expectations", "demo/fred_stub", "monthly", "%", "Medium-term forward expected inflation from the Cleveland Fed / FRED term structure."),
    SeriesDefinition("inflation_expectations_level", "Inflation Expectations Level", "expectations", "demo/fred_stub", "monthly", "%", "Weighted level of the expected-inflation curve across 1Y to 30Y maturities."),
    SeriesDefinition("inflation_expectations_slope", "Inflation Expectations Slope", "expectations", "demo/fred_stub", "monthly", "bps", "Short-end minus long-end expected inflation as a measure of front-loaded shock pricing."),
    SeriesDefinition("inflation_expectations_curvature", "Inflation Expectations Curvature", "expectations", "demo/fred_stub", "monthly", "bps", "Belly richness of the inflation-expectations curve, centered on the 5Y sector."),
    SeriesDefinition("survey_market_expectations_gap", "Survey-Market Expectations Gap", "expectations", "demo/fred_stub", "monthly", "bps", "Gap between Michigan 1Y inflation expectations and model-based 1Y expected inflation."),
    SeriesDefinition("expectations_entrenchment_score", "Expectations Entrenchment Score", "expectations", "demo/fred_stub", "monthly", "index", "Composite entrenchment score combining curve level, forward expectations, curvature, and survey-market disagreement."),
    SeriesDefinition("eur_usd_spot", "EUR/USD Spot", "funding", "demo/funding_stub", "daily", "USD per EUR", "Direct EUR/USD spot rate support input."),
    SeriesDefinition("usd_jpy_spot", "USD/JPY Spot", "funding", "demo/funding_stub", "daily", "JPY per USD", "Direct USD/JPY spot rate support input."),
    SeriesDefinition("usd_cny_spot", "USD/CNY Spot", "funding", "demo/funding_stub", "daily", "CNY per USD", "Direct USD/CNY spot rate support input."),
    SeriesDefinition("sofr_rate", "SOFR Rate", "funding", "demo/nyfed_stub", "daily", "%", "Secured Overnight Financing Rate as the USD short-rate anchor."),
    SeriesDefinition("ecb_deposit_rate", "ECB Deposit Facility Rate", "funding", "demo/funding_stub", "daily", "%", "Official ECB deposit facility rate as the EUR short-rate anchor."),
    SeriesDefinition("japan_short_rate", "Japan Short Rate", "funding", "demo/funding_stub", "daily", "%", "Public Japanese short-rate anchor for USD/JPY funding comparison."),
    SeriesDefinition("sofr_spread", "SOFR Minus Target Midpoint", "funding", "demo/nyfed_stub", "daily", "bps", "Repo funding stress proxied by SOFR relative to target midpoint."),
    SeriesDefinition("move_index", "MOVE Index", "funding", "demo/vol_stub", "daily", "index", "Treasury volatility proxy."),
    SeriesDefinition("treasury_liquidity_proxy", "Treasury Liquidity Proxy", "funding", "demo/market_depth_stub", "daily", "index", "Treasury market depth/liquidity stress proxy."),
    SeriesDefinition("treasury_basis_proxy", "Treasury Basis Stress Proxy", "funding", "demo/market_depth_stub", "daily", "index", "Cash-futures Treasury basis stress proxy."),
    SeriesDefinition("auction_stress", "UST Auction Stress", "ust_funding", "demo/treasury_stub", "daily", "index", "Composite of long-end clearing stress, foreign sponsorship stress, and front-end issuance mix stress."),
    SeriesDefinition("auction_clearing_stress", "UST Long-End Clearing Stress", "ust_funding", "demo/treasury_stub", "daily", "index", "Long-end auction clearing stress built from bid-to-cover weakness, elevated stop-out yields, and dealer absorption."),
    SeriesDefinition("auction_foreign_sponsorship_stress", "UST Foreign Sponsorship Stress", "ust_funding", "demo/treasury_stub", "daily", "index", "Weak foreign and indirect participation in long-end auctions, with higher dealer warehousing stress."),
    SeriesDefinition("auction_issuance_mix_stress", "UST Issuance Mix Stress", "ust_funding", "demo/treasury_stub", "daily", "index", "Stress from Treasury issuance shifting toward bills and shorter duration relative to long-end coupon supply."),
    SeriesDefinition("fima_repo_usage", "FIMA Repo Usage", "ust_funding", "demo/fed_stub", "daily", "USD bn", "Foreign official dollar demand against Treasuries."),
    SeriesDefinition("fed_swap_line_usage", "Fed Swap Line Usage", "ust_funding", "demo/fed_stub", "daily", "USD bn", "Offshore funding backstop usage."),
    SeriesDefinition("ten_year_yield", "10Y Treasury Yield", "ust_funding", "demo/fred_stub", "daily", "%", "10-year Treasury yield."),
    SeriesDefinition("thirty_year_yield", "30Y Treasury Yield", "ust_funding", "demo/fred_stub", "daily", "%", "30-year Treasury yield."),
    SeriesDefinition("term_premium_proxy", "Term Premium Proxy", "ust_funding", "demo/fred_stub", "daily", "bps", "Duration compensation proxy."),
    SeriesDefinition("consumer_credit_stress", "Consumer Credit Stress", "consumer_credit", "demo/consumer_stub", "daily", "index", "Composite of credit card and auto delinquency deterioration."),
    SeriesDefinition("payroll_momentum", "Payroll Momentum (3M Avg)", "employment", "demo/bls_stub", "monthly", "k jobs", "Three-month average monthly change in nonfarm payrolls as a proxy for labor demand and withholding-tax momentum."),
    SeriesDefinition("unemployment_rate", "Unemployment Rate", "employment", "demo/bls_stub", "monthly", "%", "Headline unemployment rate from the labor market."),
    SeriesDefinition("wage_stickiness", "Average Hourly Earnings YoY", "employment", "demo/bls_stub", "monthly", "%", "Year-over-year wage growth as a proxy for labor-cost persistence."),
    SeriesDefinition("hours_worked_momentum", "Average Weekly Hours 3M Change", "employment", "demo/bls_stub", "monthly", "hours", "Three-month change in average weekly hours as an early labor-demand signal."),
    SeriesDefinition("temp_help_stress", "Temporary Help Employment YoY", "employment", "demo/bls_stub", "monthly", "%", "Year-over-year change in temporary help employment as an early white-collar labor stress signal."),
    SeriesDefinition("employment_tax_base_proxy", "Employment Tax Base Proxy YoY", "employment", "demo/bls_stub", "monthly", "%", "Year-over-year growth in payrolls times wages times hours as a proxy for withholding and payroll-tax base momentum."),
    SeriesDefinition("household_real_income_squeeze", "Household Real Income Squeeze", "employment", "demo/bls_stub", "daily", "index", "Composite of energy and inflation pressure versus nominal labor support for U.S. household purchasing power."),
    SeriesDefinition("federal_receipts_quality", "Federal Receipts Quality", "consumer_credit", "demo/fiscal_stub", "daily", "index", "Proxy for withholding and receipts quality."),
    SeriesDefinition("deficit_trend", "Deficit Trend", "consumer_credit", "demo/fiscal_stub", "daily", "index", "Deficit and debt trend stress proxy."),
    SeriesDefinition("tax_receipts_market_stress", "Tax Receipts Market Stress", "consumer_credit", "demo/fiscal_stub", "daily", "index", "Composite of VIX, equity drawdown pressure, and receipts quality as a capital-gains-sensitive tax stress proxy."),
    SeriesDefinition("spx_equal_weight", "S&P 500 Equal Weight", "asset_regime", "demo/asset_stub", "daily", "index", "Equal-weight equity performance proxy."),
    SeriesDefinition("tips_vs_nominals", "TIPS Versus Nominals", "asset_regime", "demo/asset_stub", "daily", "bps", "Breakeven inflation style spread."),
    SeriesDefinition("gold_price", "Gold Price", "asset_regime", "demo/asset_stub", "daily", "USD/oz", "Gold price as repression hedge."),
    SeriesDefinition("oil_price", "Oil Price", "asset_regime", "demo/asset_stub", "daily", "USD/bbl", "Front-month oil proxy."),
    SeriesDefinition("credit_spreads", "Credit Spreads", "asset_regime", "demo/asset_stub", "daily", "bps", "Corporate spread proxy."),
    SeriesDefinition("usd_index_proxy", "USD Index Proxy", "asset_regime", "demo/asset_stub", "daily", "index", "Broad dollar proxy."),
]

MANUAL_INPUT_DEFAULTS: dict[str, float] = {
    "marine_insurance_stress": 58.0,
    "tanker_disruption_score": 52.0,
    "private_credit_stress": 46.0,
    "geopolitical_escalation_toggle": 1.0,
    "central_bank_intervention_toggle": 0.0,
    "p_and_i_circular_stress": 40.0,
    "iaea_nuclear_ambiguity": 35.0,
    "interceptor_depletion": 30.0,
    "governance_fragmentation": 28.0,
}

