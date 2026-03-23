# Advanced User Guide

## Purpose

This dashboard is designed to be used as an advanced indicator of monetary and market-plumbing stress rather than as a generic macro monitor. The core question is whether a shipping and energy shock is staying in the inflation lane, migrating into dollar funding stress, or forcing the system toward Treasury dysfunction and policy backstops.

The working chain is:

`marine war-risk / shipping disruption -> oil supply shock -> higher energy import bills -> global dollar funding stress -> weaker foreign marginal UST demand -> repo stress / Treasury basis unwind -> Treasury market dysfunction -> Fed backstop -> inflation / repression risk`

In practice, the app helps answer three questions:

1. Is the oil shock still mostly a price-level problem?
2. Is it migrating into dollar funding and sovereign-duration stress?
3. Has it become a Treasury-plumbing problem with policy-backstop implications?

## How To Read The App

Use the app from top to bottom in this order:

1. Start with the three regime cards and identify which regime has the highest score.
2. Check the 7-day and 30-day changes on those cards. The change often matters more than the level.
3. Scan the fast-moving stress panel. If three or more signals are warning or critical, the app flags systemic synchronization.
4. Check the causal chain. This tells you where the stress is concentrated: physical oil, offshore funding, UST demand, repo/basis, or Fed intervention.
5. Use the detailed panels to verify whether the move is broadening or narrowing.
6. Read the narrative block and alert engine last. Those summarize what the underlying metrics already showed.

The app is most useful when you treat it as a transmission monitor. One indicator turning red is less important than multiple linked indicators turning together in the order implied by the thesis.

## The Top Summary Layer

The top summary layer consists of four decision tools:

1. Sticky Inflation card
2. Convex Inflation / Funding Stress card
3. Break / Repression card
4. Intraday / Fast-Moving Stress Panel

### 1. Sticky Inflation

This card tracks a regime where oil and shipping stress are visible, but dollar funding and Treasury clearing are still functioning. A high Sticky score means inflation persistence is the main problem, not yet a full plumbing event.

Use it to answer: are inflation inputs rising without a full-blown market-structure break?

Typical contributors:

- Brent prompt spread
- tanker freight stress
- marine insurance stress
- oil price
- consumer credit stress
- inflation compensation

### 2. Convex Inflation / Funding Stress

This card tracks the phase where the physical shock starts migrating into offshore dollar funding, rates volatility, repo pressure, and weaker long-duration demand. This is the key transition regime in the app.

Use it to answer: is the oil shock becoming a nonlinear funding and duration problem?

Typical contributors:

- Brent backwardation
- tanker freight acceleration
- JPY and EUR dollar-basis stress
- SOFR stress
- rates volatility
- auction stress
- Treasury basis stress

### 3. Break / Repression

This card tracks the most dangerous regime: repeated weak auctions, persistent funding pressure, rising Fed backstop usage, deteriorating Treasury liquidity, and growing repression risk.

Use it to answer: is the market moving from stress into dysfunction?

Typical contributors:

- auction stress
- repo stress
- FIMA usage
- Fed swap line usage
- Treasury liquidity stress
- Treasury basis stress
- private credit and intervention overlays

### 4. Intraday / Fast-Moving Stress Panel

This is not a regime score. It is the system trigger panel. It watches the fastest-moving parts of the stress chain:

- Treasury liquidity / depth proxy
- SOFR versus target
- cash-futures Treasury basis proxy
- JPY dollar-basis proxy
- Brent prompt spread. A Brent prompt spread is the price difference between the most immediate (prompt) delivery date of Brent crude oil and a later date, reflecting market structure, such as backwardation (prompt higher than future) or contango (prompt lower than future). It indicates current physical supply/demand balance compared to future expectations.

The app raises a systemic stress alert when 3 or more of these signals are simultaneously in warning or critical territory.

This panel is the fastest way to tell whether the stress chain is synchronizing across physical oil, offshore dollar funding, and Treasury plumbing.

## Regime-Change Thresholds

There are two kinds of thresholds in the app.

### 1. Regime-card thresholds

The code identifies the current regime as the highest of the three regime scores. In other words, the formal regime change happens whenever one regime score overtakes the others.

For actual use, treat the scores with the following confidence bands:

- `0-44`: background signal only
- `45-59`: regime pressure is building, but not yet dominant
- `60-74`: active regime, should shape interpretation of the rest of the dashboard
- `75-100`: dominant regime, usually broad-based and actionable

Recommended interpretation:

- Sticky to Convex transition: Convex score rises above Sticky and moves through `60`
- Convex to Break transition: Break score rises above Convex and moves through `60`
- High-conviction break / repression warning: Break score above `75`, especially if the systemic stress panel is active

### 2. Indicator thresholds

Each indicator has a warning and critical threshold. The most important current defaults are:

- Brent M1-M2 spread: warning `> 2`, critical `> 4`
- WTI M1-M2 spread: warning `> 1.5`, critical `> 3`
- EUR/USD basis: warning `< -20`, critical `< -35`
- JPY/USD basis: warning `< -30`, critical `< -50`
- SOFR minus target midpoint: warning `> 25 bps`, critical `> 50 bps`
- MOVE: warning `> 125`, critical `> 150`
- Treasury liquidity proxy: warning `> 58`, critical `> 74`
- Treasury basis proxy: warning `> 55`, critical `> 72`
- Auction stress: warning `> 58`, critical `> 75`
- FIMA repo usage: warning `> 18`, critical `> 35`
- Fed swap line usage: warning `> 5`, critical `> 15`

## The 15 Core Metrics

The app tracks more than 15 series, but the 15 below are the core advanced-indicator set for monetary stress analysis.

### 1. Brent M1-M2 Spread

- App key: `brent_prompt_spread`
- Current source: `market/yahoo-bz-calendar`
- Unit: `USD/bbl`
- Why it is tracked: Brent prompt backwardation is the cleanest front-end signal that the oil shock is physical rather than rhetorical.
- What it contributes: it tells you whether the system is starting with genuine prompt scarcity. If Brent prompt tightness is rising while funding metrics are still calm, the regime is more likely Sticky than Convex.

### 2. WTI M1-M2 Spread

- App key: `wti_prompt_spread`
- Current source: `market/yahoo-cl-calendar`
- Unit: `USD/bbl`
- Why it is tracked: WTI confirms whether prompt crude tightness is broad or localized.
- What it contributes: it acts as a second physical-oil check. If Brent and WTI are both widening, the oil shock is more credible as a macro transmission source.

### 3. VLCC Freight Proxy

- App key: `tanker_freight_proxy`
- Current source: `fred/TSIFRGHT`
- Unit: `index`
- Why it is tracked: shipping costs are the bridge between maritime disruption and imported inflation.
- What it contributes: it measures whether the stress is transmitting through transport capacity rather than spot headlines alone.

### 4. LNG Stress Proxy

- App key: `lng_proxy`
- Current source: `fred/PNGASJPUSDM`
- Unit: `index`
- Why it is tracked: LNG stress broadens the energy story beyond crude.
- What it contributes: it helps determine whether the energy shock is becoming generalized across import-dependent energy markets.

### 5. EUR/USD Cross-Currency Basis

- App key: `eur_usd_basis`
- Current source: `proxy/fred-eur-basis`
- Unit: `bps`
- Why it is tracked: EUR basis stress is a direct clue that offshore borrowers are paying up for dollars.
- What it contributes: it shows when the shock is moving from commodity pricing into global funding conditions.

### 6. JPY/USD Cross-Currency Basis

- App key: `jpy_usd_basis`
- Current source: `proxy/fred-jpy-basis`
- Unit: `bps`
- Why it is tracked: JPY basis often reacts sharply when dollar scarcity becomes more acute.
- What it contributes: it is one of the fastest early signals that the system is moving from Sticky into Convex.

### 7. SOFR Minus Target Midpoint

- App key: `sofr_spread`
- Current source: `fred/SOFR-DFF`
- Unit: `bps`
- Why it is tracked: this is the basic domestic repo-plumbing pressure gauge.
- What it contributes: it tells you whether funding markets are still functioning cleanly or beginning to leak stress into the policy corridor.

### 8. MOVE Index / Rates Volatility Proxy

- App key: `move_index`
- Current source: `proxy/fred-rates-vol`
- Unit: `index`
- Why it is tracked: rates-volatility spikes are a direct symptom of duration-clearing stress.
- What it contributes: it separates ordinary yield drift from disorderly Treasury repricing.

### 9. Treasury Liquidity Proxy

- App key: `treasury_liquidity_proxy`
- Current source: `market/yahoo-zn-depth`
- Unit: `index`
- Why it is tracked: deteriorating Treasury depth is the market-structure expression of dealer balance-sheet strain and reduced willingness to warehouse duration.
- What it contributes: it helps identify when the stress chain has moved beyond inflation and funding into Treasury functionality itself.

### 10. Treasury Basis Stress Proxy

- App key: `treasury_basis_proxy`
- Current source: `market/yahoo-zn-basis`
- Unit: `index`
- Why it is tracked: the cash-futures basis is where leveraged duration trades can become unstable.
- What it contributes: it flags the point where repo stress, futures pricing, and cash Treasury positioning begin reinforcing each other.

### 11. UST Auction Stress

- App key: `auction_stress`
- Current source: `treasury/auctions_query`
- Unit: `index`
- Why it is tracked: repeated weak auctions are direct evidence that marginal demand for duration is softening.
- What it contributes: it is one of the clearest bridges from funding stress into sovereign-clearing stress.

### 12. FIMA Repo Usage

- App key: `fima_repo_usage`
- Current source: `fred/SWPT`
- Unit: `USD bn`
- Why it is tracked: FIMA usage shows foreign official institutions drawing dollars against Treasuries.
- What it contributes: it indicates that foreign holders are needing plumbing support rather than simply absorbing duration quietly.

### 13. Fed Swap Line Usage

- App key: `fed_swap_line_usage`
- Current source: `fred/WLCFLL`
- Unit: `USD bn`
- Why it is tracked: swap-line use is the cleanest public sign that offshore dollar pressure is leaning on central-bank backstops.
- What it contributes: it is a key marker that the system is moving from Convex toward Break / Repression.

### 14. 10Y Treasury Yield

- App key: `ten_year_yield`
- Current source: `fred/DGS10`
- Unit: `%`
- Why it is tracked: the 10-year yield is the benchmark duration clearing price.
- What it contributes: it provides the anchor for reading whether the stress is showing up as higher term compensation, inflation premium, or duration indigestion.

### 15. 30Y Treasury Yield

- App key: `thirty_year_yield`
- Current source: `fred/DGS30`
- Unit: `%`
- Why it is tracked: long-end yields are where fiscal credibility, inflation premium, and balance-sheet stress become most visible.
- What it contributes: the 30-year often reacts more violently than the 10-year when the market starts worrying about repression, duration saturation, or weak long-bond demand.

## How The 15 Metrics Work Together

These metrics should not be read in isolation. The app is built to reward ordered confirmation.

### Sticky pattern

A typical Sticky pattern looks like this:

- Brent and WTI prompt spreads widen
- freight and LNG proxies firm
- oil price rises
- inflation compensation rises
- SOFR remains quiet
- swap lines and FIMA remain low
- auction stress is contained

Interpretation: the system is still mainly absorbing the shock through prices, not through broken plumbing.

### Convex pattern

A typical Convex pattern looks like this:

- Brent and freight stay high
- JPY and EUR basis move more negative
- SOFR stress begins to rise
- MOVE / rates volatility rises
- auction stress deteriorates
- Treasury basis stress appears

Interpretation: the shock is moving from physical scarcity into funding fragility and duration stress.

### Break / Repression pattern

A typical Break pattern looks like this:

- repeated weak auctions
- elevated Treasury depth stress
- Treasury basis stress remains high
- FIMA and swap-line usage rise
- long-end yields remain elevated or disorderly
- intervention headlines become plausible or explicit

Interpretation: the system is no longer just pricing inflation. It is struggling to clear sovereign duration without policy support.

## Panel-By-Panel Workflow

### Executive Regime View

Use this first. It tells you which of the three regimes is currently dominant and whether the trend is accelerating over 7 and 30 days.

### Critical Panels Above The Fold

Use this second. It compresses the highest-signal market indicators into one scan and quickly shows whether the chain is synchronized.

### Intraday / Fast-Moving Stress Panel

Use this as the trigger board. If three or more of the five signals are simultaneously warning or critical, the system is moving from isolated stress into cross-market stress.

### Causal Chain

Use this to locate where the stress is concentrated:

- Marine insurance stress
- Oil physical stress
- Dollar funding stress
- UST demand stress
- Repo / basis stress
- Fed intervention stress
- Inflation / repression stress

### Oil / Shipping View

Use this to determine whether the shock is still fundamentally about transport and physical barrels.

### Dollar Funding / Plumbing View

Use this to determine whether offshore funding pressure is becoming the main transmission channel.

### UST / Funding View

Use this to determine whether duration clearing is deteriorating.

### Consumer / Fiscal / Credit View

Use this to check whether the shock is beginning to impair the domestic private sector and fiscal base.

### Asset Regime View

Use this to validate whether broader asset pricing is confirming the regime signaled by the plumbing metrics.

## Alerts

Alerts are useful, but they are secondary. Use them as confirmation, not as the first read.

Most important alert types:

- threshold breaches in core indicators
- basis plus repo combination alerts
- weak auction plus high-volatility alerts
- FIMA and swap-line acceleration alerts
- systemic stress monitor trigger

The best alerts are combination alerts, because they tell you the transmission chain is progressing rather than just fluctuating.

## Manual Inputs

The app includes manual overlays that matter when public data cannot capture the full event quickly enough:

- `marine_insurance_stress`
- `tanker_disruption_score`
- `private_credit_stress`
- `geopolitical_escalation_toggle`
- `central_bank_intervention_toggle`

Use manual overlays for event information that appears before it shows up cleanly in market time series. Do not use them to force a regime call you want to see.

## Data Sources Used By The App

The app currently combines direct public series, public-derived proxies, and manual overlays.

### Direct market or official public data

- Yahoo futures contract chains for Brent, WTI, and 10Y Treasury futures-derived metrics such as the direct prompt spreads, Treasury liquidity proxy, and Treasury basis proxy
- FRED series for yields, SOFR, inflation compensation, credit spreads, swap lines, FIMA usage, LNG, tanker-freight proxy, dollar index proxy, and credit deterioration inputs
- Treasury Fiscal Data API for auction stress

### Public-derived proxies

- EUR/USD basis proxy
- JPY/USD basis proxy
- MOVE / rates-volatility proxy
- Treasury basis stress proxy
- Treasury liquidity proxy

### Manual overlays

- marine insurance stress
- tanker disruption
- private credit markdown stress
- geopolitical escalation
- intervention headline toggle

## Known Limits

- Direct exchange-grade cross-currency basis data is not available in a clean free public feed, so the app uses transparent public proxies.
- The MOVE series is implemented as a public rates-volatility substitute, not a licensed index feed.
- Treasury depth and Treasury basis are derived from public futures and cash inputs rather than exchange order-book or CTD-level analytics, so they should be read as public-market stress measures rather than exact dealer microstructure measures.
- Manual overlays remain necessary for the parts of the thesis that move faster than public macro datasets.

## Practical Interpretation Rule

If you only use one rule when reading the app, use this one:

- high oil stress without funding stress means Sticky
- high oil stress plus worsening basis, SOFR, and volatility means Convex
- weak auctions plus poor Treasury depth plus rising official backstop usage means Break / Repression

That is the logic the dashboard is built to surface.


