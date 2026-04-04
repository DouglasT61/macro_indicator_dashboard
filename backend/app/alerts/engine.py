from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.services.analytics import determine_status


def _rising_streak(values: Sequence[float]) -> int:
    if len(values) < 2:
        return 0
    streak = 0
    for index in range(1, len(values)):
        if values[index] > values[index - 1]:
            streak += 1
        else:
            streak = 0
    return streak


def build_alerts(
    latest_values: dict[str, float],
    recent_history: dict[str, Sequence[float]],
    config: dict[str, Any],
    generated_at: datetime,
    systemic_warning_count: int,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    thresholds = config["thresholds"]

    def add_alert(severity: str, title: str, body: str, indicators: list[str], next_stage: str) -> None:
        alerts.append(
            {
                "timestamp": generated_at,
                "severity": severity,
                "title": title,
                "body": body,
                "related_indicators_json": indicators,
                "next_stage_consequence": next_stage,
            }
        )

    for key in [
        "brent_prompt_spread",
        "oil_buffer_depletion_stress",
        "jpy_usd_basis",
        "sofr_spread",
        "move_index",
        "auction_stress",
        "foreign_duration_sponsorship_stress",
        "fima_repo_usage",
        "fed_swap_line_usage",
        "consumer_credit_stress",
        "unemployment_rate",
        "employment_tax_base_proxy",
        "p_and_i_circular_stress",
        "iaea_nuclear_ambiguity",
        "interceptor_depletion",
        "governance_fragmentation",
    ]:
        value = latest_values.get(key)
        if value is None:
            continue
        status = determine_status(value, thresholds.get(key))
        if status == "orange":
            add_alert(
                "warning",
                f"{key.replace('_', ' ').title()} crossed warning threshold",
                f"{key.replace('_', ' ')} is at {value:.2f}, indicating the stress chain is advancing.",
                [key],
                "Watch the next node in the causal chain for spillover.",
            )
        elif status == "red":
            add_alert(
                "critical",
                f"{key.replace('_', ' ').title()} is in critical territory",
                f"{key.replace('_', ' ')} is at {value:.2f}, consistent with acute macro plumbing stress.",
                [key],
                "Expect the next stage of stress transmission to accelerate.",
            )

    if latest_values.get("jpy_usd_basis", 0) <= -30 and latest_values.get("sofr_spread", 0) >= 25:
        severity = "critical" if latest_values.get("jpy_usd_basis", 0) <= -50 and latest_values.get("sofr_spread", 0) >= 50 else "warning"
        add_alert(
            severity,
            "JPY basis widening while SOFR stress rises",
            "Dollar funding pressure is broadening from offshore basis markets into domestic repo plumbing.",
            ["jpy_usd_basis", "sofr_spread"],
            "Next stage is weaker foreign willingness to warehouse UST duration.",
        )

    if latest_values.get("auction_stress", 0) >= 58 and latest_values.get("move_index", 0) >= 125:
        severity = "critical" if latest_values.get("auction_stress", 0) >= 75 and latest_values.get("move_index", 0) >= 150 else "warning"
        add_alert(
            severity,
            "Weak long-end auction plus high MOVE",
            "Auction clearing is deteriorating while Treasury volatility remains elevated.",
            ["auction_stress", "move_index"],
            "The chain can progress into dealer saturation and basis unwind pressure.",
        )

    if determine_status(latest_values.get("oil_buffer_depletion_stress", 0.0), thresholds.get("oil_buffer_depletion_stress")) in {"orange", "red"} and determine_status(latest_values.get("iea_importer_oil_cover_stress", 0.0), thresholds.get("iea_importer_oil_cover_stress")) in {"orange", "red"}:
        severity = "critical" if latest_values.get("oil_buffer_depletion_stress", 0.0) >= float(thresholds["oil_buffer_depletion_stress"]["critical"]) else "warning"
        add_alert(
            severity,
            "Oil reserve buffers are thinning across key importers",
            "IEA reserve-cover depletion and importer-cover stress are aligning, suggesting the physical oil shock is exhausting its natural buffers.",
            ["oil_buffer_depletion_stress", "iea_importer_oil_cover_stress", "external_importer_stress"],
            "The next stage is stronger imported inflation pressure and a more persistent external-balance shock.",
        )

    if determine_status(latest_values.get("foreign_duration_sponsorship_stress", 0.0), thresholds.get("foreign_duration_sponsorship_stress")) in {"orange", "red"} and determine_status(latest_values.get("auction_foreign_sponsorship_stress", 0.0), thresholds.get("auction_foreign_sponsorship_stress")) in {"orange", "red"}:
        severity = "critical" if latest_values.get("foreign_duration_sponsorship_stress", 0.0) >= float(thresholds["foreign_duration_sponsorship_stress"]["critical"]) else "warning"
        add_alert(
            severity,
            "Foreign duration sponsorship is weakening",
            "Slow BEA external-balance support and live auction sponsorship weakness are pointing in the same direction for U.S. duration demand.",
            ["foreign_duration_sponsorship_stress", "auction_foreign_sponsorship_stress", "bea_foreign_financing_support"],
            "The next stage is worse auction clearing, higher term premium, and greater Fed-plumbing pressure.",
        )

    fima_streak = _rising_streak(recent_history.get("fima_repo_usage", []))
    if fima_streak >= int(config["alert_rules"]["fima_rising_streak"]["warning"]):
        severity = "critical" if fima_streak >= int(config["alert_rules"]["fima_rising_streak"]["critical"]) else "warning"
        add_alert(
            severity,
            "FIMA usage is rising",
            "Foreign official holders are increasingly accessing dollars against Treasuries.",
            ["fima_repo_usage"],
            "This can foreshadow weaker marginal foreign demand for U.S. duration.",
        )

    swap_streak = _rising_streak(recent_history.get("fed_swap_line_usage", []))
    if latest_values.get("fed_swap_line_usage", 0) > 0.5 and swap_streak >= int(config["alert_rules"]["swap_usage_rising"]["warning"]):
        severity = "critical" if swap_streak >= int(config["alert_rules"]["swap_usage_rising"]["critical"]) else "warning"
        add_alert(
            severity,
            "Fed swap line usage is rising",
            "Offshore dollar funding stress is leaning harder on central bank backstops.",
            ["fed_swap_line_usage"],
            "This is consistent with the system moving from convex stress toward break / repression risk.",
        )

    if latest_values.get("sofr_spread", 0) >= 25 and latest_values.get("treasury_basis_proxy", 0) >= 55 and latest_values.get("auction_stress", 0) >= 58:
        severity = "critical" if latest_values.get("sofr_spread", 0) >= 50 or latest_values.get("treasury_basis_proxy", 0) >= 72 else "warning"
        add_alert(
            severity,
            "Repo stress, basis unwind, and weak auctions are aligning",
            "Core funding markets and sovereign clearing are now reinforcing each other.",
            ["sofr_spread", "treasury_basis_proxy", "auction_stress"],
            "The likely next stage is Treasury market dysfunction requiring Fed plumbing support.",
        )

    payroll_status = determine_status(latest_values.get("payroll_momentum", 9999.0), thresholds.get("payroll_momentum"))
    tax_base_status = determine_status(latest_values.get("employment_tax_base_proxy", 9999.0), thresholds.get("employment_tax_base_proxy"))
    temp_help_status = determine_status(latest_values.get("temp_help_stress", 9999.0), thresholds.get("temp_help_stress"))
    unemployment_status = determine_status(latest_values.get("unemployment_rate", -9999.0), thresholds.get("unemployment_rate"))
    unemployment_streak = _rising_streak(recent_history.get("unemployment_rate", []))
    break_signal_count = sum(
        1
        for key in ["auction_stress", "treasury_liquidity_proxy", "treasury_basis_proxy", "fima_repo_usage"]
        if determine_status(latest_values.get(key, 0.0), thresholds.get(key)) in {"orange", "red"}
    )

    if payroll_status in {"orange", "red"} and tax_base_status in {"orange", "red"}:
        severity = "critical" if payroll_status == "red" or tax_base_status == "red" else "warning"
        add_alert(
            severity,
            "Payroll slowdown is feeding tax-base erosion",
            f"Payroll momentum is {latest_values.get('payroll_momentum', 0.0):.2f} while the employment tax-base proxy is {latest_values.get('employment_tax_base_proxy', 0.0):.2f}.",
            ["payroll_momentum", "employment_tax_base_proxy"],
            "The next stage is weaker federal receipts quality and less fiscal room as market stress broadens.",
        )

    if temp_help_status in {"orange", "red"} and determine_status(latest_values.get("consumer_credit_stress", 0.0), thresholds.get("consumer_credit_stress")) in {"orange", "red"}:
        severity = "critical" if temp_help_status == "red" and latest_values.get("consumer_credit_stress", 0.0) >= float(thresholds["consumer_credit_stress"]["critical"]) else "warning"
        add_alert(
            severity,
            "Temp-help deterioration is leaking into household credit",
            f"Temporary help employment stress is {latest_values.get('temp_help_stress', 0.0):.2f} while consumer credit stress is {latest_values.get('consumer_credit_stress', 0.0):.2f}.",
            ["temp_help_stress", "consumer_credit_stress"],
            "The next stage is broader labor-market spillover into bank and household credit stress.",
        )

    if unemployment_status in {"orange", "red"} and unemployment_streak >= 2 and break_signal_count >= 2:
        severity = "critical" if unemployment_status == "red" or break_signal_count >= 3 else "warning"
        add_alert(
            severity,
            "Unemployment is rising as break-risk signals accelerate",
            f"Unemployment has risen for {unemployment_streak} observations and {break_signal_count} break-risk signals are already in warning or critical territory.",
            ["unemployment_rate", "auction_stress", "treasury_liquidity_proxy", "treasury_basis_proxy", "fima_repo_usage"],
            "The chain is shifting from market stress into domestic labor, fiscal, and household-credit transmission.",
        )

    if determine_status(latest_values.get("p_and_i_circular_stress", 0.0), thresholds.get("p_and_i_circular_stress")) in {"orange", "red"} and determine_status(latest_values.get("hormuz_tanker_transit_stress", 0.0), thresholds.get("hormuz_tanker_transit_stress")) in {"orange", "red"}:
        severity = "critical" if latest_values.get("p_and_i_circular_stress", 0.0) >= float(thresholds["p_and_i_circular_stress"]["critical"]) else "warning"
        add_alert(
            severity,
            "Insurance withdrawal and Hormuz transit stress are aligning",
            "Official war-risk notice stress and direct Hormuz tanker transit deterioration are now confirming the same physical disruption channel.",
            ["p_and_i_circular_stress", "hormuz_tanker_transit_stress", "marine_insurance_stress"],
            "The next stage is a longer-lived oil-flow impairment and wider freight dislocation.",
        )

    if determine_status(latest_values.get("iaea_nuclear_ambiguity", 0.0), thresholds.get("iaea_nuclear_ambiguity")) in {"orange", "red"} and determine_status(latest_values.get("brent_prompt_spread", 0.0), thresholds.get("brent_prompt_spread")) in {"orange", "red"}:
        severity = "critical" if latest_values.get("iaea_nuclear_ambiguity", 0.0) >= float(thresholds["iaea_nuclear_ambiguity"]["critical"]) else "warning"
        add_alert(
            severity,
            "Nuclear ambiguity is reinforcing the oil shock",
            "IAEA verification ambiguity and oil-curve tightness are moving together, increasing the odds of abrupt tail-risk repricing.",
            ["iaea_nuclear_ambiguity", "brent_prompt_spread", "oil_price"],
            "The chain can jump from physical scarcity into a faster convex funding response.",
        )

    if determine_status(latest_values.get("interceptor_depletion", 0.0), thresholds.get("interceptor_depletion")) in {"orange", "red"} and determine_status(latest_values.get("tanker_freight_proxy", 0.0), thresholds.get("tanker_freight_proxy")) in {"orange", "red"}:
        severity = "critical" if latest_values.get("interceptor_depletion", 0.0) >= float(thresholds["interceptor_depletion"]["critical"]) else "warning"
        add_alert(
            severity,
            "Interceptor burn-rate pressure is lifting shipping stress",
            "High operational depletion pressure and rising tanker freight are aligning, consistent with escalation convexity rather than mean reversion.",
            ["interceptor_depletion", "tanker_freight_proxy", "tanker_disruption_score"],
            "The next stage is higher insurance, weaker transits, and a broader oil-market dislocation.",
        )

    if determine_status(latest_values.get("governance_fragmentation", 0.0), thresholds.get("governance_fragmentation")) in {"orange", "red"} and determine_status(latest_values.get("jpy_usd_basis", 0.0), thresholds.get("jpy_usd_basis")) in {"orange", "red"}:
        severity = "critical" if latest_values.get("governance_fragmentation", 0.0) >= float(thresholds["governance_fragmentation"]["critical"]) else "warning"
        add_alert(
            severity,
            "Governance fragmentation is extending disruption half-life",
            "Fragmented command signals and stressed offshore dollar funding suggest the market is starting to price a less governable and less reversible regime.",
            ["governance_fragmentation", "jpy_usd_basis", "synthetic_usd_funding_pressure"],
            "The next stage is a more persistent migration into sovereign-duration and plumbing stress.",
        )

    if systemic_warning_count >= int(config["alert_rules"]["systemic_warning_count"]["warning"]):
        severity = "critical" if systemic_warning_count >= int(config["alert_rules"]["systemic_warning_count"]["critical"]) else "warning"
        add_alert(
            severity,
            "Systemic stress monitor triggered",
            f"{systemic_warning_count} fast-moving stress signals are in warning or critical territory at once.",
            ["treasury_liquidity_proxy", "sofr_spread", "treasury_basis_proxy", "jpy_usd_basis", "brent_prompt_spread"],
            "The chain is synchronizing across physical oil, dollar funding, and Treasury plumbing.",
        )

    return alerts


def build_state_space_alerts(
    state_space: dict[str, Any],
    backtest: dict[str, Any],
    generated_at: datetime,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    def add_alert(severity: str, title: str, body: str, indicators: list[str], next_stage: str) -> None:
        alerts.append(
            {
                "timestamp": generated_at,
                "severity": severity,
                "title": title,
                "body": body,
                "related_indicators_json": indicators,
                "next_stage_consequence": next_stage,
            }
        )

    forecast = state_space.get('forecast', {})
    calibration = state_space.get('calibration', {})
    diagnostics = state_space.get('diagnostics', {})
    states = {row['key']: float(row['value']) for row in state_space.get('states', [])}
    state_changes = {row['key']: float(row['change_7d']) for row in state_space.get('states', [])}
    cluster_focus = calibration.get('cluster_focus', {})
    trust_gate = calibration.get('trust_gate', {})

    break_10d = next((row for row in forecast.get('horizons', []) if int(row.get('days', 0)) == 10), None)
    if break_10d and float(break_10d.get('break', 0.0)) >= 35.0:
        severity = 'critical' if float(break_10d.get('break', 0.0)) >= 45.0 else 'warning'
        add_alert(
            severity,
            'Latent-state break-risk transition is building',
            f"10-day break confidence is {float(break_10d['break']):.1f}% under {forecast.get('conditioning_label', 'current')} conditioning.",
            ['forecast_break_probability', forecast.get('conditioning_cluster', 'forecast_conditioning')],
            'The system can rotate from convex stress into Treasury market dysfunction and Fed backstop usage.',
        )

    if states.get('treasury_stress', 0.0) >= 62.0 and state_changes.get('treasury_stress', 0.0) >= 6.0:
        add_alert(
            'critical' if states.get('treasury_stress', 0.0) >= 70.0 else 'warning',
            'Latent Treasury stress is accelerating',
            f"Treasury stress latent state is {states.get('treasury_stress', 0.0):.1f} with a 7-day change of {state_changes.get('treasury_stress', 0.0):+.1f}.",
            ['treasury_stress', 'auction_stress', 'treasury_liquidity_proxy', 'treasury_basis_proxy'],
            'Acceleration here raises the odds of a disorderly sovereign-clearing episode.',
        )

    if states.get('funding_stress', 0.0) >= 58.0 and state_changes.get('funding_stress', 0.0) >= 6.0:
        add_alert(
            'warning',
            'Latent funding stress is broadening',
            f"Funding stress latent state is {states.get('funding_stress', 0.0):.1f} with a 7-day change of {state_changes.get('funding_stress', 0.0):+.1f}.",
            ['funding_stress', 'jpy_usd_basis', 'eur_usd_basis', 'sofr_spread'],
            'The next stage is migration into Treasury demand and repo/basis stress.',
        )

    if cluster_focus.get('confidence', 0.0) >= 0.45 and backtest.get('dominant_cluster') in {'plumbing', 'funding'}:
        add_alert(
            'warning',
            'Episode family rotated into a tighter macro-stress subfamily',
            f"Dominant subfamily is {backtest.get('dominant_cluster_label', 'unknown')} at {float(backtest.get('cluster_confidence', 0.0)) * 100:.0f}% confidence.",
            ['episode_cluster', backtest.get('dominant_cluster', 'unknown')],
            'That shift usually precedes more direct pressure on sovereign duration clearing and central-bank facilities.',
        )

    if trust_gate.get('status') == 'Reduced' and diagnostics.get('confidence_band') == 'Fragile':
        add_alert(
            'info',
            'Latent-state confidence is constrained by model guardrails',
            trust_gate.get('summary', 'Model guardrails reduced the live latent-state blend.'),
            ['trust_gate', 'validation'],
            'Treat the current latent-state read as tentative until the signal broadens or forecast conviction rises.',
        )

    scenarios = forecast.get('scenarios', [])
    if scenarios:
        top_scenario = scenarios[0]
        if float(top_scenario.get('break', 0.0)) >= 40.0:
            add_alert(
                'critical' if float(top_scenario.get('break', 0.0)) >= 50.0 else 'warning',
                'Stress scenario points to a break-risk path',
                f"{top_scenario.get('label', 'Top scenario')} implies {float(top_scenario.get('break', 0.0)):.1f}% break confidence over the scenario horizon.",
                [top_scenario.get('key', 'scenario'), 'forecast'],
                'If the scenario begins to align with live data, expect intervention pressure and repression risk to rise quickly.',
            )

    return alerts
