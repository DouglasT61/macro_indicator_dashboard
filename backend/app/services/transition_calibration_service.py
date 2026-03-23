from __future__ import annotations

from math import sqrt
from typing import Any


def _transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def _mat_mul(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    rows = len(left)
    cols = len(right[0])
    inner = len(right)
    return [
        [sum(left[row][idx] * right[idx][col] for idx in range(inner)) for col in range(cols)]
        for row in range(rows)
    ]


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


def _fit_ridge_coefficients(inputs: list[list[float]], targets: list[float], ridge: float = 18.0) -> list[float]:
    design = [[1.0, *row] for row in inputs]
    design_t = _transpose(design)
    xtx = _mat_mul(design_t, design)
    for index in range(len(xtx)):
        xtx[index][index] += ridge if index > 0 else ridge * 0.1
    xty = [sum(design_t[row][col] * targets[col] for col in range(len(targets))) for row in range(len(design_t))]
    return _solve_linear_system(xtx, xty)


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
