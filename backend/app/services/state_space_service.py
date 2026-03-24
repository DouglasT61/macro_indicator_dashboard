from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.services.analytics import clamp, normalize_value
from app.services.backtest_service import EPISODE_TEMPLATES, extract_snapshot_profile, infer_episode_cluster
from app.services.filter_calibration_service import fit_filter_calibration
from app.services.transition_calibration_service import fit_transition_calibration


STATE_LABELS = {
    'oil_shock': 'Oil Shock',
    'funding_stress': 'Dollar Funding Stress',
    'treasury_stress': 'Treasury Market Stress',
    'intervention_pressure': 'Fed Backstop Pressure',
    'repression_risk': 'Inflation / Repression Risk',
}
REGIME_LABELS = {
    'sticky': 'Sticky',
    'convex': 'Convex',
    'break': 'Break',
}
REGIME_ORDER = ('sticky', 'convex', 'break')
SCENARIO_LIBRARY = [
    {
        'key': 'oil_escalation',
        'label': 'Oil Escalation Shock',
        'description': 'Shipping, insurance, and prompt crude tightness intensify before funding stress fully clears.',
        'impulse': [16.0, 8.0, 3.0, 0.0, 7.0],
    },
    {
        'key': 'dollar_short_squeeze',
        'label': 'Dollar Short Squeeze',
        'description': 'Cross-currency funding strain and repo pressure migrate quickly into Treasury market stress.',
        'impulse': [3.0, 18.0, 12.0, 5.0, 4.0],
    },
    {
        'key': 'treasury_plumbing_break',
        'label': 'Treasury Plumbing Break',
        'description': 'Auction weakness and liquidity breakdown force a rapid jump in intervention pressure and repression risk.',
        'impulse': [0.0, 9.0, 20.0, 14.0, 10.0],
    },
]

FORECAST_CLUSTER_ADJUSTMENTS = {
    'shipping': {
        'transition_deltas': [(0, 0, 0.04), (0, 1, 0.03), (0, 4, 0.02), (1, 2, 0.01)],
        'intercept_deltas': [2.4, 1.2, 0.3, 0.0, 1.2],
        'scenario_bias': {'oil_escalation': 1.15, 'dollar_short_squeeze': 0.95, 'treasury_plumbing_break': 0.9},
    },
    'funding': {
        'transition_deltas': [(1, 1, 0.05), (1, 2, 0.04), (2, 3, 0.03), (1, 3, 0.02)],
        'intercept_deltas': [0.6, 2.2, 1.2, 0.7, 0.2],
        'scenario_bias': {'oil_escalation': 0.9, 'dollar_short_squeeze': 1.15, 'treasury_plumbing_break': 1.0},
    },
    'plumbing': {
        'transition_deltas': [(2, 2, 0.06), (2, 3, 0.05), (3, 4, 0.03), (1, 2, 0.03)],
        'intercept_deltas': [0.1, 1.0, 2.4, 1.8, 1.0],
        'scenario_bias': {'oil_escalation': 0.85, 'dollar_short_squeeze': 1.0, 'treasury_plumbing_break': 1.2},
    },
    'energy': {
        'transition_deltas': [(0, 0, 0.05), (0, 4, 0.03), (4, 2, 0.02), (0, 1, 0.02)],
        'intercept_deltas': [2.0, 0.8, 0.6, 0.0, 1.8],
        'scenario_bias': {'oil_escalation': 1.12, 'dollar_short_squeeze': 0.92, 'treasury_plumbing_break': 0.95},
    },
}


def _mat_vec_mul(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(cell * vector[col] for col, cell in enumerate(row)) for row in matrix]


def _mat_mul(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    rows = len(left)
    cols = len(right[0])
    inner = len(right)
    return [
        [sum(left[row][idx] * right[idx][col] for idx in range(inner)) for col in range(cols)]
        for row in range(rows)
    ]


def _transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def _diag(values: list[float]) -> list[list[float]]:
    size = len(values)
    return [[values[row] if row == col else 0.0 for col in range(size)] for row in range(size)]


def _softmax(scores: dict[str, float], temperature: float = 18.0) -> dict[str, float]:
    del temperature
    positive_scores = {key: max(0.0, float(value)) for key, value in scores.items()}
    total = sum(positive_scores.values())
    if total <= 0:
        equal_share = round(100.0 / max(1, len(positive_scores)), 2)
        return {key: equal_share for key in positive_scores}
    return {key: round((value / total) * 100.0, 2) for key, value in positive_scores.items()}


def _dominant_regime(probabilities: dict[str, float]) -> str:
    return max(REGIME_ORDER, key=lambda key: float(probabilities[key]))


def _empty_state_space(rule_regime: str, message: str) -> dict[str, Any]:
    fallback_regime = 'break' if rule_regime.lower().startswith('break') else rule_regime.lower().split()[0]
    return {
        'current_regime': fallback_regime,
        'current_probability': 0.0,
        'rule_agreement': True,
        'agreement_summary': message,
        'observation_coverage': 0.0,
        'innovation_stress': 0.0,
        'states': [],
        'state_history': [],
        'probability_history': [],
        'diagnostics': {
            'recent_disagreement_streak': 0,
            'dominant_regime_flips': 0,
            'max_probability_gap': 0.0,
            'latest_probability_gap': 0.0,
            'confidence_band': 'Unavailable',
            'tracking_quality': 'No aligned history',
        },
        'disagreement_history': [],
        'forecast': {
            'summary': 'No forward confidence path is available because aligned measurement history is missing.',
            'conditioning_cluster': 'unavailable',
            'conditioning_label': 'Unavailable',
            'conditioning_confidence': 0.0,
            'conditioning_summary': 'Forecast conditioning unavailable because aligned measurement history is missing.',
            'baseline_path': [],
            'horizons': [],
            'scenarios': [],
        },
        'calibration': {
            'method': 'configured latent-state monitor',
            'sample_size': 0,
            'fit_rmse': 0.0,
            'quality': 'Unavailable',
            'blend_weight': 0.0,
            'base_blend_weight': 0.0,
            'summary': 'Historical fit layers are disabled because aligned measurement history is missing.',
            'configured_regime': fallback_regime,
            'configured_probability': 0.0,
            'calibrated_regime': fallback_regime,
            'calibrated_probability': 0.0,
            'configured_probability_history': [],
            'calibrated_probability_history': [],
            'episodes': [],
            'cluster_focus': {
                'key': 'unavailable',
                'label': 'Unavailable',
                'confidence': 0.0,
                'summary': 'Episode subfamily classification unavailable because aligned measurement history is missing.',
                'supporting_episodes': [],
            },
            'trust_gate': {
                'status': 'Disabled',
                'base_blend_weight': 0.0,
                'effective_blend_weight': 0.0,
                'guardrail_factor': 0.0,
                'configured_avg_rmse': 0.0,
                'iterative_avg_rmse': 0.0,
                'configured_hit_rate': 0.0,
                'iterative_hit_rate': 0.0,
                'summary': 'Historical validation guardrails are disabled in the configured latent-state monitor.',
            },
            'transition': {
                'fit_rmse': 0.0,
                'quality': 'Unavailable',
                'blend_weight': 0.0,
                'summary': 'Configured transition matrix unavailable because aligned measurement history is missing.',
                'configured_persistence': 0.0,
                'fitted_persistence': 0.0,
                'blended_persistence': 0.0,
                'drift_strength': 0.0,
                'links': [],
            },
            'filter': {
                'fit_rmse': 0.0,
                'quality': 'Unavailable',
                'blend_weight': 0.0,
                'summary': 'Configured observation filter unavailable because aligned measurement history is missing.',
                'configured_noise_floor': 0.0,
                'fitted_noise_floor': 0.0,
                'blended_noise_floor': 0.0,
                'configured_process_noise': 0.0,
                'fitted_process_noise': 0.0,
                'blended_process_noise': 0.0,
                'observations': [],
                'observation_conditioning': {
                    'cluster_key': 'unavailable',
                    'cluster_label': 'Unavailable',
                    'cluster_confidence': 0.0,
                    'regime_key': fallback_regime,
                    'regime_probability': 0.0,
                    'average_trust': 1.0,
                    'boosted_indicators': [],
                    'reduced_indicators': [],
                    'summary': 'Observation conditioning unavailable because aligned measurement history is missing.',
                },
            },
            'iteration': {
                'iterations_run': 0,
                'max_iterations': 0,
                'tolerance': 0.0,
                'converged': False,
                'final_parameter_delta': 0.0,
                'summary': 'Iterative estimation is disabled in the configured latent-state monitor.',
                'path': [],
            },
            'validation': {
                'summary': 'Historical validation is disabled in the configured latent-state monitor.',
                'configured_hit_rate': 0.0,
                'calibrated_hit_rate': 0.0,
                'iterative_hit_rate': 0.0,
                'configured_avg_rmse': 0.0,
                'calibrated_avg_rmse': 0.0,
                'iterative_avg_rmse': 0.0,
                'episodes': [],
            },
        },
    }


def _build_measurement_histories(
    snapshots: dict[str, dict[str, Any]],
    thresholds: dict[str, dict[str, Any]],
    measurements: dict[str, list[float]],
) -> tuple[list[datetime], dict[str, dict[datetime, float]]]:
    histories: dict[str, dict[datetime, float]] = {}
    timestamps: set[datetime] = set()

    for key in measurements:
        snapshot = snapshots.get(key)
        if snapshot is None:
            continue
        series_history: dict[datetime, float] = {}
        for point in snapshot.get('history', [])[-120:]:
            timestamp = point['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            value = float(point['value'])
            normalized = normalize_value(value, thresholds.get(key))
            if normalized is None:
                continue
            series_history[timestamp] = float(normalized)
            timestamps.add(timestamp)
        if series_history:
            histories[key] = dict(sorted(series_history.items(), key=lambda item: item[0]))

    return sorted(timestamps), histories


def _carry_forward_observations(
    timestamps: list[datetime],
    histories: dict[str, dict[datetime, float]],
) -> list[dict[str, float]]:
    carried: dict[str, float] = {}
    rows: list[dict[str, float]] = []
    for timestamp in timestamps:
        row: dict[str, float] = {}
        for key, history in histories.items():
            if timestamp in history:
                carried[key] = history[timestamp]
            if key in carried:
                row[key] = carried[key]
        rows.append(row)
    return rows


def _state_scores(values: list[float], state_keys: list[str]) -> dict[str, float]:
    return {key: round(clamp(value), 2) for key, value in zip(state_keys, values)}


def _configured_regime_scores(values: list[float], state_config: dict[str, Any]) -> dict[str, float]:
    loadings = state_config.get('regime_loadings', {})
    scores: dict[str, float] = {}
    for regime, weights in loadings.items():
        weighted = sum(values[index] * float(weight) for index, weight in enumerate(weights))
        normalizer = sum(float(weight) for weight in weights) or 1.0
        scores[regime] = round(clamp(weighted / normalizer), 2)
    return scores


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]

    for pivot_col in range(size):
        pivot_row = max(range(pivot_col, size), key=lambda row: abs(augmented[row][pivot_col]))
        if abs(augmented[pivot_row][pivot_col]) < 1e-9:
            augmented[pivot_row][pivot_col] = 1e-9
        if pivot_row != pivot_col:
            augmented[pivot_col], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_col]

        pivot_value = augmented[pivot_col][pivot_col]
        augmented[pivot_col] = [value / pivot_value for value in augmented[pivot_col]]

        for row in range(size):
            if row == pivot_col:
                continue
            factor = augmented[row][pivot_col]
            augmented[row] = [
                augmented[row][col] - factor * augmented[pivot_col][col]
                for col in range(size + 1)
            ]

    return [augmented[row][-1] for row in range(size)]


def _fit_ridge_coefficients(
    inputs: list[list[float]],
    targets: list[float],
    ridge: float = 12.0,
    sample_weights: list[float] | None = None,
    anchor: list[float] | None = None,
    anchor_strength: float = 0.0,
) -> list[float]:
    design = [[1.0, *row] for row in inputs]
    design_t = _transpose(design)
    weights = sample_weights or [1.0 for _ in targets]
    weighted_design = [
        [design[row][col] * weights[row] for col in range(len(design[row]))]
        for row in range(len(design))
    ]
    xtx = _mat_mul(design_t, weighted_design)
    weighted_targets = [targets[row] * weights[row] for row in range(len(targets))]
    xty = [sum(design_t[row][col] * weighted_targets[col] for col in range(len(targets))) for row in range(len(design_t))]

    if anchor is None:
        anchor = [0.0 for _ in range(len(xtx))]
    for index in range(len(xtx)):
        penalty = ridge if index > 0 else ridge * 0.1
        prior_penalty = anchor_strength if index > 0 else anchor_strength * 0.1
        xtx[index][index] += penalty + prior_penalty
        xty[index] += float(anchor[index]) * prior_penalty
    return _solve_linear_system(xtx, xty)


def _template_state_vector(
    profile: dict[str, float],
    state_keys: list[str],
    measurements: dict[str, list[float]],
) -> list[float]:
    values: list[float] = []
    for state_index, _ in enumerate(state_keys):
        weighted_sum = 0.0
        total_weight = 0.0
        for indicator, target in profile.items():
            loading = measurements.get(indicator)
            if not loading:
                continue
            weight = abs(float(loading[state_index]))
            if weight <= 0:
                continue
            weighted_sum += float(target) * weight
            total_weight += weight
        values.append(round(weighted_sum / total_weight, 2) if total_weight else 50.0)
    return values


def _configured_regime_beta(state_config: dict[str, Any], regime: str) -> list[float]:
    weights = [float(value) for value in state_config.get('regime_loadings', {}).get(regime, [])]
    normalizer = sum(weights) or 1.0
    return [0.0, *[weight / normalizer for weight in weights]]


def _episode_weight(template: Any, state_config: dict[str, Any]) -> float:
    settings = state_config.get('regime_calibration', {})
    explicit = settings.get('episode_weights', {})
    if template.key in explicit:
        return float(explicit[template.key])
    bias_weights = settings.get('bias_weights', {})
    return float(bias_weights.get(template.regime_bias, 1.0))


def _cluster_weight_multiplier(template: Any, state_config: dict[str, Any], cluster_key: str | None, cluster_confidence: float) -> float:
    if not cluster_key:
        return 1.0
    settings = state_config.get('regime_calibration', {}).get('cluster_weighting', {})
    same_cluster_boost = float(settings.get('same_cluster_boost', 0.45))
    other_cluster_penalty = float(settings.get('other_cluster_penalty', 0.12))
    confidence = max(0.0, min(1.0, float(cluster_confidence)))
    if getattr(template, 'cluster', None) == cluster_key:
        return round(1.0 + same_cluster_boost * confidence, 4)
    return round(max(0.55, 1.0 - other_cluster_penalty * confidence), 4)


def _predict_regime_scores_from_coefficients(state: list[float], coefficients: dict[str, list[float]]) -> dict[str, float]:
    features = [1.0, *state]
    scores: dict[str, float] = {}
    for regime, beta in coefficients.items():
        value = sum(beta[index] * features[index] for index in range(len(features)))
        scores[regime] = round(clamp(value), 2)
    return scores


def _calibration_quality(fit_rmse: float) -> tuple[str, float]:
    if fit_rmse <= 8.0:
        return 'Strong', 0.8
    if fit_rmse <= 14.0:
        return 'Usable', 0.6
    return 'Fragile', 0.35


def _capped_blend_weight(base_weight: float, state_config: dict[str, Any]) -> float:
    max_blend = float(state_config.get('regime_calibration', {}).get('max_blend_weight', 0.35))
    return round(min(max_blend, base_weight), 2)


def _forecast_cluster_intensity(confidence: float) -> float:
    return round(max(0.35, min(1.0, 0.35 + float(confidence))), 2)


def _condition_forecast_dynamics(
    transition: list[list[float]],
    transition_intercepts: list[float] | None,
    cluster_key: str,
    confidence: float,
) -> tuple[list[list[float]], list[float], dict[str, float], str]:
    profile = FORECAST_CLUSTER_ADJUSTMENTS.get(cluster_key)
    base_intercepts = [float(value) for value in (transition_intercepts or [0.0 for _ in range(len(transition))])]
    if not profile:
        return [[float(cell) for cell in row] for row in transition], base_intercepts, {}, 'Forecast uses neutral transition dynamics.'

    intensity = _forecast_cluster_intensity(confidence)
    conditioned_transition = [[float(cell) for cell in row] for row in transition]
    for row, col, delta in profile.get('transition_deltas', []):
        conditioned_transition[row][col] = round(clamp(conditioned_transition[row][col] + float(delta) * intensity), 4)

    conditioned_intercepts = [
        round(base_intercepts[index] + float(profile.get('intercept_deltas', [0.0 for _ in base_intercepts])[index]) * intensity, 4)
        for index in range(len(base_intercepts))
    ]
    scenario_bias = {key: round(float(value), 2) for key, value in profile.get('scenario_bias', {}).items()}
    summary = (
        f"Forecast is conditioned on the {cluster_key.replace('_', ' ')} subfamily with intensity {intensity:.2f}, "
        f"tilting transition persistence and intercept drift toward its historical propagation pattern."
    )
    return conditioned_transition, conditioned_intercepts, scenario_bias, summary


def _build_observation_context(
    measurements: dict[str, list[float]],
    state_config: dict[str, Any],
    cluster_focus: dict[str, Any],
    regime_key: str,
    regime_probability: float,
) -> dict[str, Any]:
    settings = state_config.get('observation_conditioning', {})
    cluster_profiles = settings.get('cluster_profiles', {})
    regime_profiles = settings.get('regime_profiles', {})
    cluster_weight = float(settings.get('cluster_weight', 0.65))
    regime_weight = float(settings.get('regime_weight', 0.55))
    min_multiplier = float(settings.get('min_multiplier', 0.72))
    max_multiplier = float(settings.get('max_multiplier', 1.6))

    cluster_key = str(cluster_focus.get('key', 'unavailable'))
    cluster_label = str(cluster_focus.get('label', 'Unavailable'))
    cluster_confidence = float(cluster_focus.get('confidence', 0.0))
    regime_confidence = max(0.2, min(1.0, float(regime_probability) / 100.0))

    indicator_trust: dict[str, float] = {}
    for indicator in measurements:
        cluster_multiplier = float(cluster_profiles.get(cluster_key, {}).get(indicator, 1.0))
        regime_multiplier = float(regime_profiles.get(regime_key, {}).get(indicator, 1.0))
        multiplier = 1.0
        multiplier += (cluster_multiplier - 1.0) * cluster_confidence * cluster_weight
        multiplier += (regime_multiplier - 1.0) * regime_confidence * regime_weight
        indicator_trust[indicator] = round(max(min_multiplier, min(max_multiplier, multiplier)), 2)

    sorted_trust = sorted(indicator_trust.items(), key=lambda item: item[1], reverse=True)
    boosted = [key.replace('_', ' ') for key, value in sorted_trust[:4] if value > 1.03]
    reduced = [key.replace('_', ' ') for key, value in sorted(indicator_trust.items(), key=lambda item: item[1])[:4] if value < 0.97]
    average_trust = round(sum(indicator_trust.values()) / max(1, len(indicator_trust)), 2)
    summary = (
        f"Observation weighting leans on {cluster_label} and {REGIME_LABELS.get(regime_key, regime_key.title())} signals, "
        f"with average trust multiplier {average_trust:.2f}."
    )
    return {
        'cluster_key': cluster_key,
        'cluster_label': cluster_label,
        'cluster_confidence': round(cluster_confidence, 2),
        'regime_key': regime_key,
        'regime_probability': round(float(regime_probability), 2),
        'average_trust': average_trust,
        'boosted_indicators': boosted,
        'reduced_indicators': reduced,
        'summary': summary,
        'indicator_trust': indicator_trust,
    }


def _blend_scores(
    configured_scores: dict[str, float],
    calibrated_scores: dict[str, float],
    blend_weight: float,
) -> dict[str, float]:
    return {
        regime: round(
            configured_scores[regime] * (1.0 - blend_weight) + calibrated_scores[regime] * blend_weight,
            2,
        )
        for regime in REGIME_ORDER
    }


def _derive_diagnostics(
    probability_history: list[dict[str, Any]],
    rule_regime_key: str,
    innovation_stress: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not probability_history:
        diagnostics = {
            'recent_disagreement_streak': 0,
            'dominant_regime_flips': 0,
            'max_probability_gap': 0.0,
            'latest_probability_gap': 0.0,
            'confidence_band': 'Unavailable',
            'tracking_quality': 'No aligned history',
        }
        return diagnostics, []

    disagreement_history: list[dict[str, Any]] = []
    previous_regime: str | None = None
    flips = 0
    streak = 0
    max_gap = 0.0

    for row in probability_history:
        regime_scores = {key: float(value) for key, value in row.items() if key != 'timestamp'}
        sorted_regimes = sorted(regime_scores.items(), key=lambda item: item[1], reverse=True)
        dominant_regime, dominant_probability = sorted_regimes[0]
        runner_up_probability = sorted_regimes[1][1] if len(sorted_regimes) > 1 else 0.0
        gap = round(dominant_probability - runner_up_probability, 2)
        aligned = dominant_regime == rule_regime_key
        max_gap = max(max_gap, gap)
        if previous_regime is not None and dominant_regime != previous_regime:
            flips += 1
        previous_regime = dominant_regime
        streak = streak + 1 if not aligned else 0
        disagreement_history.append(
            {
                'timestamp': row['timestamp'],
                'dominant_regime': dominant_regime,
                'dominant_probability': round(dominant_probability, 2),
                'probability_gap': gap,
                'aligned_with_rule': aligned,
            }
        )

    latest = disagreement_history[-1]
    confidence_band = 'Dominant' if latest['probability_gap'] >= 20 else 'Watch' if latest['probability_gap'] >= 10 else 'Fragile'
    if innovation_stress >= 3.0:
        tracking_quality = 'Noisy'
    elif innovation_stress >= 1.6:
        tracking_quality = 'Usable'
    else:
        tracking_quality = 'Clean'

    diagnostics = {
        'recent_disagreement_streak': streak,
        'dominant_regime_flips': flips,
        'max_probability_gap': round(max_gap, 2),
        'latest_probability_gap': latest['probability_gap'],
        'confidence_band': confidence_band,
        'tracking_quality': tracking_quality,
    }
    return diagnostics, disagreement_history[-90:]


def _fit_calibration_coefficients(
    state_keys: list[str],
    measurements: dict[str, list[float]],
    state_config: dict[str, Any],
    templates: list[Any] | None = None,
    cluster_key: str | None = None,
    cluster_confidence: float = 0.0,
) -> tuple[list[list[float]], dict[str, list[float]]]:
    templates = templates or EPISODE_TEMPLATES
    settings = state_config.get('regime_calibration', {})
    ridge = float(settings.get('ridge', 18.0))
    anchor_strength = float(settings.get('anchor_strength', 36.0))
    episode_states = [_template_state_vector(template.profile, state_keys, measurements) for template in templates]
    sample_weights = [
        _episode_weight(template, state_config) * _cluster_weight_multiplier(template, state_config, cluster_key, cluster_confidence)
        for template in templates
    ]
    coefficients = {
        regime: _fit_ridge_coefficients(
            episode_states,
            [float(template.regime_scores[regime]) for template in templates],
            ridge=ridge,
            sample_weights=sample_weights,
            anchor=_configured_regime_beta(state_config, regime),
            anchor_strength=anchor_strength,
        )
        for regime in REGIME_ORDER
    }
    return episode_states, coefficients


def _regime_rmse(scores: dict[str, float], template: Any) -> float:
    return round((
        sum((float(scores[regime]) - float(template.regime_scores[regime])) ** 2 for regime in REGIME_ORDER) / len(REGIME_ORDER)
    ) ** 0.5, 2)


def _build_validation(
    state_keys: list[str],
    measurements: dict[str, list[float]],
    state_config: dict[str, Any],
) -> dict[str, Any]:
    if len(EPISODE_TEMPLATES) < 2:
        return {
            'summary': 'Validation unavailable because the episode library is too small.',
            'configured_hit_rate': 0.0,
            'calibrated_hit_rate': 0.0,
            'iterative_hit_rate': 0.0,
            'configured_avg_rmse': 0.0,
            'calibrated_avg_rmse': 0.0,
            'iterative_avg_rmse': 0.0,
            'episodes': [],
        }

    rows: list[dict[str, Any]] = []
    configured_hits = 0
    calibrated_hits = 0
    iterative_hits = 0
    configured_rmses: list[float] = []
    calibrated_rmses: list[float] = []
    iterative_rmses: list[float] = []

    for index, template in enumerate(EPISODE_TEMPLATES):
        training = [candidate for pos, candidate in enumerate(EPISODE_TEMPLATES) if pos != index]
        heldout_cluster = infer_episode_cluster(template.profile)
        _, coefficients = _fit_calibration_coefficients(
            state_keys,
            measurements,
            state_config,
            training,
            cluster_key=heldout_cluster['key'],
            cluster_confidence=heldout_cluster['confidence'],
        )
        training_states = [_template_state_vector(candidate.profile, state_keys, measurements) for candidate in training]
        training_errors: list[float] = []
        for candidate, state_vector in zip(training, training_states):
            predicted = _predict_regime_scores_from_coefficients(state_vector, coefficients)
            training_errors.append(_regime_rmse(predicted, candidate))
        fit_rmse = round(sum(training_errors) / max(1, len(training_errors)), 2)
        _, blend_weight = _calibration_quality(fit_rmse)
        blend_weight = _capped_blend_weight(blend_weight, state_config)

        state_vector = _template_state_vector(template.profile, state_keys, measurements)
        configured_scores = _configured_regime_scores(state_vector, state_config)
        configured_probs = _softmax(configured_scores)
        calibrated_scores = _predict_regime_scores_from_coefficients(state_vector, coefficients)
        calibrated_probs = _softmax(calibrated_scores)
        iterative_scores = _blend_scores(configured_scores, calibrated_scores, blend_weight)
        iterative_probs = _softmax(iterative_scores)

        target_regime = max(REGIME_ORDER, key=lambda regime: float(template.regime_scores[regime]))
        configured_regime = _dominant_regime(configured_probs)
        calibrated_regime = _dominant_regime(calibrated_probs)
        iterative_regime = _dominant_regime(iterative_probs)
        configured_rmse = _regime_rmse(configured_scores, template)
        calibrated_rmse = _regime_rmse(calibrated_scores, template)
        iterative_rmse = _regime_rmse(iterative_scores, template)

        configured_hits += int(configured_regime == target_regime)
        calibrated_hits += int(calibrated_regime == target_regime)
        iterative_hits += int(iterative_regime == target_regime)
        configured_rmses.append(configured_rmse)
        calibrated_rmses.append(calibrated_rmse)
        iterative_rmses.append(iterative_rmse)

        winner = min(
            [('configured', configured_rmse), ('calibrated', calibrated_rmse), ('iterative', iterative_rmse)],
            key=lambda item: item[1],
        )[0]
        rows.append(
            {
                'key': template.key,
                'label': template.label,
                'period': template.period,
                'target_regime': target_regime,
                'configured_regime': configured_regime,
                'calibrated_regime': calibrated_regime,
                'iterative_regime': iterative_regime,
                'configured_rmse': configured_rmse,
                'calibrated_rmse': calibrated_rmse,
                'iterative_rmse': iterative_rmse,
                'winner': winner,
            }
        )

    total = max(1, len(rows))
    configured_hit_rate = round((configured_hits / total) * 100.0, 2)
    calibrated_hit_rate = round((calibrated_hits / total) * 100.0, 2)
    iterative_hit_rate = round((iterative_hits / total) * 100.0, 2)
    configured_avg_rmse = round(sum(configured_rmses) / total, 2)
    calibrated_avg_rmse = round(sum(calibrated_rmses) / total, 2)
    iterative_avg_rmse = round(sum(iterative_rmses) / total, 2)
    best_label = min(
        [('configured', configured_avg_rmse), ('calibrated', calibrated_avg_rmse), ('iterative', iterative_avg_rmse)],
        key=lambda item: item[1],
    )[0]
    summary = (
        f'Leave-one-out validation favors {best_label} with average RMSE {min(configured_avg_rmse, calibrated_avg_rmse, iterative_avg_rmse):.1f}. '
        f'Hit rates are configured {configured_hit_rate:.0f}%, calibrated {calibrated_hit_rate:.0f}%, iterative {iterative_hit_rate:.0f}%.'
    )

    rows.sort(key=lambda row: row['iterative_rmse'])
    return {
        'summary': summary,
        'configured_hit_rate': configured_hit_rate,
        'calibrated_hit_rate': calibrated_hit_rate,
        'iterative_hit_rate': iterative_hit_rate,
        'configured_avg_rmse': configured_avg_rmse,
        'calibrated_avg_rmse': calibrated_avg_rmse,
        'iterative_avg_rmse': iterative_avg_rmse,
        'episodes': rows,
    }


def _build_validation_trust_gate(
    validation: dict[str, Any],
    base_blend_weight: float,
    state_config: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    settings = state_config.get('regime_calibration', {}).get('validation_guardrail', {})
    min_blend = float(settings.get('min_blend_weight', 0.05))
    rmse_tolerance = float(settings.get('rmse_tolerance_ratio', 1.02))
    hit_tolerance = float(settings.get('hit_rate_tolerance', 0.0))
    floor_factor = float(settings.get('floor_factor', 0.3))

    configured_rmse = float(validation.get('configured_avg_rmse', 0.0))
    iterative_rmse = float(validation.get('iterative_avg_rmse', 0.0))
    configured_hit = float(validation.get('configured_hit_rate', 0.0))
    iterative_hit = float(validation.get('iterative_hit_rate', 0.0))

    rmse_factor = 1.0
    if configured_rmse > 0 and iterative_rmse > configured_rmse * rmse_tolerance:
        rmse_factor = max(floor_factor, (configured_rmse * rmse_tolerance) / iterative_rmse)

    hit_factor = 1.0
    if configured_hit > 0 and iterative_hit + hit_tolerance < configured_hit:
        hit_factor = max(floor_factor, (iterative_hit + hit_tolerance) / configured_hit)

    guardrail_factor = round(min(1.0, rmse_factor * hit_factor), 2)
    if base_blend_weight <= 0:
        effective_blend_weight = 0.0
    elif guardrail_factor >= 1.0:
        effective_blend_weight = round(base_blend_weight, 2)
    else:
        effective_blend_weight = round(max(min_blend, base_blend_weight * guardrail_factor), 2)

    if effective_blend_weight <= max(0.0, min_blend + 0.01):
        status = 'Tight'
    elif effective_blend_weight < base_blend_weight:
        status = 'Reduced'
    else:
        status = 'Open'

    summary = (
        f"Validation trust gate is {status.lower()}. Effective regime-calibration blend is {effective_blend_weight * 100:.0f}% "
        f"versus a base cap of {base_blend_weight * 100:.0f}% because iterative validation RMSE is {iterative_rmse:.1f} "
        f"against configured {configured_rmse:.1f}, with hit rates {iterative_hit:.0f}% versus {configured_hit:.0f}%."
    )

    return (
        {
            'status': status,
            'base_blend_weight': round(base_blend_weight, 2),
            'effective_blend_weight': round(effective_blend_weight, 2),
            'guardrail_factor': guardrail_factor,
            'configured_avg_rmse': round(configured_rmse, 2),
            'iterative_avg_rmse': round(iterative_rmse, 2),
            'configured_hit_rate': round(configured_hit, 2),
            'iterative_hit_rate': round(iterative_hit, 2),
            'summary': summary,
        },
        effective_blend_weight,
    )


def _build_probability_histories(
    state_history: list[dict[str, Any]],
    configured_scores_history: list[dict[str, float]],
    state_keys: list[str],
    coefficients: dict[str, list[float]],
    blend_weight: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    calibrated_probability_history: list[dict[str, Any]] = []
    blended_probability_history: list[dict[str, Any]] = []
    for state_row, configured_scores in zip(state_history, configured_scores_history):
        state_vector = [float(state_row[key]) for key in state_keys]
        calibrated_scores = _predict_regime_scores_from_coefficients(state_vector, coefficients)
        calibrated_probabilities = _softmax(calibrated_scores)
        blended_scores = _blend_scores(configured_scores, calibrated_scores, blend_weight)
        blended_probabilities = _softmax(blended_scores)
        timestamp = state_row['timestamp']
        calibrated_probability_history.append({'timestamp': timestamp, **calibrated_probabilities})
        blended_probability_history.append({'timestamp': timestamp, **blended_probabilities})
    return calibrated_probability_history, blended_probability_history


def _build_calibration(
    snapshots: dict[str, dict[str, Any]],
    state_keys: list[str],
    measurements: dict[str, list[float]],
    state_config: dict[str, Any],
    state_history: list[dict[str, Any]],
    configured_probability_history: list[dict[str, Any]],
    configured_scores_history: list[dict[str, float]],
    latest_state_vector: list[float],
) -> tuple[dict[str, Any], dict[str, list[float]], list[dict[str, Any]], float]:
    cluster_focus = infer_episode_cluster(extract_snapshot_profile(snapshots))
    episode_states, coefficients = _fit_calibration_coefficients(
        state_keys,
        measurements,
        state_config,
        cluster_key=cluster_focus['key'],
        cluster_confidence=cluster_focus['confidence'],
    )

    episode_rows: list[dict[str, Any]] = []
    errors: list[float] = []
    for template, episode_state in zip(EPISODE_TEMPLATES, episode_states):
        calibrated_scores = _predict_regime_scores_from_coefficients(episode_state, coefficients)
        calibrated_probabilities = _softmax(calibrated_scores)
        rmse = (
            sum((calibrated_scores[regime] - float(template.regime_scores[regime])) ** 2 for regime in REGIME_ORDER) / len(REGIME_ORDER)
        ) ** 0.5
        errors.append(rmse)
        target_regime = max(REGIME_ORDER, key=lambda regime: float(template.regime_scores[regime]))
        calibrated_regime = _dominant_regime(calibrated_probabilities)
        episode_rows.append(
            {
                'key': template.key,
                'label': template.label,
                'period': template.period,
                'target_regime': target_regime,
                'calibrated_regime': calibrated_regime,
                'fit_score': round(max(0.0, 100.0 - rmse * 5.0), 2),
                'rmse': round(rmse, 2),
                'sticky': calibrated_probabilities['sticky'],
                'convex': calibrated_probabilities['convex'],
                'break': calibrated_probabilities['break'],
            }
        )

    fit_rmse = round(sum(errors) / max(1, len(errors)), 2)
    quality, blend_weight = _calibration_quality(fit_rmse)
    blend_weight = _capped_blend_weight(blend_weight, state_config)

    calibrated_probability_history, blended_probability_history = _build_probability_histories(
        state_history,
        configured_scores_history,
        state_keys,
        coefficients,
        blend_weight,
    )

    current_calibrated_scores = _predict_regime_scores_from_coefficients(latest_state_vector, coefficients)
    current_calibrated_probabilities = _softmax(current_calibrated_scores)
    current_configured = configured_probability_history[-1]

    calibration = {
        'method': 'ridge fit on historical episode library',
        'sample_size': len(EPISODE_TEMPLATES),
        'fit_rmse': fit_rmse,
        'quality': quality,
        'blend_weight': round(blend_weight, 2),
        'base_blend_weight': round(blend_weight, 2),
        'summary': (
            f"Episode-fit calibration is {quality.lower()} with RMSE {fit_rmse:.1f} across {len(EPISODE_TEMPLATES)} historical stress windows. "
            f"Calibrated loadings contribute up to {blend_weight * 100:.0f}% of the live econometric regime score before validation trust gating."
        ),
        'configured_regime': _dominant_regime({key: float(current_configured[key]) for key in REGIME_ORDER}),
        'configured_probability': round(max(float(current_configured[key]) for key in REGIME_ORDER), 2),
        'calibrated_regime': _dominant_regime(current_calibrated_probabilities),
        'calibrated_probability': round(max(float(current_calibrated_probabilities[key]) for key in REGIME_ORDER), 2),
        'configured_probability_history': configured_probability_history[-90:],
        'calibrated_probability_history': calibrated_probability_history[-90:],
        'episodes': sorted(episode_rows, key=lambda row: row['fit_score'], reverse=True),
        'cluster_focus': {
            'key': cluster_focus['key'],
            'label': cluster_focus['label'],
            'confidence': cluster_focus['confidence'],
            'summary': cluster_focus['summary'],
            'supporting_episodes': cluster_focus['supporting_episodes'],
        },
        'trust_gate': {
            'status': 'Open',
            'base_blend_weight': round(blend_weight, 2),
            'effective_blend_weight': round(blend_weight, 2),
            'guardrail_factor': 1.0,
            'configured_avg_rmse': 0.0,
            'iterative_avg_rmse': 0.0,
            'configured_hit_rate': 0.0,
            'iterative_hit_rate': 0.0,
            'summary': f'Validation trust gate is open. Effective regime-calibration blend remains {blend_weight * 100:.0f}%.',
        },
    }

    return calibration, coefficients, blended_probability_history, blend_weight


def _run_filter(
    timestamps: list[datetime],
    observations_by_time: list[dict[str, float]],
    state_keys: list[str],
    transition: list[list[float]],
    transition_intercepts: list[float] | None,
    process_noise_values: list[float],
    initial_state: list[float],
    initial_covariance: list[float],
    measurement_noise_floor: float,
    measurements: dict[str, list[float]],
    state_config: dict[str, Any],
    observation_trust: dict[str, float] | None = None,
) -> dict[str, Any]:
    state = [float(value) for value in initial_state]
    covariance = _diag([float(value) for value in initial_covariance])
    process_noise = _diag([float(value) for value in process_noise_values])
    latest_measurements: dict[str, float] = {}
    latest_measurement_timestamp = timestamps[-1]
    state_history: list[dict[str, Any]] = []
    configured_scores_history: list[dict[str, float]] = []
    configured_probability_history: list[dict[str, Any]] = []
    innovations: list[float] = []

    for timestamp, observations in zip(timestamps, observations_by_time):
        state = _mat_vec_mul(transition, state)
        if transition_intercepts:
            state = [clamp(state[index] + float(transition_intercepts[index])) for index in range(len(state_keys))]
        covariance = _mat_mul(_mat_mul(transition, covariance), _transpose(transition))
        covariance = [
            [covariance[row][col] + process_noise[row][col] for col in range(len(state_keys))]
            for row in range(len(state_keys))
        ]

        for indicator, observed_value in observations.items():
            loading = measurements.get(indicator)
            if not loading:
                continue
            predicted_value = sum(loading[index] * state[index] for index in range(len(state_keys)))
            innovation = observed_value - predicted_value
            projected_variance = sum(
                loading[row] * covariance[row][col] * loading[col]
                for row in range(len(state_keys))
                for col in range(len(state_keys))
            )
            trust_multiplier = float((observation_trust or {}).get(indicator, 1.0))
            measurement_noise = measurement_noise_floor / max(0.55, trust_multiplier)
            innovation_variance = projected_variance + measurement_noise
            if innovation_variance <= 0:
                continue
            kalman_gain = [
                sum(covariance[row][col] * loading[col] for col in range(len(state_keys))) / innovation_variance
                for row in range(len(state_keys))
            ]
            state = [clamp(state[index] + kalman_gain[index] * innovation) for index in range(len(state_keys))]
            updated_covariance: list[list[float]] = []
            for row in range(len(state_keys)):
                updated_row: list[float] = []
                for col in range(len(state_keys)):
                    reduction = kalman_gain[row] * sum(loading[idx] * covariance[idx][col] for idx in range(len(state_keys)))
                    updated_row.append(max(0.0, covariance[row][col] - reduction))
                updated_covariance.append(updated_row)
            covariance = updated_covariance
            innovations.append(abs(innovation) / max(10.0, innovation_variance ** 0.5))
            if timestamp == latest_measurement_timestamp:
                latest_measurements[indicator] = observed_value

        state_scores = _state_scores(state, state_keys)
        configured_scores = _configured_regime_scores(state, state_config)
        configured_probabilities = _softmax(configured_scores)
        state_history.append({'timestamp': timestamp, **state_scores})
        configured_scores_history.append(configured_scores)
        configured_probability_history.append({'timestamp': timestamp, **configured_probabilities})

    return {
        'state_history': state_history,
        'configured_scores_history': configured_scores_history,
        'configured_probability_history': configured_probability_history,
        'innovations': innovations,
        'latest_measurements': latest_measurements,
        'latest_measurement_timestamp': latest_measurement_timestamp,
        'covariance': covariance,
        'observation_trust': observation_trust or {},
    }


def _relative_delta(left: float, right: float, scale_floor: float) -> float:
    baseline = max(scale_floor, abs(float(left)), abs(float(right)))
    return abs(float(left) - float(right)) / baseline


def _avg_abs_matrix_delta(left: list[list[float]], right: list[list[float]], scale_floor: float = 0.1) -> float:
    values = [
        _relative_delta(float(left[row][col]), float(right[row][col]), scale_floor)
        for row in range(len(left))
        for col in range(len(left[row]))
    ]
    return round(sum(values) / max(1, len(values)), 4)


def _avg_abs_vector_delta(left: list[float], right: list[float], scale_floor: float = 1.0) -> float:
    values = [_relative_delta(float(left[index]), float(right[index]), scale_floor) for index in range(len(left))]
    return round(sum(values) / max(1, len(values)), 4)


def _avg_abs_measurement_delta(left: dict[str, list[float]], right: dict[str, list[float]], scale_floor: float = 0.1) -> float:
    values: list[float] = []
    for key in left:
        values.extend(_relative_delta(float(left[key][index]), float(right[key][index]), scale_floor) for index in range(len(left[key])))
    return round(sum(values) / max(1, len(values)), 4)


def _blend_scalar(current: float, proposed: float, relaxation: float, anchor: float, anchor_weight: float) -> float:
    blended = float(current) * (1.0 - relaxation) + float(proposed) * relaxation
    return blended * (1.0 - anchor_weight) + float(anchor) * anchor_weight


def _blend_vector(current: list[float], proposed: list[float], relaxation: float, anchor: list[float], anchor_weight: float) -> list[float]:
    return [
        round(_blend_scalar(current[index], proposed[index], relaxation, anchor[index], anchor_weight), 4)
        for index in range(len(current))
    ]


def _blend_matrix(
    current: list[list[float]],
    proposed: list[list[float]],
    relaxation: float,
    anchor: list[list[float]],
    anchor_weight: float,
) -> list[list[float]]:
    return [
        [round(_blend_scalar(current[row][col], proposed[row][col], relaxation, anchor[row][col], anchor_weight), 4) for col in range(len(current[row]))]
        for row in range(len(current))
    ]


def _blend_measurements(
    current: dict[str, list[float]],
    proposed: dict[str, list[float]],
    relaxation: float,
    anchor: dict[str, list[float]],
    anchor_weight: float,
) -> dict[str, list[float]]:
    return {
        key: [
            round(_blend_scalar(current[key][index], proposed[key][index], relaxation, anchor[key][index], anchor_weight), 4)
            for index in range(len(current[key]))
        ]
        for key in current
    }


def _iterate_estimation(
    timestamps: list[datetime],
    observations_by_time: list[dict[str, float]],
    state_keys: list[str],
    state_config: dict[str, Any],
    configured_transition: list[list[float]],
    configured_process_noise: list[float],
    initial_state: list[float],
    initial_covariance: list[float],
    configured_measurement_noise_floor: float,
    configured_measurements: dict[str, list[float]],
) -> dict[str, Any]:
    settings = state_config.get('iterative_estimation', {})
    max_iterations = int(settings.get('max_iterations', 4))
    tolerance = float(settings.get('tolerance', 0.08))
    relaxation = float(settings.get('relaxation', 0.35))
    noise_relaxation = float(settings.get('noise_relaxation', 0.25))
    anchor_weight = float(settings.get('anchor_weight', 0.18))
    intercept_scale = float(settings.get('intercept_scale', 0.5))
    worsening_backoff = float(settings.get('worsening_backoff', 0.6))

    current_transition = [[float(cell) for cell in row] for row in configured_transition]
    current_intercepts = [0.0 for _ in state_keys]
    current_measurements = {key: [float(value) for value in weights] for key, weights in configured_measurements.items()}
    current_process_noise = [float(value) for value in configured_process_noise]
    current_noise_floor = float(configured_measurement_noise_floor)
    path: list[dict[str, Any]] = []
    converged = False
    last_transition_overview = {
        'fit_rmse': 0.0,
        'quality': 'Unavailable',
        'blend_weight': 0.0,
        'summary': 'Transition fit unavailable.',
        'configured_persistence': 0.0,
        'fitted_persistence': 0.0,
        'blended_persistence': 0.0,
        'drift_strength': 0.0,
        'links': [],
    }
    last_filter_overview = {
        'fit_rmse': 0.0,
        'quality': 'Unavailable',
        'blend_weight': 0.0,
        'summary': 'Filter fit unavailable.',
        'configured_noise_floor': 0.0,
        'fitted_noise_floor': 0.0,
        'blended_noise_floor': 0.0,
        'configured_process_noise': 0.0,
        'fitted_process_noise': 0.0,
        'blended_process_noise': 0.0,
        'observations': [],
    }

    for iteration in range(1, max_iterations + 1):
        pass_result = _run_filter(
            timestamps,
            observations_by_time,
            state_keys,
            current_transition,
            current_intercepts,
            current_process_noise,
            initial_state,
            initial_covariance,
            current_noise_floor,
            current_measurements,
            state_config,
        )

        latest_probabilities = pass_result['configured_probability_history'][-1]
        dominant_regime = _dominant_regime({key: float(latest_probabilities[key]) for key in REGIME_ORDER})
        dominant_probability = round(float(latest_probabilities[dominant_regime]), 2)

        transition_overview, next_transition, next_intercepts = fit_transition_calibration(
            pass_result['state_history'],
            state_keys,
            configured_transition,
        )
        filter_overview, next_measurements, next_process_noise, next_noise_floor = fit_filter_calibration(
            pass_result['state_history'],
            observations_by_time,
            state_keys,
            configured_measurements,
            configured_process_noise,
            configured_measurement_noise_floor,
            next_transition,
            next_intercepts,
        )

        proposed_intercepts = [round(float(value) * intercept_scale, 4) for value in next_intercepts]
        applied_relaxation = relaxation
        applied_noise_relaxation = noise_relaxation

        candidate_transition = _blend_matrix(
            current_transition,
            next_transition,
            applied_relaxation,
            configured_transition,
            anchor_weight,
        )
        candidate_intercepts = _blend_vector(
            current_intercepts,
            proposed_intercepts,
            applied_relaxation,
            [0.0 for _ in state_keys],
            anchor_weight,
        )
        candidate_measurements = _blend_measurements(
            current_measurements,
            next_measurements,
            applied_relaxation,
            configured_measurements,
            anchor_weight,
        )
        candidate_process_noise = _blend_vector(
            current_process_noise,
            next_process_noise,
            applied_noise_relaxation,
            configured_process_noise,
            anchor_weight,
        )
        candidate_noise_floor = round(
            _blend_scalar(
                current_noise_floor,
                next_noise_floor,
                applied_noise_relaxation,
                configured_measurement_noise_floor,
                anchor_weight,
            ),
            4,
        )

        parameter_delta = round((
            _avg_abs_matrix_delta(current_transition, candidate_transition, 0.1)
            + _avg_abs_vector_delta(current_intercepts, candidate_intercepts, 0.5)
            + _avg_abs_measurement_delta(current_measurements, candidate_measurements, 0.1)
            + _avg_abs_vector_delta(current_process_noise, candidate_process_noise, 1.0)
            + _relative_delta(current_noise_floor, candidate_noise_floor, 1.0)
        ) / 5.0, 4)

        if path and parameter_delta > float(path[-1]['parameter_delta']) * 0.98:
            applied_relaxation *= worsening_backoff
            applied_noise_relaxation *= worsening_backoff
            candidate_transition = _blend_matrix(
                current_transition,
                next_transition,
                applied_relaxation,
                configured_transition,
                anchor_weight,
            )
            candidate_intercepts = _blend_vector(
                current_intercepts,
                proposed_intercepts,
                applied_relaxation,
                [0.0 for _ in state_keys],
                anchor_weight,
            )
            candidate_measurements = _blend_measurements(
                current_measurements,
                next_measurements,
                applied_relaxation,
                configured_measurements,
                anchor_weight,
            )
            candidate_process_noise = _blend_vector(
                current_process_noise,
                next_process_noise,
                applied_noise_relaxation,
                configured_process_noise,
                anchor_weight,
            )
            candidate_noise_floor = round(
                _blend_scalar(
                    current_noise_floor,
                    next_noise_floor,
                    applied_noise_relaxation,
                    configured_measurement_noise_floor,
                    anchor_weight,
                ),
                4,
            )
            parameter_delta = round((
                _avg_abs_matrix_delta(current_transition, candidate_transition, 0.1)
                + _avg_abs_vector_delta(current_intercepts, candidate_intercepts, 0.5)
                + _avg_abs_measurement_delta(current_measurements, candidate_measurements, 0.1)
                + _avg_abs_vector_delta(current_process_noise, candidate_process_noise, 1.0)
                + _relative_delta(current_noise_floor, candidate_noise_floor, 1.0)
            ) / 5.0, 4)

        path.append(
            {
                'iteration': iteration,
                'transition_rmse': round(float(transition_overview['fit_rmse']), 2),
                'filter_rmse': round(float(filter_overview['fit_rmse']), 2),
                'parameter_delta': parameter_delta,
                'dominant_regime': dominant_regime,
                'dominant_probability': dominant_probability,
                'transition_quality': transition_overview['quality'],
                'filter_quality': filter_overview['quality'],
            }
        )

        current_transition = candidate_transition
        current_intercepts = candidate_intercepts
        current_measurements = candidate_measurements
        current_process_noise = candidate_process_noise
        current_noise_floor = candidate_noise_floor
        last_transition_overview = transition_overview
        last_filter_overview = filter_overview

        if parameter_delta <= tolerance:
            converged = True
            break

    final_pass = _run_filter(
        timestamps,
        observations_by_time,
        state_keys,
        current_transition,
        current_intercepts,
        current_process_noise,
        initial_state,
        initial_covariance,
        current_noise_floor,
        current_measurements,
        state_config,
    )

    final_parameter_delta = float(path[-1]['parameter_delta']) if path else 0.0
    iteration_overview = {
        'iterations_run': len(path),
        'max_iterations': max_iterations,
        'tolerance': round(tolerance, 4),
        'converged': converged,
        'final_parameter_delta': round(final_parameter_delta, 4),
        'summary': (
            f"Iterative estimation {'converged' if converged else 'stopped at max iterations'} after {len(path)} passes. "
            f"Final parameter delta is {final_parameter_delta:.4f} versus tolerance {tolerance:.4f}."
        ),
        'path': path,
    }

    return {
        'final_pass': final_pass,
        'transition': current_transition,
        'transition_intercepts': current_intercepts,
        'measurements': current_measurements,
        'process_noise': current_process_noise,
        'noise_floor': current_noise_floor,
        'transition_overview': last_transition_overview,
        'filter_overview': last_filter_overview,
        'iteration_overview': iteration_overview,
    }


def _project_probabilities(
    start_state: list[float],
    transition: list[list[float]],
    transition_intercepts: list[float] | None,
    state_config: dict[str, Any],
    latest_timestamp: datetime,
    calibration_coefficients: dict[str, list[float]] | None,
    blend_weight: float,
    impulse: list[float] | None = None,
    steps: int = 10,
    decay: float = 0.72,
) -> list[dict[str, Any]]:
    state = [float(value) for value in start_state]
    path: list[dict[str, Any]] = []
    impulse_vector = impulse or [0.0 for _ in state]

    for step in range(1, steps + 1):
        state = _mat_vec_mul(transition, state)
        if transition_intercepts:
            state = [clamp(state[index] + float(transition_intercepts[index])) for index in range(len(state))]
        if impulse is not None:
            applied = [impulse_vector[index] * (decay ** (step - 1)) for index in range(len(state))]
            state = [clamp(state[index] + applied[index]) for index in range(len(state))]
        configured_scores = _configured_regime_scores(state, state_config)
        if calibration_coefficients:
            comparison_scores = _predict_regime_scores_from_coefficients(state, calibration_coefficients)
            output_scores = _blend_scores(configured_scores, comparison_scores, blend_weight)
        else:
            output_scores = configured_scores
        probabilities = _softmax(output_scores)
        path.append(
            {
                'step': step,
                'timestamp': latest_timestamp + timedelta(days=step),
                **probabilities,
            }
        )
    return path


def _build_forecast(
    state: list[float],
    transition: list[list[float]],
    transition_intercepts: list[float] | None,
    state_config: dict[str, Any],
    latest_timestamp: datetime,
    calibration_coefficients: dict[str, list[float]] | None,
    blend_weight: float,
    state_keys: list[str],
    cluster_focus: dict[str, Any],
) -> dict[str, Any]:
    conditioning_cluster = str(cluster_focus.get('key', 'unavailable'))
    conditioning_label = str(cluster_focus.get('label', 'Unavailable'))
    conditioning_confidence = float(cluster_focus.get('confidence', 0.0))
    conditioned_transition, conditioned_intercepts, scenario_bias, conditioning_summary = _condition_forecast_dynamics(
        transition,
        transition_intercepts,
        conditioning_cluster,
        conditioning_confidence,
    )
    baseline_path = _project_probabilities(
        state,
        conditioned_transition,
        conditioned_intercepts,
        state_config,
        latest_timestamp,
        calibration_coefficients,
        blend_weight,
    )
    horizons: list[dict[str, Any]] = []
    for day in (1, 5, 10):
        row = baseline_path[day - 1]
        dominant_regime = _dominant_regime({key: float(row[key]) for key in REGIME_ORDER})
        horizons.append(
            {
                'days': day,
                'dominant_regime': dominant_regime,
                'dominant_probability': round(float(row[dominant_regime]), 2),
                'sticky': round(float(row['sticky']), 2),
                'convex': round(float(row['convex']), 2),
                'break': round(float(row['break']), 2),
            }
        )

    scenarios: list[dict[str, Any]] = []
    for scenario in SCENARIO_LIBRARY:
        bias = float(scenario_bias.get(scenario['key'], 1.0))
        scenario_impulse = [round(float(value) * bias, 2) for value in scenario['impulse'][: len(state_keys)]]
        scenario_path = _project_probabilities(
            state,
            conditioned_transition,
            conditioned_intercepts,
            state_config,
            latest_timestamp,
            calibration_coefficients,
            blend_weight,
            impulse=scenario_impulse,
            steps=5,
        )
        terminal = scenario_path[-1]
        dominant_regime = _dominant_regime({key: float(terminal[key]) for key in REGIME_ORDER})
        impulse_summary = ', '.join(
            f"{STATE_LABELS.get(state_keys[index], state_keys[index])} +{scenario_impulse[index]:.0f}"
            for index in range(min(len(state_keys), len(scenario_impulse)))
            if scenario_impulse[index] > 0
        )
        scenarios.append(
            {
                'key': scenario['key'],
                'label': scenario['label'],
                'description': scenario['description'],
                'dominant_regime': dominant_regime,
                'dominant_probability': round(float(terminal[dominant_regime]), 2),
                'sticky': round(float(terminal['sticky']), 2),
                'convex': round(float(terminal['convex']), 2),
                'break': round(float(terminal['break']), 2),
                'state_impulse_summary': impulse_summary,
            }
        )

    scenarios.sort(key=lambda row: (row['break'], row['convex'], row['dominant_probability']), reverse=True)
    baseline_terminal = horizons[-1]
    baseline_label = REGIME_LABELS.get(baseline_terminal['dominant_regime'], baseline_terminal['dominant_regime'].title())
    summary = (
        f"{conditioning_label} conditioning is active at {conditioning_confidence * 100:.0f}% confidence. "
        f"Baseline 10-day path keeps {baseline_label} as the lead regime at {baseline_terminal['dominant_probability']:.1f}% relative confidence. "
        f"Largest stressed-scenario break signal comes from {scenarios[0]['label']} at {scenarios[0]['break']:.1f}% break confidence."
        if scenarios
        else f"{conditioning_label} conditioning is active at {conditioning_confidence * 100:.0f}% confidence. Baseline 10-day path keeps {baseline_label} as the lead regime at {baseline_terminal['dominant_probability']:.1f}% relative confidence."
    )
    return {
        'summary': summary,
        'conditioning_cluster': conditioning_cluster,
        'conditioning_label': conditioning_label,
        'conditioning_confidence': round(conditioning_confidence, 2),
        'conditioning_summary': conditioning_summary,
        'baseline_path': baseline_path,
        'horizons': horizons,
        'scenarios': scenarios,
    }


def evaluate_state_space(
    snapshots: dict[str, dict[str, Any]],
    config: dict[str, Any],
    rule_regime: str,
) -> dict[str, Any]:
    state_config = config.get('state_space') or {}
    state_keys = list(state_config.get('states', []))
    measurements = {key: [float(value) for value in weights] for key, weights in state_config.get('measurements', {}).items()}
    if not state_keys or not measurements:
        return {}

    timestamps, measurement_histories = _build_measurement_histories(snapshots, config['thresholds'], measurements)
    if not timestamps:
        return _empty_state_space(rule_regime, 'Latent-state layer unavailable because no aligned measurement history was found.')

    observations_by_time = _carry_forward_observations(timestamps, measurement_histories)
    configured_transition = [[float(cell) for cell in row] for row in state_config['transition_matrix']]
    configured_process_noise = [float(value) for value in state_config['process_noise']]
    initial_state = [float(value) for value in state_config['initial_state']]
    initial_covariance = [float(value) for value in state_config['initial_covariance']]
    measurement_noise_floor = float(state_config.get('measurement_noise_floor', 25.0))
    cluster_focus = infer_episode_cluster(extract_snapshot_profile(snapshots))
    initial_pass = _run_filter(
        timestamps,
        observations_by_time,
        state_keys,
        configured_transition,
        None,
        configured_process_noise,
        initial_state,
        initial_covariance,
        measurement_noise_floor,
        measurements,
        state_config,
    )
    initial_probabilities = initial_pass['configured_probability_history'][-1]
    initial_regime = _dominant_regime({key: float(initial_probabilities[key]) for key in REGIME_ORDER})
    initial_probability = round(float(initial_probabilities[initial_regime]), 2)
    observation_context = _build_observation_context(
        measurements,
        state_config,
        cluster_focus,
        initial_regime,
        initial_probability,
    )
    conditioned_pass = _run_filter(
        timestamps,
        observations_by_time,
        state_keys,
        configured_transition,
        None,
        configured_process_noise,
        initial_state,
        initial_covariance,
        measurement_noise_floor,
        measurements,
        state_config,
        observation_trust=observation_context['indicator_trust'],
    )
    state_history = conditioned_pass['state_history']
    configured_scores_history = conditioned_pass['configured_scores_history']
    probability_history = conditioned_pass['configured_probability_history']
    innovations = conditioned_pass['innovations']
    latest_measurements = conditioned_pass['latest_measurements']
    latest_measurement_timestamp = conditioned_pass['latest_measurement_timestamp']
    covariance = conditioned_pass['covariance']
    latest_states = state_history[-1]

    previous_index = max(0, len(state_history) - 8)
    prior_states = state_history[previous_index]
    current_probabilities = probability_history[-1]
    current_regime = _dominant_regime({key: float(current_probabilities[key]) for key in REGIME_ORDER})
    current_probability = round(float(current_probabilities[current_regime]), 2)
    rule_key = 'break' if rule_regime.lower().startswith('break') else rule_regime.lower().split()[0]
    rule_agreement = current_regime == rule_key
    top_measurements = sorted(latest_measurements.items(), key=lambda item: abs(item[1] - 50.0), reverse=True)
    innovation_stress = round(sum(innovations[-10:]) / max(1, len(innovations[-10:])), 2)

    state_cards: list[dict[str, Any]] = []
    for state_key in state_keys:
        state_index = state_keys.index(state_key)
        dominant_measurements = [
            indicator.replace('_', ' ')
            for indicator, _ in top_measurements
            if abs(measurements.get(indicator, [0.0] * len(state_keys))[state_index]) >= 0.4
        ][:3]
        uncertainty = round(covariance[state_index][state_index] ** 0.5, 2)
        state_cards.append(
            {
                'key': state_key,
                'label': STATE_LABELS.get(state_key, state_key.replace('_', ' ').title()),
                'value': latest_states[state_key],
                'change_7d': round(latest_states[state_key] - prior_states[state_key], 2),
                'uncertainty': uncertainty,
                'dominant_measurements': dominant_measurements or ['No dominant measurement'],
            }
        )

    configured_current = probability_history[-1]
    configured_regime = current_regime
    diagnostics, disagreement_history = _derive_diagnostics(probability_history, rule_key, innovation_stress)
    agreement_summary = (
        f"Configured latent-state layer agrees with the rule engine on {REGIME_LABELS.get(current_regime, current_regime.title())} stress."
        if rule_agreement
        else f"Configured latent-state layer leans {REGIME_LABELS.get(current_regime, current_regime.title())} while the rule engine remains {rule_regime}."
    )

    forecast = _build_forecast(
        [float(state_history[-1][key]) for key in state_keys],
        configured_transition,
        None,
        state_config,
        latest_measurement_timestamp,
        None,
        0.0,
        state_keys,
        cluster_focus,
    )
    configured_persistence = round(
        sum(configured_transition[index][index] for index in range(len(state_keys))) / max(1, len(state_keys)),
        2,
    )
    calibration = {
        'method': 'configured latent-state monitor',
        'sample_size': len(EPISODE_TEMPLATES),
        'fit_rmse': 0.0,
        'quality': 'Configured',
        'blend_weight': 0.0,
        'base_blend_weight': 0.0,
        'summary': 'Live scoring uses the configured latent-state filter only. Historical episode templates remain descriptive and are not used to fit or blend live scores.',
        'configured_regime': configured_regime,
        'configured_probability': current_probability,
        'calibrated_regime': configured_regime,
        'calibrated_probability': current_probability,
        'configured_probability_history': probability_history[-90:],
        'calibrated_probability_history': probability_history[-90:],
        'episodes': [],
        'cluster_focus': {
            'key': cluster_focus['key'],
            'label': cluster_focus['label'],
            'confidence': round(float(cluster_focus['confidence']), 2),
            'summary': f"Nearest historical subfamily is {cluster_focus['label']}. This is descriptive context, not a fitted calibration.",
            'supporting_episodes': [template.label for template in EPISODE_TEMPLATES if template.cluster == cluster_focus['key']][:4],
        },
        'trust_gate': {
            'status': 'Disabled',
            'base_blend_weight': 0.0,
            'effective_blend_weight': 0.0,
            'guardrail_factor': 0.0,
            'configured_avg_rmse': 0.0,
            'iterative_avg_rmse': 0.0,
            'configured_hit_rate': 0.0,
            'iterative_hit_rate': 0.0,
            'summary': 'Validation trust gating is disabled because live scoring does not use fitted calibration weights.',
        },
        'transition': {
            'fit_rmse': 0.0,
            'quality': 'Configured',
            'blend_weight': 0.0,
            'summary': 'Live scoring uses the configured transition matrix only; no fitted transition weights are applied.',
            'configured_persistence': configured_persistence,
            'fitted_persistence': configured_persistence,
            'blended_persistence': configured_persistence,
            'drift_strength': 0.0,
            'links': [],
        },
        'filter': {
            'fit_rmse': 0.0,
            'quality': 'Configured',
            'blend_weight': 0.0,
            'summary': 'Live scoring uses the configured observation model with trust-based noise adjustment only; no fitted observation loadings are applied.',
            'configured_noise_floor': round(measurement_noise_floor, 2),
            'fitted_noise_floor': round(measurement_noise_floor, 2),
            'blended_noise_floor': round(measurement_noise_floor, 2),
            'configured_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
            'fitted_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
            'blended_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
            'observations': [],
            'observation_conditioning': {
                'cluster_key': observation_context['cluster_key'],
                'cluster_label': observation_context['cluster_label'],
                'cluster_confidence': observation_context['cluster_confidence'],
                'regime_key': observation_context['regime_key'],
                'regime_probability': observation_context['regime_probability'],
                'average_trust': observation_context['average_trust'],
                'boosted_indicators': observation_context['boosted_indicators'],
                'reduced_indicators': observation_context['reduced_indicators'],
                'summary': observation_context['summary'],
            },
        },
        'iteration': {
            'iterations_run': 0,
            'max_iterations': 0,
            'tolerance': 0.0,
            'converged': False,
            'final_parameter_delta': 0.0,
            'summary': 'Iterative estimation is disabled in the live configured latent-state monitor.',
            'path': [],
        },
        'validation': {
            'summary': 'Historical episode validation is descriptive only and is not used to fit or blend the live latent-state scores.',
            'configured_hit_rate': 0.0,
            'calibrated_hit_rate': 0.0,
            'iterative_hit_rate': 0.0,
            'configured_avg_rmse': 0.0,
            'calibrated_avg_rmse': 0.0,
            'iterative_avg_rmse': 0.0,
            'episodes': [],
        },
    }

    return {
        'current_regime': current_regime,
        'current_probability': current_probability,
        'rule_agreement': rule_agreement,
        'agreement_summary': agreement_summary,
        'observation_coverage': round((len(latest_measurements) / max(1, len(measurements))) * 100.0, 2),
        'innovation_stress': innovation_stress,
        'states': state_cards,
        'state_history': state_history[-90:],
        'probability_history': probability_history[-90:],
        'diagnostics': diagnostics,
        'disagreement_history': disagreement_history,
        'forecast': forecast,
        'calibration': calibration,
    }
