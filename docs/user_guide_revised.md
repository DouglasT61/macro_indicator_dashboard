# Advanced User Guide

## Purpose

The Macro Stress Dashboard is built around a specific macro thesis:

`marine war-risk / shipping disruption -> oil supply shock -> higher energy import bills -> global dollar funding stress -> weaker foreign marginal UST demand -> repo stress / Treasury basis unwind -> Treasury market dysfunction -> Fed plumbing backstop -> higher medium-term inflation / repression risk`

This is not a generic macro monitor. The app is designed to answer one question: **where is the stress chain today, how fast is it migrating, and how likely is it to move from a real-economy oil shock into financial repression risk?**

The app does that in five layers:

1. A **rule-based regime engine** converts the live indicator set into Sticky, Convex, and Break/Repression scores on a common `0-100` scale.
2. A **recursive propagation layer** models second-round feedback loops across the causal chain, so stress in one node can amplify downstream nodes and then feed back into the regime cards.
3. An **econometric state-space layer** estimates latent states such as oil shock, funding stress, Treasury stress, intervention pressure, and repression risk from the observed indicators.
4. A **historical analog / clustering layer** compares the current profile to past episodes, assigns the closest stress subfamily, and conditions calibration on that family.
5. A **forecast and adaptive alert layer** projects short-horizon regime probabilities, stress scenarios, and latent-state acceleration into live warning logic.

The result should be read as a structured decision-support system, not as a perfect market oracle. It is strongest at identifying **synchronization, acceleration, migration, and reinforcement of stress across domains**.

## Overall Thesis Review

The app assumes that a sustained maritime and insurance shock can begin as a physical supply constraint but become much more dangerous once it interacts with global dollar funding, Treasury market plumbing, domestic labor conditions, and the fiscal-credit transmission channel.

The progression is interpreted as follows:

1. **Shipping, marine insurance, and chokepoint transit stress** raise the delivered cost and uncertainty of moving crude, LNG, and related cargo.
2. **Prompt oil curve stress and Hormuz tanker-flow deterioration** indicate whether the disruption is translating into real physical scarcity rather than just headlines.
3. **Higher energy bills and broader risk aversion** feed into offshore dollar demand and cross-currency funding pressure.
4. **Funding stress** raises the odds that foreign investors and leveraged intermediaries become less willing or less able to warehouse U.S. duration.
5. **Auction weakness, liquidity deterioration, and basis stress** indicate that the system is moving from a macro stress event into a market-structure event.
6. **Fed backstop usage and intervention signals** indicate that the public sector is being drawn into market functioning.
7. **Labor-market deterioration and tax-base erosion** show whether financial stress is broadening into weaker federal receipts and higher consumer-credit strain.
8. Once that happens while inflation-sensitive inputs remain elevated, the medium-term policy mix can shift toward **real-return suppression / repression risk** rather than a clean disinflationary resolution.

The app measures this progression explicitly rather than inferring it from one market alone.

## Funding Source Hierarchy

The funding section now uses a source hierarchy rather than treating every displayed number as equivalent.

1. **Direct live market or official source**
2. **Official supporting input**
3. **Synthetic composite built from direct inputs**
4. **Proxy**
5. **Demo fallback**

In the current build:

- `MOVE Index` is direct and live from TradingView.
- `SOFR Rate`, `SOFR Minus Target Midpoint`, and `Japan Short Rate` use official FRED inputs.
- `ECB Deposit Facility Rate` uses the official ECB key-rates page.
- `EUR/USD Spot` and `USD/JPY Spot` use direct Yahoo market endpoints.
- `Synthetic USD Funding Pressure` is built from those direct spot and short-rate inputs.
- `EUR/USD basis` and `JPY/USD basis` remain explicitly marked as proxies because no clean public direct basis feed is wired yet.

This means the funding area should now be read as a combination of direct support inputs plus two remaining proxy basis cards, not as a fully direct basis terminal.

## How To Read The App

### The Four Top-Level Summary Cards

The top of the dashboard should be read as four decision cards:

1. `Sticky Inflation`
2. `Convex Inflation / Funding Stress`
3. `Break / Repression`
4. `Fast-Moving Stress Panel`

### Sticky Inflation

This card measures whether the shock is still primarily physical, inflationary, and not yet fully destabilizing market plumbing.

Interpretation:

- `0-44`: background or localized inflation pressure
- `45-59`: building sticky-inflation regime
- `60-74`: active sticky regime
- `75-100`: dominant sticky regime

Typical contributors:

- Brent M1-M6
- WTI M1-M6
- tanker freight
- Hormuz tanker transit stress
- marine insurance stress
- oil price / inflation compensation
- wage stickiness

### Convex Inflation / Funding Stress

This is the key transition regime. It marks the point where a physical shock is no longer just an inflation problem and is becoming a nonlinear funding and sovereign-duration problem.

Interpretation:

- `0-44`: no meaningful migration into funding yet
- `45-59`: transition forming
- `60-74`: active convex regime
- `75-100`: dominant nonlinear funding-stress regime

Typical contributors:

- JPY and EUR cross-currency basis stress
- SOFR versus target
- MOVE / rates-volatility stress
- auction deterioration
- Treasury basis stress
- private credit deterioration
- payroll slowdown
- temporary-help deterioration

### Break / Repression

This card measures whether the system is moving from stress into dysfunction, intervention dependence, weaker domestic credit quality, and medium-term repression risk.

Interpretation:

- `0-44`: break risk low
- `45-59`: dysfunction risk building
- `60-74`: active break-risk regime
- `75-100`: dominant dysfunction / repression regime

Typical contributors:

- persistent auction stress
- Treasury liquidity deterioration
- Treasury basis stress
- FIMA repo usage
- Fed swap-line usage
- intervention overlays
- unemployment deterioration
- tax-base erosion

### Fast-Moving Stress Panel

This is a simultaneity trigger, not a regime card. It watches five fast indicators:

- Treasury liquidity / depth proxy
- SOFR versus target
- Treasury basis proxy
- JPY/USD basis
- Brent M1-M6

Interpretation:

- `0-2` stressed signals: contained
- `3` stressed signals: warning
- `4-5` stressed signals: critical

Each card is color-coded:

- `green`: normal
- `yellow`: early caution
- `orange`: warning
- `red`: critical

## The Causal Chain

The causal chain panel is the structural core of the app. It groups the indicators into seven nodes:

1. `Marine insurance stress`
2. `Oil physical stress`
3. `Dollar funding stress`
4. `UST demand stress`
5. `Repo / basis stress`
6. `Fed intervention stress`
7. `Inflation / repression stress`

Each node displays:

- `base score`: the direct average stress of the indicators in that node
- `propagated score`: the post-feedback score after recursive transmission
- `loop pressure`: the incoming pressure from upstream nodes

That split matters. It shows whether a node is stressed because its own indicators are high, or because the rest of the system is forcing stress into it.

The inflation / repression node now includes labor and domestic-transmission metrics. That is deliberate. The app treats employment deterioration as a downstream amplifier of the same macro chain, because weaker payrolls reduce federal withholding and raise household-credit stress at the same time.

On the shipping side, the oil physical node now also uses PortWatch-based Strait of Hormuz tanker transit stress. That gives the dashboard a direct chokepoint-flow signal instead of relying only on oil prices, freight, or article-derived shipping overlays.

The oil block now also includes direct Gulf-versus-U.S. crude dislocation spreads. Murban-WTI and Oman-WTI help distinguish a generalized oil rally from a specific Middle East export-basin dislocation. When those spreads widen at the same time as Hormuz transit stress, freight stress, and insurance stress, the app treats that as stronger evidence that the shock is becoming physically regional and harder to absorb through normal arbitrage.

## Core System Metrics

The app tracks more than 20 total series across the detailed panels, but the main system engine is centered on the 15 metrics below. These are the metrics most directly used to monitor progression from physical disruption to repression risk.

### 1. Brent M1-M6 Spread

- **What it measures:** medium-horizon Brent backwardation, used as the primary physical scarcity signal.
- **Why it matters:** if front-to-sixth-month backwardation is wide and persistent, the oil shock is physical rather than merely rhetorical.
- **Progression role:** early physical node; helps determine whether the chain is genuinely starting.
- **Current source:** Yahoo futures contract chain via the backend market collector, labeled `market/yahoo-bz-calendar` when live. Demo fallback exists.
- **Source cadence:** market data is available daily from the public chart endpoint; the app refreshes daily at `06:00 UTC` by scheduler and on manual refresh.
- **App use:** heavily weighted in Sticky and Convex, and also in the practical interpretation rule.

### 2. WTI M1-M6 Spread

- **What it measures:** medium-horizon WTI backwardation.
- **Why it matters:** confirms whether physical stress is broad across crude benchmarks rather than isolated to one contract complex.
- **Progression role:** supporting physical node confirmation.
- **Current source:** Yahoo futures contract chain via `market/yahoo-cl-calendar`, with demo fallback.
- **Source cadence:** daily market observations; refreshed daily and manually.
- **App use:** supports oil physical stress and broadens the physical-scarcity read.

### Regional Gulf-U.S. Crude Dislocation

- **What it measures:** direct Murban-WTI and Oman-WTI regional crude spreads, plus a composite Gulf crude dislocation signal built from those two spreads.
- **Why it matters:** these spreads indicate whether Middle East export barrels are richening versus U.S. crude, which is often a cleaner sign of basin-level dislocation than looking at outright oil prices alone.
- **Progression role:** confirms whether shipping, insurance, and chokepoint stress are translating into real cross-basin crude market dislocation.
- **Current source:** Murban uses the TradingView Murban continuous contract page and Oman uses GME's official OQD marker page, both measured versus direct WTI front prices from Yahoo; labels are `spread/tradingview-murban-vs-yahoo-wti`, `spread/gme-oman-vs-yahoo-wti`, and `spread/direct-gulf-crude-dislocation` when live.
- **Source cadence:** refreshed daily and on manual refresh. Murban and Oman are currently direct live current-value sources, so history builds over repeated refreshes rather than arriving with a fully backfilled public history set.
- **App use:** included in Oil / Shipping View, the oil physical causal node, Sticky and Convex regime logic, and shipping/energy observation conditioning.

### 3. Tanker Freight Proxy

- **What it measures:** a public dirty-tanker freight proxy.
- **Why it matters:** freight cost pressure is one of the cleanest signs that routing and insurance stress are affecting real transport economics.
- **Progression role:** bridges marine disruption into delivered energy inflation.
- **Current source:** FRED series `TSIFRGHT`, transformed into an index-like stress measure; source label `fred/TSIFRGHT` when live.
- **Source cadence:** depends on FRED publication cadence of the underlying series; the app refreshes daily but the underlying series may lag publication.
- **App use:** weighted in Sticky and Convex; also boosted under shipping/energy observation conditioning.

### Hormuz Tanker Transit Stress

- **What it measures:** a PortWatch-derived stress score based on deterioration in Strait of Hormuz tanker calls, tanker capacity, and tanker share of total transits.
- **Why it matters:** it is a direct physical-flow confirmation signal for one of the world?s most important oil chokepoints.
- **Progression role:** confirms whether the shipping shock is impairing actual tanker movement rather than only affecting prices or narrative overlays.
- **Current source:** PortWatch IMF/Oxford chokepoint dataset via ArcGIS query endpoint; source label `portwatch/hormuz-transits` when live, with demo fallback if the endpoint is unavailable.
- **Source cadence:** daily source updates when PortWatch publishes new chokepoint rows; the app refreshes daily and on manual refresh.
- **App use:** included in Oil / Shipping View, the oil physical causal node, Sticky and Convex regime logic, and shipping/energy observation weighting.

### 4. Marine Insurance Stress

- **What it measures:** an article-derived overlay of war-risk and marine-insurance stress.
- **Why it matters:** marine insurance is often where geopolitical shipping stress first becomes explicit in price and capacity language.
- **Progression role:** earliest discretionary / text-derived shipping-risk node.
- **Current source:** Beinsure site scan across relevant marine and war-risk articles; source label `beinsure/site_scan`.
- **Source cadence:** the source site updates irregularly; the app rescans on daily refresh and on manual refresh.
- **App use:** weighted materially in Sticky and used as an observation-weighting booster when the environment is shipping- or energy-led.

### 5. JPY/USD Cross-Currency Basis

- **What it measures:** proxy for offshore dollar scarcity in JPY funding markets.
- **Why it matters:** JPY basis is often one of the clearest early public signals that dollar funding conditions are tightening globally.
- **Progression role:** first major funding-stress transmission channel after the oil shock broadens.
- **Current source:** public FRED-based proxy, labeled `proxy/fred-jpy-basis`.
- **Source cadence:** refreshed daily, but dependent on the underlying daily public inputs.
- **App use:** heavily weighted in Convex; also included in alerts, crisis monitor, and forecast conditioning.
- **Interpretation note:** this card is still a proxy. The direct support inputs for the JPY funding story now sit beside it in the `FX Funding Support` panel.

### 6. EUR/USD Cross-Currency Basis

- **What it measures:** proxy for offshore dollar scarcity in EUR funding markets.
- **Why it matters:** confirms whether funding stress is regional or broad.
- **Progression role:** broadening confirmation of the funding node.
- **Current source:** public FRED-based proxy, labeled `proxy/fred-eur-basis`.
- **Source cadence:** refreshed daily with the same lag caveat as other public daily inputs.
- **App use:** secondary Convex indicator and funding-state observation input.
- **Interpretation note:** this card is still a proxy. Use the live ECB deposit rate, SOFR rate, and EUR/USD spot series to judge whether the proxy read is directionally supported.

### 7. SOFR Minus Target Midpoint

- **What it measures:** stress in U.S. short-dollar / repo plumbing, proxied as `SOFR - DFF` in basis points.
- **Why it matters:** indicates whether funding strain is bleeding into domestic plumbing rather than remaining offshore.
- **Progression role:** core funding-to-plumbing transition metric.
- **Current source:** FRED series `SOFR` and `DFF`, combined as `fred/SOFR-DFF`.
- **Source cadence:** daily; refreshed daily and manually.
- **App use:** included in all three regime layers and in simultaneity alerts.

### 8. MOVE Index

- **What it measures:** the live ICE BofA MOVE market level.
- **Why it matters:** rising rates volatility reduces balance-sheet tolerance for duration risk and basis carry.
- **Progression role:** confirms that the funding shock is becoming nonlinear.
- **Current source:** TradingView live market page, labeled `market/tradingview-move` when the direct fetch succeeds. FYIcenter is retained only as a tertiary historical backfill aid, not as the primary feed.
- **Source cadence:** market-derived and refreshed daily by the app, with manual refresh available.
- **App use:** strong Convex and Break input, and a key alert metric.

### 9. UST Auction Stress

- **What it measures:** a weighted composite of three Treasury-auction subcomponents derived from the Treasury Fiscal Data `auctions_query` dataset:
  - `UST Long-End Clearing Stress`
  - `UST Foreign Sponsorship Stress`
  - `UST Issuance Mix Stress`
- **Component weights:** `50%` long-end clearing, `30%` foreign sponsorship, `20%` issuance mix.
- **Why it matters:** a system can tolerate funding stress for a while, but repeated weak auctions, weaker foreign sponsorship, and a shift in issuance toward the front end together indicate weakening sovereign duration clearing.
- **Progression role:** UST demand node.
- **Current source:** Treasury Fiscal Data `auctions_query` API, labeled `treasury/auctions_query`.
- **Source cadence:** event-driven around auction publication; the app refreshes daily, but the series only changes when new qualifying auction information changes one of the subcomponents.
- **App use:** major Convex and Break input, plus direct alert trigger.

#### UST Auction Subcomponents

- **UST Long-End Clearing Stress**
  - built from long-end (`7Y+`) note and bond auction deterioration
  - combines weak bid-to-cover, elevated stop-out yield stress, and higher dealer absorption
  - this is the closest internal measure to classical auction-clearing stress

- **UST Foreign Sponsorship Stress**
  - built from weaker indirect participation and heavier dealer warehousing in long-end auctions
  - intended to capture weakening foreign and reserve-manager style sponsorship of Treasury duration

- **UST Issuance Mix Stress**
  - built from the rolling 90-day share of issuance shifting toward bills and shorter duration relative to long-end coupons
  - this is a debt-management stress signal rather than a clearing signal
  - it is useful when Treasury appears to be relying more heavily on the front end of the curve

#### How To Read The UST Auction Card

The `UST Auction Stress` tile is intentionally **event-native**, not a market-style sparkline card.

It now shows:

- `Window`
  - the historical window required to display meaningful step changes
  - currently this may expand to `2y` if `1y` shows no distinct changes
- `Last step`
  - the date of the last score change
- `Stressed events (3m)`
  - the number of step changes in the last 3 months at or above the warning threshold
  - if there were none, the card displays `none`
- `Stressed events (6m)`
  - the same count over the last 6 months
  - if there were none, the card displays `none`
- `Last recorded step changes`
  - the most recent score transitions, shown with full dates including year

Important: a current `critical` state can coexist with `none` for recent stressed events. That means the score remains elevated from prior auction deterioration, but there have been no **new** stressed auction step changes in the recent 3-month or 6-month window.

### 10. Treasury Liquidity Proxy

- **What it measures:** public futures-derived Treasury market depth / liquidity stress.
- **Why it matters:** weak liquidity is a hallmark of plumbing stress and a precondition for disorderly moves.
- **Progression role:** direct plumbing node.
- **Current source:** front Treasury futures (`ZN`) market-derived metric via Yahoo, labeled `market/yahoo-zn-depth`.
- **Source cadence:** daily market observations; refreshed daily and manually.
- **App use:** weighted in Break, included in crisis monitor, and used in state-space Treasury stress measurement.

### 11. Treasury Basis Stress Proxy

- **What it measures:** public cash-futures basis stress proxy for Treasury basis-trade pressure.
- **Why it matters:** when basis relationships destabilize, leveraged relative-value positions can become a feedback amplifier.
- **Progression role:** repo / basis node and direct recursive amplifier.
- **Current source:** Treasury futures plus cash-yield divergence via Yahoo + FRED inputs, labeled `market/yahoo-zn-basis`.
- **Source cadence:** daily with market/funding updates.
- **App use:** weighted in Convex and Break; also part of the systemic stress panel.

### 12. FIMA Repo Usage

- **What it measures:** foreign official demand for dollars against Treasuries.
- **Why it matters:** a rising pattern suggests global holders are pulling liquidity from Treasuries rather than adding marginal demand.
- **Progression role:** intervention and weak foreign marginal demand node.
- **Current source:** FRED `SWPT`, labeled `fred/SWPT`.
- **Source cadence:** publication-lagged relative to intraday markets; refreshed daily, but not a true intraday signal.
- **App use:** weighted especially in Break and in alert streak logic.

### 13. Fed Swap Line Usage

- **What it measures:** central-bank use of Federal Reserve dollar swap lines.
- **Why it matters:** one of the clearest signs that offshore dollar scarcity has migrated into official-sector backstop territory.
- **Progression role:** late funding/intervention node.
- **Current source:** FRED `WLCFLL`, transformed to USD billions and labeled `fred/WLCFLL`.
- **Source cadence:** publication-lagged official data; refreshed daily.
- **App use:** Break regime input and alert trigger.

### 14. Consumer Credit Stress

- **What it measures:** public consumer-credit deterioration index.
- **Why it matters:** indicates whether macro stress is broadening into households and domestic balance sheets rather than staying isolated to market plumbing.
- **Progression role:** downstream macro confirmation and repression-risk broadening input.
- **Current source:** FRED `DRCCLACBS`, transformed into an index-like measure, labeled `fred/DRCCLACBS`.
- **Source cadence:** slower than market data and subject to publication lag; refreshed daily but changes only when source updates.
- **App use:** Sticky input and panel-level confirmation signal.

### 15. Private Credit Stress

- **What it measures:** public market proxy basket for private-credit markdown stress.
- **Why it matters:** private-credit vehicles often reveal tighter funding and deteriorating risk appetite before private marks adjust cleanly.
- **Progression role:** late Convex / early Break cross-check.
- **Current source:** Yahoo market proxy basket using `BIZD`, `BKLN`, and `HYG`, labeled `market/yahoo-private-credit-proxy`.
- **Source cadence:** daily market data; refreshed daily and manually.
- **App use:** Convex regime input and discretionary credit-spillover monitor.

## Employment / Receipts / Household Credit Module

The employment module extends the macro chain into domestic transmission. Its job is to answer two questions:

1. Is labor-market weakness starting to reduce the federal withholding and payroll-tax base?
2. Is labor-market weakness starting to raise the probability of household and bank consumer-credit stress?

These metrics are slower than the market/plumbing layer, so they are not used as fast-crisis triggers. They are used to confirm whether the stress chain is broadening into fiscal and household-credit damage.

### Payroll Momentum (3M Avg)

- **What it measures:** three-month average monthly change in nonfarm payrolls.
- **Why it matters:** slowing payroll growth weakens labor-demand momentum and reduces the flow base for withholding-tax receipts.
- **Progression role:** domestic transmission from macro stress into fiscal capacity.
- **Current source:** derived from FRED `PAYEMS`; source label `fred/PAYEMS-3MAVG` when live, `demo/bls_stub` when falling back.
- **Source cadence:** monthly underlying data; app checks daily and refreshes when a new observation is available.
- **App use:** Convex and Break input, plus employment alert logic.

### Unemployment Rate

- **What it measures:** headline unemployment rate.
- **Why it matters:** rising unemployment is the clearest public sign that macro stress is leaking into households and the credit system.
- **Progression role:** downstream labor, household, and repression-risk amplifier.
- **Current source:** FRED `UNRATE`; source label `fred/UNRATE` when live, `demo/bls_stub` on fallback.
- **Source cadence:** monthly underlying data; refreshed daily by the app.
- **App use:** Break input, employment alert trigger, and state-space repression-risk measurement.

### Wage Stickiness

- **What it measures:** year-over-year average hourly earnings growth.
- **Why it matters:** persistent wage growth can keep inflation sticky even as financial conditions worsen, which is exactly the mix that raises repression risk.
- **Progression role:** bridge between labor resilience and sticky inflation.
- **Current source:** FRED `CES0500000003`; source label `fred/CES0500000003-YOY` when live, `demo/bls_stub` on fallback.
- **Source cadence:** monthly underlying data; refreshed daily by the app.
- **App use:** Sticky input and inflation / repression node support.

### Hours Worked Momentum

- **What it measures:** three-month change in average weekly hours.
- **Why it matters:** firms often cut hours before they cut payrolls, so this is an early labor-demand deterioration signal.
- **Progression role:** early domestic confirmation that labor conditions are weakening.
- **Current source:** FRED `AWHAETP`; source label `fred/AWHAETP-3MCHANGE` when live, `demo/bls_stub` on fallback.
- **Source cadence:** monthly underlying data; refreshed daily by the app.
- **App use:** Break input and labor-transmission context.

### Temporary Help Stress

- **What it measures:** year-over-year change in temporary-help employment.
- **Why it matters:** temp-help rolls over early in labor slowdowns and is often a good proxy for white-collar demand softening.
- **Progression role:** bridge from macro stress into domestic hiring hesitation and later credit weakness.
- **Current source:** FRED `TEMPHELPS`; source label `fred/TEMPHELPS-YOY` when live, `demo/bls_stub` on fallback.
- **Source cadence:** monthly underlying data; refreshed daily by the app.
- **App use:** Convex and Break input, white-collar stress proxy, and employment alert trigger.

### Employment Tax Base Proxy YoY

- **What it measures:** year-over-year growth of a payroll-tax-base proxy constructed from payrolls, wages, and hours.
- **Why it matters:** this is the direct bridge from labor conditions into federal receipts quality.
- **Progression role:** fiscal-capacity deterioration signal.
- **Current source:** derived from FRED `PAYEMS`, `CES0500000003`, and `AWHAETP`; source label `proxy/fred-payroll-tax-base` when live, `demo/bls_stub` on fallback.
- **Source cadence:** monthly underlying data; refreshed daily by the app.
- **App use:** Sticky and Break input, consumer/fiscal panel input, and labor alert trigger.

## Additional Supporting Overlays And Series

The app also uses supporting metrics outside the 15-core set, including:

- `tanker_disruption_score`: public EIA chokepoint scan plus optional AISHub refinement
- `hormuz_tanker_transit_stress`: PortWatch Strait of Hormuz tanker-call and tanker-capacity deterioration signal
  This is the main public chokepoint-flow confirmation series in the app.
- `murban_wti_spread`, `oman_wti_spread`, `gulf_crude_dislocation`: direct regional crude dislocation measures for Gulf export barrels versus WTI
  These are the main basin-dislocation confirmation series in the app.
- `geopolitical_escalation_toggle`: GDELT / Google News escalation scan
- `central_bank_intervention_toggle`: Federal Reserve RSS intervention scan
- `ten_year_yield`, `thirty_year_yield`, `term_premium_proxy`
- `tips_vs_nominals`, `gold_price`, `oil_price`, `credit_spreads`, `usd_index_proxy`
- `federal_receipts_quality`, `deficit_trend`

These supporting series broaden context, feed the state-space observation set, and help classify the active cluster or episode family.

The funding area now also includes a dedicated support block:

- `synthetic_usd_funding_pressure`
- `eur_usd_spot`
- `usd_jpy_spot`
- `sofr_rate`
- `ecb_deposit_rate`
- `japan_short_rate`

These are used to separate three questions:

1. Is the app observing direct spot-FX and short-rate information?
2. Do those direct inputs support a stronger broad-dollar funding read?
3. Are the remaining EUR and JPY basis proxies directionally consistent with those direct inputs?

### Synthetic USD Funding Pressure

- **What it measures:** a composite funding-pressure signal built from EUR/USD spot, USD/JPY spot, SOFR, the ECB deposit rate, and Japan short-rate inputs.
- **Why it matters:** until a clean public direct basis feed is wired, the app still needs a live, non-proxy way to assess whether broad dollar funding pressure is actually tightening.
- **Progression role:** bridge between direct FX / rates inputs and the broader dollar-funding node.
- **Current source:** synthetic composite labeled `synthetic/yahoo-ecb-fred-funding-pressure`.
- **Source cadence:** refreshed daily and on manual refresh, using the latest available direct source inputs.
- **App use:** included in the Dollar Funding / Plumbing panel, Convex and Break regime logic, the interpretation chart, and the state-space funding measurements.

### FX Funding Support Panel

The `FX Funding Support` panel exists so the basis cards are not read in isolation.

Use it as follows:

1. Check `EUR/USD Spot` and `USD/JPY Spot` for direct dollar strength or weakness.
2. Check `SOFR Rate`, `ECB Deposit Facility Rate`, and `Japan Short Rate` for the short-rate backdrop.
3. Check `Synthetic USD Funding Pressure` in the main funding panel.
4. Then decide whether the EUR and JPY basis proxies are corroborated or contradicted by the direct support inputs.

If the support panel and the basis cards point in the same direction, conviction in the funding read should rise. If they diverge, treat the basis signal more cautiously.

## Data Frequency And Update Logic

The app has two timing layers:

1. **Source cadence**: how often the outside source actually updates.
2. **App refresh cadence**: how often the app checks for new data.

### App Refresh Cadence

By default the backend scheduler is enabled and runs a full refresh **daily at `06:00 UTC`**. The same refresh logic also runs when you press the manual refresh control.

### Source Frequency By Type

- **Market-derived public endpoints** such as Yahoo chart data: effectively daily in this app, though the endpoint may publish more frequently than the app polls it.
- **TradingView market pages** such as the direct MOVE feed and Murban contract page: treated as daily market reads in the app and refreshed daily or on manual refresh.
- **FRED daily series**: refreshed daily but subject to the underlying publication delay.
- **FRED monthly labor series**: checked daily by the app but only change when the monthly release updates.
- **ECB key-rate pages**: checked daily by the app; the rate only changes when the ECB changes its official administered rates.
- **Official exchange data pages** such as GME's Oman marker page: checked daily by the app; public current-value access is direct but public historical backfill is limited.
- **Treasury auction data**: event-driven when auctions publish.
- **PortWatch chokepoint data**: daily chokepoint rows when the platform publishes new passage observations; checked daily and on manual refresh.
- **Text/news scans** such as Beinsure, Google News, and Fed RSS: checked daily and on manual refresh, but fundamentally irregular because they update when new articles or releases appear.
- **Manual overlays**: immediate when changed by the user.

The dashboard therefore mixes fast and slow signals intentionally. Fast market indicators are used for detection and simultaneity. Slower official or text-derived signals are used for confirmation, classification, and intervention context.

## How The App Accounts For Recursive Loops

The real system is recursive, so the app does not stop at simple weighted averages.

### Step 1: Direct Stress Measurement

Each observable metric is first normalized onto a comparable stress scale using configured warning and critical thresholds. That converts very different units, such as `USD/bbl`, `bps`, `%`, and toggles, into a common stress language.

### Step 2: Causal Grouping

Indicators are grouped into causal nodes such as oil physical stress, dollar funding stress, and Treasury market stress. The app computes a base node score as the average normalized stress inside that node.

### Step 3: Recursive Propagation

The recursive propagation engine then applies a directed graph with:

- `activation_floor`: minimum stress needed for one node to push another
- `memory`: persistence of the prior node score
- `feedback_gain`: direct transmission from upstream pressure
- `synergy_gain`: extra nonlinear amplification when both the node and the upstream source are stressed
- `iterations`: multiple rounds of propagation

Conceptually, the propagated node score is built from:

- direct node stress
- persistence of the prior propagated value
- incoming pressure from upstream nodes above the activation floor
- a synergy term when stressed nodes interact
- physical chokepoint confirmation from series such as Hormuz tanker transit stress when shipping routes start to deteriorate

This means, for example, that a stressed oil node can push funding stress higher, which can then push Treasury stress higher, which can then increase intervention pressure, while those downstream nodes can later feed back into the regime calculation.

### Step 4: Domestic Transmission Feedback

Employment, tax-base, and consumer-credit metrics sit later in the chain but matter because they create a domestic feedback loop:

- market stress weakens labor demand
- weaker labor demand reduces payroll and withholding momentum
- weaker labor conditions raise household-credit stress
- weaker tax receipts and weaker consumer credit raise fiscal and bank vulnerability
- that vulnerability increases the pressure to stabilize markets with easier or more repressive policy mixes

The app does not treat labor as an unrelated macro sidebar. It treats labor deterioration as a downstream recursion into the inflation / repression node.

### Step 5: Regime-Level Propagation Boost

The amplification of each node is mapped into the three regime cards using regime-specific sensitivity weights. The app therefore shows not only the direct rule-based contributions, but also the extra `recursive boost` created by second-round system pressure.

## Mathematical And Statistical Methods

The app uses several layers of mathematics to handle simultaneous analysis of multiple metrics with different units, release schedules, and noise properties.

The current funding build adds three practical controls on top of the earlier math stack:

- it separates **direct measurements** from **proxies**
- it adds a **synthetic composite** when no direct public feed exists for the exact concept
- it uses the direct support inputs to cross-check whether a proxy funding signal is credible

### 1. Threshold Normalization

For every thresholded metric, the app converts the raw value into a `0-100` stress score.

For `high-is-bad` metrics, the normalized score rises linearly from warning toward critical. For `low-is-bad` metrics such as cross-currency basis, the direction is inverted. Scores are clamped to `0-100`.

This is what allows Brent spreads, SOFR, payroll momentum, and FIMA usage to enter the same scoring system without pretending they are in the same physical units.

### 2. Rolling Z-Scores

For each time series, the app computes a rolling `30-observation` z-score using the population standard deviation of the recent window.

Purpose:

- identify how unusual today is relative to the recent local regime
- separate large absolute levels from locally accelerating deviations

### 3. Moving Averages

The app computes `7-observation` and `30-observation` moving averages for fast series and appropriate rolling transformations for slower monthly series such as payroll momentum.

Purpose:

- smooth noisy market series
- distinguish temporary spikes from persistent deterioration
- support breadth and trend interpretation in the panels

### 4. Percentile Bands

For each observation, the app computes its percentile in the recent `30-observation` window.

Purpose:

- tell whether a move is merely high, or high relative to its recent distribution
- improve explainability when a series has unstable scale or noisy variance

### 5. First Derivative: Rate Of Change

The app computes the first difference of each series:

`ROC_t = x_t - x_(t-1)`

Purpose:

- detect whether stress is rising or falling
- distinguish static high stress from fresh acceleration

### 6. Second Derivative: Acceleration

The app computes acceleration as the change in rate of change:

`Acceleration_t = ROC_t - ROC_(t-1)`

Purpose:

- detect whether deterioration itself is speeding up
- identify convex transitions where nonlinear stress matters more than the level alone

### 7. Rule-Based Weighted Regime Scoring

Each regime card is a weighted sum of normalized component scores, plus any recursive propagation boost.

This provides:

- transparency
- configurability through `backend/config/regime_config.json`
- explainability through driver contributions

The regime cards are **independent absolute scores**, not percentages that must sum to 100.

### 8. Simultaneity / Breadth Logic

The fast-moving stress panel and many alert rules use cross-indicator simultaneity. The app does not rely on one metric alone; it asks whether multiple fast indicators are warning at once.

Purpose:

- reduce false positives from isolated moves
- capture synchronization across physical, funding, Treasury-plumbing, and labor-transmission domains

### 9. Historical Analog Scoring

The app stores a curated historical episode library and converts the current normalized profile into a comparison vector. Similarity is scored against past episode templates and cluster centroids.

Purpose:

- determine whether the current profile most resembles a shipping-led, funding-led, plumbing-led, or energy-led subfamily
- improve interpretation when the same headline regime can arrive through different channels

### 10. Econometric State-Space Layer

The state-space model estimates latent states for:

- oil shock
- funding stress
- Treasury market stress
- intervention pressure
- repression risk

Observed indicators are treated as noisy measurements of those latent states. The filter operates on aligned historical measurement histories, carrying forward the latest available public observation when a source is slower-moving.

Purpose:

- infer hidden system stress that is not directly observable from one metric alone
- reduce overreliance on any single noisy series
- allow probability-based regime classification and forecasting

### 11. Ridge-Regularized Calibration

The econometric layer uses ridge-style regularization when fitting regime mappings from episode templates and historical state paths.

Purpose:

- prevent unstable coefficients from a relatively small curated episode library
- keep calibrated coefficients anchored near configured priors rather than overfitting a few episodes

### 12. Transition Calibration

The app calibrates latent-state transition dynamics from filtered state history and blends the fitted transitions with configured transitions.

Purpose:

- allow the system to learn persistence and cross-state spillovers from data
- avoid fully trusting either hardcoded transitions or unstable fitted transitions on their own

### 13. Filter Calibration

The app calibrates observation loadings and noise terms, then reruns the filter using blended parameters.

Purpose:

- adjust how strongly each indicator should move each latent state
- adapt the filter to the actual data behavior rather than keeping all loadings fixed forever

### 14. Iterative Estimation With Damping

The filter and transition calibrations are iterated with damping, baseline regularization, and a worsening guard.

Purpose:

- refine the state-space solution without allowing it to diverge or oscillate
- stop once parameter drift falls below tolerance or the maximum pass count is hit

### 15. Out-Of-Sample Validation And Trust Gating

The app runs leave-one-out style validation across the episode library and compares configured, calibrated, and iterative variants.

Purpose:

- decide how much to trust the econometric layer in live scoring
- reduce the calibrated blend if validation weakens
- keep the live model conservative when historical fit is not convincing

### 16. Cluster-Conditioned Forecasting

Forecast paths are conditioned on the active episode subfamily:

- Shipping / Insurance Shock
- Dollar Funding Squeeze
- Treasury Plumbing Break
- Energy / Inflation Shock

Purpose:

- different stress families propagate differently through time
- a shipping-led environment should not use the same transition bias as a repo-led environment

### 17. Regime-Dependent Observation Weighting

The app dynamically changes measurement trust multipliers depending on the active cluster and regime.

Purpose:

- trust shipping and oil indicators more in a shipping- or energy-led regime
- trust funding and plumbing indicators more in a funding- or break-led regime
- trust labor metrics more when the signal is migrating into domestic transmission
- acknowledge that the same indicator has different information content in different environments

### 18. Adaptive Econometric Alerting

The alert engine now combines threshold alerts with model-driven alerts from:

- latent-state acceleration
- subfamily rotation
- scenario-conditioned break-risk transitions
- validation guardrail state
- labor / tax-base / household-credit transmission combinations
- direct threshold breaches in newly added chokepoint series such as Hormuz tanker transit stress
- widening regional crude dislocation spreads such as Murban-WTI and Oman-WTI

Purpose:

- translate a complex multilayer model back into discrete operational warnings
- avoid forcing the user to infer regime escalation manually from every panel

## Employment Alert Logic

The app now includes employment-transmission alerts that specifically watch whether labor weakness is becoming economically relevant downstream.

### Payroll slowdown is feeding tax-base erosion

This alert fires when payroll momentum and the employment-tax-base proxy are both in warning or critical territory.

Interpretation:

- labor demand is weakening
- the federal withholding / payroll-tax base is weakening with it
- fiscal room may shrink even before more visible macro data worsens

### Temp-help deterioration is leaking into household credit

This alert fires when temporary-help stress and consumer-credit stress are both elevated.

Interpretation:

- white-collar or early-cycle labor demand is deteriorating
- household balance-sheet strain is beginning to show up alongside it
- labor weakness is no longer just a growth concern; it is becoming a credit concern

### Unemployment is rising as break-risk signals accelerate

This alert fires when unemployment is in warning or critical territory, the unemployment series is still rising, and at least two break-risk signals are already in warning or critical territory.

Interpretation:

- market/plumbing stress is no longer isolated
- domestic labor conditions are weakening at the same time
- the chain is moving toward a broader fiscal-credit-repression configuration

## How The Metrics Work Together

The complexity of analyzing the full stack simultaneously is handled by layering rather than by flattening everything into one number.

1. **Normalization** puts different units onto a common stress scale.
2. **Causal grouping** organizes the metrics by economic function.
3. **Recursive propagation** captures cross-node feedback loops.
4. **Regime scoring** turns the multi-metric state into interpretable cards.
5. **State-space filtering** estimates latent states underneath the noisy observables.
6. **Validation and trust gates** prevent the econometric layer from dominating if it underperforms historically.
7. **Alerts and simultaneity rules** flag when multiple dimensions of stress are aligning in real time.

That architecture is the app's answer to the simultaneity problem. It does not pretend the metrics are independent. Instead, it assumes they interact, models those interactions explicitly, and then forces the output back into an interpretable decision framework.

## Practical Reading Sequence

For day-to-day use, the most robust sequence is:

1. Read the three regime cards and the fast-moving stress panel.
2. Check the causal chain for where base stress is highest and where loop pressure is building.
3. Check the econometric layer for latent-state acceleration, current regime probability, cluster family, and forecast-conditioned break risk.
4. Use the historical analog panel to see which episode family the system most resembles.
5. Check the employment / receipts / household credit panel to see whether the macro shock is broadening into domestic fiscal and consumer channels.
6. Only then drill into the other detailed panels to determine whether the move is broadening or narrowing.

## Key Limitations

- `EUR/USD basis` and `JPY/USD basis` are still public proxies rather than direct licensed market feeds.
- Official series such as FIMA, swap-line data, monthly labor prints, and some FRED inputs are publication-lagged.
- The new Murban and Oman spread series are direct live values, but their public historical depth is still limited; those histories will strengthen as the app accumulates refresh observations over time.
- Marine insurance and geopolitical overlays are text-derived, not exchange-traded prices.
- The econometric layer is materially more advanced than the original rule engine, but it remains constrained by the size and quality of the episode library and by public data availability.
- The labor module uses high-quality public series, but some environments will still fall back to seeded demo values if a live fetch fails.

Those limits are real, but they do not negate the app's value. The app is strongest as a **multi-layer stress migration monitor**: it tells you whether the system is remaining a physical oil shock, becoming a nonlinear funding event, or crossing into Treasury dysfunction, domestic fiscal-credit strain, and repression risk.

## March 2026 Fine-Tuning Update

This build adds and/or makes explicit the following fine-tuning changes without changing the core thesis:

1. `Stagflation` is now an explicit executive interpretation layer rather than only an implicit result of the regime engine.
2. `Ordering discipline` is now shown directly in the executive view: physical shock first, income squeeze next, labor / receipts next, financial tightening last.
3. The app now gives more explicit weight to the household-income, tax-base, and receipts channel through `household_real_income_squeeze`, `employment_tax_base_proxy`, and `tax_receipts_market_stress`.
4. Long-end market stress remains central through yields, auction stress, Treasury liquidity, and term-premium logic, but the narrative now makes the physical-to-financial sequence more explicit.
5. Repo, basis, FIMA, and swap-line variables remain in the model, but they are framed as migration / late-stage variables rather than default first-order explanations.
6. The app now separates `physical oil dislocation` from `financial-market response` in the executive interpretation layer.
7. `VIX` is now a live propagation feature for risk appetite, tax-receipts sensitivity, and tightening of financial conditions.
8. `IG CDS` is still intentionally excluded from scoring because there is not yet a clean direct public feed good enough for production use.
9. The app now explicitly models `oil in local currency` stress through `oil_in_yen_stress`, `oil_in_eur_stress`, and `oil_in_cny_stress`, aggregated into `external_importer_stress`.
10. The external importer channel is now interpreted asymmetrically: Japan is the sharpest observable transmission path, Europe is a strong imported-inflation / funding amplifier, and China is treated as lower-confidence but still relevant to marginal UST-demand and Fed-plumbing interpretation.

## Mathematical Framework Appendix

### 1. Threshold Normalization

Each raw indicator is first converted into a normalized stress score on a `0-100` scale.

For indicators where higher values are more stressful:

```text
N_i(x) = clamp(50 + 50 * (x - warning_i) / (critical_i - warning_i), 0, 100)
```

For indicators where lower values are more stressful:

```text
N_i(x) = clamp(50 + 50 * (warning_i - x) / (warning_i - critical_i), 0, 100)
```

### 2. Rule-Based Regime Scores

```text
R_r = ?_i (w_(r,i) * N_i) + P_r
```

Where `R_r` is the regime score, `w_(r,i)` is the configured regime weight, `N_i` is the normalized indicator stress, and `P_r` is the recursive propagation boost.

### 3. Recursive Propagation Layer

```text
pressure_j^(t) = ?_k [ edge_(k?j) * max(0, score_k^(t) - activation_floor) ]

score_j^(t+1) = clamp(
    base_j * (1 - memory)
    + score_j^(t) * memory
    + pressure_j^(t) * feedback_gain
    + max(0, base_j - activation_floor) * pressure_j^(t) / 100 * synergy_gain,
    0,
    100
)
```

### 4. Executive Interpretation Layers

```text
Ordering stage score = average of stage component normalized scores
Stagflation composite = (inflation_score + growth_score + policy_constraint_score) / 3
Migration spread = financial_score - physical_score
```

### 5. State-Space Layer

```text
x_t = A x_(t-1) + w_t
y_t = C x_t + v_t
```

The latent states are `oil_shock`, `funding_stress`, `treasury_stress`, `intervention_pressure`, and `repression_risk`.

### 6. Threshold Parameters

| Indicator | Direction | Warning | Critical |
| --- | --- | --- | --- |
| auction_stress | high | 58 | 75 |
| brent_prompt_spread | high | 4.5 | 7.5 |
| central_bank_intervention_toggle | high | 1 | 1 |
| consumer_credit_stress | high | 58 | 72 |
| credit_spreads | high | 145 | 185 |
| deficit_trend | high | 55 | 72 |
| employment_tax_base_proxy | low | 3 | 0 |
| eur_usd_basis | low | -20 | -35 |
| expectations_entrenchment_score | high | 55 | 72 |
| expected_inflation_5y5y | high | 2.7 | 3.2 |
| external_importer_stress | high | 58 | 78 |
| fed_swap_line_usage | high | 5 | 15 |
| federal_receipts_quality | low | 45 | 35 |
| fima_repo_usage | high | 18 | 35 |
| geopolitical_escalation_toggle | high | 1 | 1 |
| gold_price | high | 2380 | 2520 |
| governance_fragmentation | high | 50 | 72 |
| gulf_crude_dislocation | high | 4 | 8 |
| hormuz_tanker_transit_stress | high | 55 | 75 |
| hours_worked_momentum | low | -0.05 | -0.25 |
| household_real_income_squeeze | high | 55 | 72 |
| iaea_nuclear_ambiguity | high | 55 | 78 |
| inflation_expectations_curvature | high | 15 | 35 |
| inflation_expectations_level | high | 2.55 | 3 |
| inflation_expectations_slope | high | 40 | 85 |
| interceptor_depletion | high | 55 | 78 |
| jpy_usd_basis | low | -30 | -50 |
| lng_proxy | high | 58 | 75 |
| marine_insurance_stress | high | 60 | 80 |
| move_index | high | 125 | 150 |
| murban_wti_spread | high | 4 | 8 |
| oil_in_cny_stress | high | 55 | 72 |
| oil_in_eur_stress | high | 58 | 78 |
| oil_in_yen_stress | high | 60 | 80 |
| oil_price | high | 88 | 102 |
| oman_wti_spread | high | 3 | 7 |
| p_and_i_circular_stress | high | 58 | 82 |
| payroll_momentum | low | 100 | 0 |
| private_credit_stress | high | 55 | 75 |
| sofr_spread | high | 25 | 50 |
| spx_equal_weight | low | 470 | 430 |
| survey_market_expectations_gap | high | 35 | 80 |
| synthetic_usd_funding_pressure | high | 55 | 72 |
| tanker_disruption_score | high | 58 | 78 |
| tanker_freight_proxy | high | 60 | 78 |
| tax_receipts_market_stress | high | 55 | 75 |
| temp_help_stress | low | -2 | -8 |
| ten_year_yield | high | 4.4 | 4.9 |
| term_premium_proxy | high | 55 | 80 |
| thirty_year_yield | high | 4.6 | 5.1 |
| tips_vs_nominals | high | 22 | 40 |
| treasury_basis_proxy | high | 55 | 72 |
| treasury_liquidity_proxy | high | 58 | 74 |
| unemployment_rate | high | 4.5 | 5.4 |
| usd_index_proxy | high | 104 | 108 |
| vix_index | high | 22 | 30 |
| wage_stickiness | high | 4 | 4.8 |
| wti_prompt_spread | high | 4 | 6.5 |

### 7. Rule Engine Weights

### Sticky Weights

| Indicator | Weight | Description |
| --- | --- | --- |
| brent_prompt_spread | 0.18 | Oil curve tightness remains visible across the M1-M6 window. |
| tanker_freight_proxy | 0.08 | Freight markets are transmitting the shipping shock. |
| gulf_crude_dislocation | 0.06 | Middle East export grades are dislocating versus WTI. |
| oman_wti_spread | 0.05 | Oman is richening versus U.S. crude, confirming regional dislocation. |
| murban_wti_spread | 0.06 | Murban is richening versus U.S. crude, showing Gulf export tightness. |
| hormuz_tanker_transit_stress | 0.08 | PortWatch shows tanker transit deterioration through the Strait of Hormuz. |
| marine_insurance_stress | 0.14 | Manual marine insurance stress overlay. |
| oil_price | 0.08 | Spot oil remains elevated. |
| jpy_usd_basis | 0.08 | Funding stress is visible but still contained. |
| consumer_credit_stress | 0.1 | Consumer balance sheets are deteriorating. |
| tips_vs_nominals | 0.12 | Inflation compensation is creeping higher. |
| auction_stress | 0.08 | Treasury demand is softer but not yet broken. |
| move_index | 0.07 | Rates volatility remains above calm levels. |
| sofr_spread | 0.07 | Repo plumbing is functional. |
| wage_stickiness | 0.08 | Wage growth remains sticky enough to keep inflation persistence alive. |
| employment_tax_base_proxy | 0.05 | The payroll-tax base is softening only gradually, keeping nominal demand alive. |
| synthetic_usd_funding_pressure | 0.05 | Direct FX spot and short-rate differentials show broad dollar funding pressure, but not a full break. |
| p_and_i_circular_stress | 0.03 | Official P&I notices show insurance withdrawal or reinstatement stress remains active. |
| iaea_nuclear_ambiguity | 0.015 | IAEA verification ambiguity is keeping the oil shock structurally alive. |
| expected_inflation_5y5y | 0.06 | Medium-term forward inflation expectations are no longer mean-reverting cleanly. |
| inflation_expectations_level | 0.07 | The expected-inflation curve is lifting across maturities. |
| expectations_entrenchment_score | 0.07 | Combined market and survey expectations point to persistence rather than transitory repricing. |
| survey_market_expectations_gap | 0.03 | Survey expectations are rising faster than the market-implied short end. |
| external_importer_stress | 0.05 | Local-currency oil stress in major importer regions is feeding imported inflation and current-account strain. |
| household_real_income_squeeze | 0.06 | Real household purchasing power is being squeezed before labor fully rolls over. |
| vix_index | 0.02 | Equity volatility is rising, hinting that the nominal shock is starting to tighten financial conditions. |
### Convex Weights

| Indicator | Weight | Description |
| --- | --- | --- |
| brent_prompt_spread | 0.14 | Brent M1-M6 backwardation is widening. |
| tanker_freight_proxy | 0.12 | Freight costs are accelerating. |
| gulf_crude_dislocation | 0.06 | Regional crude spreads are broadening as the shock migrates. |
| oman_wti_spread | 0.04 | Oman versus WTI is widening, reinforcing the Gulf supply shock. |
| murban_wti_spread | 0.04 | Murban versus WTI is widening, showing cross-basin dislocation. |
| hormuz_tanker_transit_stress | 0.06 | Hormuz tanker transit stress confirms the shipping shock is constraining flows. |
| jpy_usd_basis | 0.14 | JPY basis is materially more negative. |
| eur_usd_basis | 0.08 | EUR basis is also leaning into dollar scarcity. |
| sofr_spread | 0.12 | Repo stress is building. |
| move_index | 0.12 | Treasury volatility is elevated. |
| auction_stress | 0.11 | Long-end auction demand is slipping. |
| treasury_basis_proxy | 0.09 | Basis trade stress is visible. |
| fima_repo_usage | 0.04 | Foreign holders are drawing dollar liquidity. |
| private_credit_stress | 0.04 | Private credit marks are deteriorating. |
| payroll_momentum | 0.04 | Payroll growth is weakening as the shock reaches labor demand. |
| temp_help_stress | 0.04 | Temporary-help employment is deteriorating ahead of broader payroll weakness. |
| synthetic_usd_funding_pressure | 0.11 | Direct spot FX and rate differentials confirm broader dollar funding strain. |
| p_and_i_circular_stress | 0.035 | Insurance-market fragmentation is extending the physical shock into a longer-lived regime transition. |
| iaea_nuclear_ambiguity | 0.045 | Nuclear verification ambiguity is raising the odds of nonlinear repricing. |
| interceptor_depletion | 0.035 | Sustained defensive burn-rate pressure raises escalation convexity. |
| governance_fragmentation | 0.03 | Fragmented command signals reduce confidence in a clean reopening path. |
| expected_inflation_5y5y | 0.05 | Forward inflation expectations are climbing as the shock migrates into policy credibility. |
| inflation_expectations_curvature | 0.04 | The 5Y belly is richening versus the front and long end, signaling embedded persistence. |
| survey_market_expectations_gap | 0.03 | Survey-market expectation divergence is widening into a nonlinear repricing risk. |
| expectations_entrenchment_score | 0.05 | The combined expectations block shows persistence broadening beyond spot oil. |
| external_importer_stress | 0.08 | Japan, Europe, and China are absorbing a compounded local-currency energy shock. |
| vix_index | 0.05 | Equity volatility is broadening the tightening impulse beyond rates and oil. |
| household_real_income_squeeze | 0.04 | The real-income squeeze is increasing the chance that the oil shock migrates into broader demand and credit stress. |
### Break Weights

| Indicator | Weight | Description |
| --- | --- | --- |
| auction_stress | 0.17 | Repeated weak auctions are impairing duration clearing. |
| sofr_spread | 0.13 | Repo stress is persistent. |
| fima_repo_usage | 0.15 | Foreign official holders are pulling dollars against Treasuries. |
| fed_swap_line_usage | 0.13 | Fed swap lines are picking up. |
| treasury_liquidity_proxy | 0.12 | Treasury depth is deteriorating. |
| treasury_basis_proxy | 0.1 | Basis unwind pressure is visible. |
| move_index | 0.05 | Rates volatility is consistent with dysfunction. |
| consumer_credit_stress | 0.05 | Broader inflation inputs are leaking into credit. |
| private_credit_stress | 0.05 | Private credit is under markdown pressure. |
| central_bank_intervention_toggle | 0.05 | Manual intervention headline flag is set. |
| unemployment_rate | 0.06 | Labor-market slack is rising and feeding household credit stress. |
| payroll_momentum | 0.05 | Payroll hiring is weakening, damaging withholding and growth confidence. |
| hours_worked_momentum | 0.04 | Hours worked are rolling over before broader job cuts fully show up. |
| employment_tax_base_proxy | 0.08 | The labor-income tax base is eroding, worsening fiscal strain. |
| temp_help_stress | 0.04 | White-collar-sensitive temporary employment is signaling credit spillover risk. |
| synthetic_usd_funding_pressure | 0.09 | Synthetic funding pressure remains elevated alongside broader plumbing stress. |
| p_and_i_circular_stress | 0.02 | Insurance cancellation and case-by-case write-back stress reinforce trade and funding dysfunction. |
| iaea_nuclear_ambiguity | 0.05 | A widening verification gap creates abrupt tail-risk repricing pressure. |
| interceptor_depletion | 0.04 | High interceptor burn rates raise the probability of forced escalation into a market break. |
| governance_fragmentation | 0.04 | Governance fragmentation lowers the odds that chokepoint and war-risk stress can be resolved quickly. |
| expected_inflation_5y5y | 0.05 | Medium-term inflation expectations are high enough to constrain clean policy easing. |
| inflation_expectations_level | 0.04 | The full expected-inflation curve is inconsistent with a temporary commodity shock only. |
| expectations_entrenchment_score | 0.07 | Entrenched expectations raise repression risk once market plumbing is under strain. |
| external_importer_stress | 0.07 | Foreign importer balance-sheet stress is raising the odds of unstable marginal UST demand and Fed-plumbing pressure. |
| tax_receipts_market_stress | 0.07 | Volatility, weaker equities, and softer receipts quality are worsening capital-gains-sensitive fiscal pressure. |
| vix_index | 0.04 | High equity volatility is consistent with a broader risk-premium shock and tighter financial conditions. |

### 8. Propagation Parameters

| Parameter | Value |
| --- | --- |
| iterations | 4 |
| memory | 0.35 |
| activation_floor | 45 |
| feedback_gain | 0.24 |
| synergy_gain | 0.22 |

### 9. Propagation Edge Weights

| From | To | Weight |
| --- | --- | --- |
| geopolitical_trigger_stress | marine_insurance_stress | 0.46 |
| geopolitical_trigger_stress | oil_physical_stress | 0.32 |
| geopolitical_trigger_stress | dollar_funding_stress | 0.18 |
| marine_insurance_stress | oil_physical_stress | 0.34 |
| oil_physical_stress | dollar_funding_stress | 0.28 |
| dollar_funding_stress | ust_demand_stress | 0.3 |
| ust_demand_stress | repo_basis_stress | 0.34 |
| repo_basis_stress | ust_demand_stress | 0.24 |
| repo_basis_stress | fed_intervention_stress | 0.32 |
| fed_intervention_stress | inflation_repression_stress | 0.24 |
| inflation_repression_stress | ust_demand_stress | 0.18 |
| dollar_funding_stress | repo_basis_stress | 0.22 |
| oil_physical_stress | inflation_repression_stress | 0.18 |
| oil_physical_stress | expectations_credibility_stress | 0.24 |
| expectations_credibility_stress | ust_demand_stress | 0.24 |
| expectations_credibility_stress | inflation_repression_stress | 0.3 |
| expectations_credibility_stress | dollar_funding_stress | 0.08 |
| oil_physical_stress | external_importer_stress | 0.34 |
| external_importer_stress | dollar_funding_stress | 0.24 |
| external_importer_stress | ust_demand_stress | 0.32 |
| external_importer_stress | fed_intervention_stress | 0.12 |
| external_importer_stress | household_tax_stress | 0.16 |
| oil_physical_stress | household_tax_stress | 0.16 |
| household_tax_stress | inflation_repression_stress | 0.26 |
| household_tax_stress | ust_demand_stress | 0.18 |

### 10. Propagation-to-Regime Sensitivity

#### Sticky Propagation Sensitivity

| Node | Weight |
| --- | --- |
| marine_insurance_stress | 0.02 |
| oil_physical_stress | 0.04 |
| inflation_repression_stress | 0.03 |
| geopolitical_trigger_stress | 0.015 |
| expectations_credibility_stress | 0.03 |
| external_importer_stress | 0.025 |
| household_tax_stress | 0.025 |
#### Convex Propagation Sensitivity

| Node | Weight |
| --- | --- |
| oil_physical_stress | 0.04 |
| dollar_funding_stress | 0.06 |
| ust_demand_stress | 0.05 |
| repo_basis_stress | 0.06 |
| geopolitical_trigger_stress | 0.06 |
| expectations_credibility_stress | 0.035 |
| external_importer_stress | 0.05 |
| household_tax_stress | 0.03 |
#### Break Propagation Sensitivity

| Node | Weight |
| --- | --- |
| dollar_funding_stress | 0.04 |
| ust_demand_stress | 0.06 |
| repo_basis_stress | 0.08 |
| fed_intervention_stress | 0.07 |
| inflation_repression_stress | 0.05 |
| geopolitical_trigger_stress | 0.075 |
| expectations_credibility_stress | 0.04 |
| external_importer_stress | 0.05 |
| household_tax_stress | 0.06 |

### 11. State-Space Transition Matrix

| From \ To | oil_shock | funding_stress | treasury_stress | intervention_pressure | repression_risk |
| --- | --- | --- | --- | --- | --- |
| oil_shock | 0.82 | 0.08 | 0 | 0 | 0.04 |
| funding_stress | 0.16 | 0.76 | 0.1 | 0 | 0 |
| treasury_stress | 0 | 0.2 | 0.79 | 0.1 | 0.1 |
| intervention_pressure | 0 | 0.1 | 0.18 | 0.78 | 0.06 |
| repression_risk | 0.1 | 0 | 0.12 | 0.16 | 0.8 |

### 12. State-Space Noise and Initial Conditions

- Measurement noise floor: `25`
- Iterative estimation max iterations: `5`
- Iterative estimation tolerance: `0.08`
- Iterative estimation relaxation: `0.35`
- Iterative estimation noise relaxation: `0.25`
- Iterative estimation anchor weight: `0.18`
- Iterative estimation intercept scale: `0.5`
- Iterative estimation worsening-backoff: `0.6`

| State | Process noise | Initial state | Initial covariance |
| --- | --- | --- | --- |
| oil_shock | 18 | 45 | 80 |
| funding_stress | 16 | 40 | 70 |
| treasury_stress | 16 | 38 | 70 |
| intervention_pressure | 14 | 25 | 55 |
| repression_risk | 14 | 42 | 60 |

### 13. State-Space Measurement Loadings

| Indicator | Oil Shock | Funding Stress | Treasury Stress | Intervention Pressure | Repression Risk |
| --- | --- | --- | --- | --- | --- |
| brent_prompt_spread | 0.78 | 0.05 | 0 | 0 | 0.08 |
| wti_prompt_spread | 0.72 | 0.04 | 0 | 0 | 0.05 |
| tanker_freight_proxy | 0.64 | 0.06 | 0 | 0 | 0.02 |
| hormuz_tanker_transit_stress | 0.74 | 0.04 | 0 | 0 | 0.04 |
| lng_proxy | 0.46 | 0 | 0 | 0 | 0.08 |
| marine_insurance_stress | 0.62 | 0 | 0 | 0 | 0 |
| tanker_disruption_score | 0.68 | 0 | 0 | 0 | 0 |
| geopolitical_escalation_toggle | 0.55 | 0.12 | 0 | 0 | 0 |
| jpy_usd_basis | 0.04 | 0.82 | 0.08 | 0 | 0 |
| eur_usd_basis | 0.02 | 0.7 | 0.08 | 0 | 0 |
| sofr_spread | 0 | 0.58 | 0.28 | 0 | 0 |
| move_index | 0 | 0.2 | 0.64 | 0 | 0.06 |
| treasury_liquidity_proxy | 0 | 0.1 | 0.82 | 0.04 | 0 |
| treasury_basis_proxy | 0 | 0.16 | 0.78 | 0 | 0 |
| auction_stress | 0 | 0.1 | 0.74 | 0.04 | 0 |
| ten_year_yield | 0.1 | 0 | 0.44 | 0 | 0.28 |
| thirty_year_yield | 0.04 | 0 | 0.52 | 0 | 0.28 |
| term_premium_proxy | 0 | 0 | 0.54 | 0 | 0.32 |
| fima_repo_usage | 0 | 0.18 | 0.22 | 0.58 | 0 |
| fed_swap_line_usage | 0 | 0.28 | 0.12 | 0.58 | 0 |
| central_bank_intervention_toggle | 0 | 0.1 | 0.05 | 0.7 | 0.05 |
| consumer_credit_stress | 0.08 | 0.08 | 0.08 | 0 | 0.62 |
| private_credit_stress | 0 | 0.16 | 0.16 | 0 | 0.58 |
| tips_vs_nominals | 0.22 | 0 | 0.1 | 0 | 0.6 |
| gold_price | 0.12 | 0 | 0.04 | 0.02 | 0.52 |
| oil_price | 0.48 | 0 | 0.04 | 0 | 0.18 |
| payroll_momentum | 0.02 | 0.04 | 0.08 | 0 | 0.58 |
| unemployment_rate | 0 | 0.06 | 0.12 | 0 | 0.66 |
| wage_stickiness | 0.18 | 0 | 0.04 | 0 | 0.56 |
| hours_worked_momentum | 0.02 | 0.02 | 0.06 | 0 | 0.54 |
| temp_help_stress | 0 | 0.12 | 0.1 | 0 | 0.58 |
| employment_tax_base_proxy | 0.08 | 0.02 | 0.12 | 0 | 0.68 |
| synthetic_usd_funding_pressure | 0.02 | 0.72 | 0.12 | 0 | 0.04 |
| murban_wti_spread | 0.62 | 0.08 | 0 | 0 | 0.04 |
| oman_wti_spread | 0.58 | 0.08 | 0 | 0 | 0.04 |
| gulf_crude_dislocation | 0.7 | 0.1 | 0 | 0 | 0.05 |
| p_and_i_circular_stress | 0.66 | 0.06 | 0 | 0 | 0.04 |
| iaea_nuclear_ambiguity | 0.34 | 0.18 | 0.06 | 0.02 | 0.28 |
| interceptor_depletion | 0.28 | 0.12 | 0.08 | 0.03 | 0.12 |
| governance_fragmentation | 0.2 | 0.16 | 0.08 | 0.02 | 0.18 |
| expected_inflation_5y5y | 0.1 | 0 | 0.16 | 0 | 0.68 |
| inflation_expectations_level | 0.12 | 0 | 0.12 | 0 | 0.66 |
| inflation_expectations_slope | 0.18 | 0.02 | 0.1 | 0 | 0.42 |
| inflation_expectations_curvature | 0.1 | 0.02 | 0.08 | 0 | 0.46 |
| survey_market_expectations_gap | 0.08 | 0 | 0.04 | 0 | 0.56 |
| expectations_entrenchment_score | 0.12 | 0 | 0.12 | 0.02 | 0.72 |
| vix_index | 0 | 0.12 | 0.28 | 0 | 0.18 |
| oil_in_yen_stress | 0.18 | 0.34 | 0.16 | 0.02 | 0.1 |
| oil_in_eur_stress | 0.16 | 0.22 | 0.12 | 0 | 0.1 |
| oil_in_cny_stress | 0.12 | 0.16 | 0.08 | 0 | 0.08 |
| external_importer_stress | 0.1 | 0.34 | 0.24 | 0.06 | 0.1 |
| household_real_income_squeeze | 0.12 | 0.08 | 0.08 | 0 | 0.64 |
| tax_receipts_market_stress | 0 | 0.12 | 0.18 | 0.02 | 0.58 |

### 14. State-Space Regime Loadings

### State-Space Sticky Loadings

| State | Loading |
| --- | --- |
| oil_shock | 0.4 |
| funding_stress | 0.1 |
| treasury_stress | 0.05 |
| intervention_pressure | 0 |
| repression_risk | 0.35 |
### State-Space Convex Loadings

| State | Loading |
| --- | --- |
| oil_shock | 0.25 |
| funding_stress | 0.4 |
| treasury_stress | 0.2 |
| intervention_pressure | 0 |
| repression_risk | 0.1 |
### State-Space Break Loadings

| State | Loading |
| --- | --- |
| oil_shock | 0.05 |
| funding_stress | 0.2 |
| treasury_stress | 0.35 |
| intervention_pressure | 0.25 |
| repression_risk | 0.15 |

### 15. Observation Conditioning Parameters

- Cluster weight: `0.65`
- Regime weight: `0.55`
- Minimum multiplier: `0.72`
- Maximum multiplier: `1.6`

### Observation Conditioning Cluster: Shipping

| Indicator | Multiplier |
| --- | --- |
| brent_prompt_spread | 1.15 |
| eur_usd_basis | 0.92 |
| expected_inflation_5y5y | 1.04 |
| external_importer_stress | 1.08 |
| governance_fragmentation | 1.08 |
| gulf_crude_dislocation | 1.24 |
| hormuz_tanker_transit_stress | 1.45 |
| iaea_nuclear_ambiguity | 1.08 |
| inflation_expectations_level | 1.04 |
| interceptor_depletion | 1.06 |
| jpy_usd_basis | 0.92 |
| marine_insurance_stress | 1.45 |
| murban_wti_spread | 1.2 |
| oil_in_eur_stress | 1.08 |
| oil_in_yen_stress | 1.1 |
| oman_wti_spread | 1.18 |
| p_and_i_circular_stress | 1.4 |
| tanker_disruption_score | 1.45 |
| tanker_freight_proxy | 1.3 |
| treasury_liquidity_proxy | 0.9 |
| wti_prompt_spread | 1.1 |
### Observation Conditioning Cluster: Funding

| Indicator | Multiplier |
| --- | --- |
| employment_tax_base_proxy | 1.04 |
| eur_usd_basis | 1.35 |
| expectations_entrenchment_score | 1.08 |
| expected_inflation_5y5y | 1.05 |
| external_importer_stress | 1.18 |
| fed_swap_line_usage | 1.15 |
| fima_repo_usage | 1.1 |
| governance_fragmentation | 1.08 |
| iaea_nuclear_ambiguity | 1.08 |
| interceptor_depletion | 1.04 |
| jpy_usd_basis | 1.4 |
| marine_insurance_stress | 0.85 |
| move_index | 1.1 |
| oil_in_cny_stress | 1.08 |
| oil_in_eur_stress | 1.1 |
| oil_in_yen_stress | 1.16 |
| payroll_momentum | 1.05 |
| sofr_spread | 1.35 |
| survey_market_expectations_gap | 1.08 |
| synthetic_usd_funding_pressure | 1.25 |
| tax_receipts_market_stress | 1.1 |
| temp_help_stress | 1.08 |
| treasury_basis_proxy | 1.15 |
| vix_index | 1.08 |
### Observation Conditioning Cluster: Plumbing

| Indicator | Multiplier |
| --- | --- |
| auction_stress | 1.3 |
| brent_prompt_spread | 0.9 |
| employment_tax_base_proxy | 1.1 |
| expectations_entrenchment_score | 1.1 |
| expected_inflation_5y5y | 1.08 |
| external_importer_stress | 1.14 |
| fed_swap_line_usage | 1.15 |
| fima_repo_usage | 1.2 |
| governance_fragmentation | 1.06 |
| hours_worked_momentum | 1.05 |
| iaea_nuclear_ambiguity | 1.05 |
| inflation_expectations_level | 1.06 |
| interceptor_depletion | 1.05 |
| move_index | 1.25 |
| sofr_spread | 1.15 |
| synthetic_usd_funding_pressure | 1.1 |
| tax_receipts_market_stress | 1.12 |
| treasury_basis_proxy | 1.35 |
| treasury_liquidity_proxy | 1.45 |
| unemployment_rate | 1.08 |
| vix_index | 1.12 |
### Observation Conditioning Cluster: Energy

| Indicator | Multiplier |
| --- | --- |
| brent_prompt_spread | 1.4 |
| employment_tax_base_proxy | 1.06 |
| eur_usd_basis | 0.95 |
| expectations_entrenchment_score | 1.18 |
| expected_inflation_5y5y | 1.18 |
| external_importer_stress | 1.22 |
| governance_fragmentation | 1.08 |
| gulf_crude_dislocation | 1.32 |
| hormuz_tanker_transit_stress | 1.28 |
| household_real_income_squeeze | 1.14 |
| iaea_nuclear_ambiguity | 1.18 |
| inflation_expectations_curvature | 1.08 |
| inflation_expectations_level | 1.16 |
| inflation_expectations_slope | 1.1 |
| interceptor_depletion | 1.12 |
| jpy_usd_basis | 0.95 |
| marine_insurance_stress | 1.05 |
| murban_wti_spread | 1.28 |
| oil_in_cny_stress | 1.1 |
| oil_in_eur_stress | 1.16 |
| oil_in_yen_stress | 1.28 |
| oman_wti_spread | 1.24 |
| p_and_i_circular_stress | 1.25 |
| private_credit_stress | 1.08 |
| survey_market_expectations_gap | 1.06 |
| synthetic_usd_funding_pressure | 0.95 |
| tanker_freight_proxy | 1.15 |
| tips_vs_nominals | 1.18 |
| wage_stickiness | 1.12 |
| wti_prompt_spread | 1.35 |

### Observation Conditioning Regime: Sticky

| Indicator | Multiplier |
| --- | --- |
| brent_prompt_spread | 1.22 |
| employment_tax_base_proxy | 1.06 |
| expectations_entrenchment_score | 1.18 |
| expected_inflation_5y5y | 1.16 |
| external_importer_stress | 1.12 |
| gulf_crude_dislocation | 1.14 |
| hormuz_tanker_transit_stress | 1.18 |
| household_real_income_squeeze | 1.12 |
| iaea_nuclear_ambiguity | 1.06 |
| inflation_expectations_level | 1.16 |
| inflation_expectations_slope | 1.08 |
| marine_insurance_stress | 1.15 |
| murban_wti_spread | 1.12 |
| oil_in_yen_stress | 1.14 |
| oil_price | 1.1 |
| oman_wti_spread | 1.1 |
| p_and_i_circular_stress | 1.14 |
| survey_market_expectations_gap | 1.08 |
| synthetic_usd_funding_pressure | 1.04 |
| tanker_disruption_score | 1.15 |
| tanker_freight_proxy | 1.12 |
| tips_vs_nominals | 1.08 |
| wage_stickiness | 1.16 |
| wti_prompt_spread | 1.18 |
### Observation Conditioning Regime: Convex

| Indicator | Multiplier |
| --- | --- |
| auction_stress | 1.08 |
| eur_usd_basis | 1.18 |
| expectations_entrenchment_score | 1.12 |
| expected_inflation_5y5y | 1.12 |
| external_importer_stress | 1.18 |
| governance_fragmentation | 1.1 |
| gulf_crude_dislocation | 1.12 |
| iaea_nuclear_ambiguity | 1.14 |
| inflation_expectations_curvature | 1.12 |
| interceptor_depletion | 1.12 |
| jpy_usd_basis | 1.22 |
| move_index | 1.14 |
| murban_wti_spread | 1.08 |
| oil_in_eur_stress | 1.1 |
| oil_in_yen_stress | 1.18 |
| oman_wti_spread | 1.08 |
| p_and_i_circular_stress | 1.12 |
| payroll_momentum | 1.08 |
| private_credit_stress | 1.08 |
| sofr_spread | 1.2 |
| survey_market_expectations_gap | 1.1 |
| synthetic_usd_funding_pressure | 1.18 |
| temp_help_stress | 1.1 |
| treasury_basis_proxy | 1.12 |
| vix_index | 1.1 |
### Observation Conditioning Regime: Break

| Indicator | Multiplier |
| --- | --- |
| auction_stress | 1.2 |
| central_bank_intervention_toggle | 1.15 |
| employment_tax_base_proxy | 1.18 |
| expectations_entrenchment_score | 1.16 |
| expected_inflation_5y5y | 1.14 |
| external_importer_stress | 1.14 |
| fed_swap_line_usage | 1.18 |
| fima_repo_usage | 1.2 |
| governance_fragmentation | 1.16 |
| hours_worked_momentum | 1.12 |
| household_real_income_squeeze | 1.12 |
| iaea_nuclear_ambiguity | 1.18 |
| inflation_expectations_level | 1.1 |
| interceptor_depletion | 1.16 |
| move_index | 1.12 |
| p_and_i_circular_stress | 1.08 |
| payroll_momentum | 1.12 |
| synthetic_usd_funding_pressure | 1.12 |
| tax_receipts_market_stress | 1.18 |
| treasury_basis_proxy | 1.24 |
| treasury_liquidity_proxy | 1.32 |
| unemployment_rate | 1.18 |
| vix_index | 1.14 |

