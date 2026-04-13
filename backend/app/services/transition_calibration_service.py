from __future__ import annotations

from math import sqrt
from typing import Any

from app.services.linalg_utils import _fit_ridge_coefficients, _mat_mul, _transpose


def _fit_quality(fit_rmse: float) -> tuple[str, float]:
    if fit_rmse <= 4.0:
        return 'Strong', 0.7
    if fit_rmse <= 7.0:
        return 'Usable', 0.5
    return 'Fragile', 0.25


def fit_transition_calibration(
    state_history: list[dict[str, Any]],
    state_keys: list[str],
    configured_transition: list[list[float]],
) -> tuple[dict[str, Any], list[list[float]], list[float]]:
    if len(state_history) < 4:
        zeros = [0.0 for _ in state_keys]
        return {
            'fit_rmse': 0.0,
            'quality': 'Unavailable',
            'blend_weight': 0.0,
            'summary': 'Transition fit unavailable because there is not enough latent-state history.',
            'configured_persistence': round(sum(configured_transition[i][i] for i in range(len(state_keys))) / max(1, len(state_keys)), 3),
            'fitted_persistence': 0.0,
            'blended_persistence': 0.0,
            'drift_strength': 0.0,
            'links': [],
        }, configured_transition, zeros

    inputs = [[float(row[key]) for key in state_keys] for row in state_history[:-1]]
    targets_by_state = {
        key: [float(row[key]) for row in state_history[1:]]
        for key in state_keys
    }

    intercepts: list[float] = []
    fitted_transition: list[list[float]] = []
    errors: list[float] = []
    for state_key in state_keys:
        beta = _fit_ridge_coefficients(inputs, targets_by_state[state_key])
        intercept = float(beta[0])
        weights = [float(value) for value in beta[1:]]
        intercepts.append(intercept)
        fitted_transition.append(weights)
        for row, target in zip(inputs, targets_by_state[state_key]):
            prediction = intercept + sum(weights[col] * row[col] for col in range(len(weights)))
            errors.append((prediction - target) ** 2)

    fit_rmse = round(sqrt(sum(errors) / max(1, len(errors))), 2)
    quality, blend_weight = _fit_quality(fit_rmse)
    blended_transition = [
        [
            round(configured_transition[row][col] * (1.0 - blend_weight) + fitted_transition[row][col] * blend_weight, 4)
            for col in range(len(state_keys))
        ]
        for row in range(len(state_keys))
    ]
    blended_intercepts = [round(intercept * blend_weight, 4) for intercept in intercepts]

    links: list[dict[str, Any]] = []
    for row in range(len(state_keys)):
        for col in range(len(state_keys)):
            if row == col:
                continue
            links.append(
                {
                    'source': state_keys[col],
                    'target': state_keys[row],
                    'configured_weight': round(float(configured_transition[row][col]), 3),
                    'fitted_weight': round(float(fitted_transition[row][col]), 3),
                    'blended_weight': round(float(blended_transition[row][col]), 3),
                    'delta': round(float(fitted_transition[row][col] - configured_transition[row][col]), 3),
                }
            )
    links.sort(key=lambda item: abs(item['delta']), reverse=True)

    configured_persistence = round(sum(configured_transition[i][i] for i in range(len(state_keys))) / len(state_keys), 3)
    fitted_persistence = round(sum(fitted_transition[i][i] for i in range(len(state_keys))) / len(state_keys), 3)
    blended_persistence = round(sum(blended_transition[i][i] for i in range(len(state_keys))) / len(state_keys), 3)
    drift_strength = round(sum(abs(value) for value in blended_intercepts) / len(blended_intercepts), 3)

    overview = {
        'fit_rmse': fit_rmse,
        'quality': quality,
        'blend_weight': round(blend_weight, 2),
        'summary': (
            f'Transition fit is {quality.lower()} with one-step latent-state RMSE {fit_rmse:.1f}. '
            f'Blended transition persistence is {blended_persistence:.2f}, versus configured {configured_persistence:.2f}.'
        ),
        'configured_persistence': configured_persistence,
        'fitted_persistence': fitted_persistence,
        'blended_persistence': blended_persistence,
        'drift_strength': drift_strength,
        'links': links[:6],
    }
    return overview, blended_transition, blended_intercepts
