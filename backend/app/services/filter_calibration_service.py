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


def _fit_ridge_coefficients(inputs: list[list[float]], targets: list[float], ridge: float = 14.0) -> list[float]:
    design = [[1.0, *row] for row in inputs]
    design_t = _transpose(design)
    xtx = _mat_mul(design_t, design)
    for index in range(len(xtx)):
        xtx[index][index] += ridge if index > 0 else ridge * 0.1
    xty = [sum(design_t[row][col] * targets[col] for col in range(len(targets))) for row in range(len(design_t))]
    return _solve_linear_system(xtx, xty)


def _quality_from_rmse(fit_rmse: float) -> tuple[str, float]:
    if fit_rmse <= 6.0:
        return 'Strong', 0.7
    if fit_rmse <= 11.0:
        return 'Usable', 0.45
    return 'Fragile', 0.2


def fit_filter_calibration(
    state_history: list[dict[str, Any]],
    observations_by_time: list[dict[str, float]],
    state_keys: list[str],
    configured_measurements: dict[str, list[float]],
    configured_process_noise: list[float],
    configured_measurement_noise_floor: float,
    transition: list[list[float]],
    transition_intercepts: list[float],
) -> tuple[dict[str, Any], dict[str, list[float]], list[float], float]:
    if len(state_history) < 5 or not observations_by_time:
        return {
            'fit_rmse': 0.0,
            'quality': 'Unavailable',
            'blend_weight': 0.0,
            'summary': 'Filter calibration unavailable because there is not enough aligned history.',
            'configured_noise_floor': round(configured_measurement_noise_floor, 2),
            'fitted_noise_floor': 0.0,
            'blended_noise_floor': round(configured_measurement_noise_floor, 2),
            'configured_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
            'fitted_process_noise': 0.0,
            'blended_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
            'observations': [],
        }, configured_measurements, configured_process_noise, configured_measurement_noise_floor

    state_vectors = [[float(row[key]) for key in state_keys] for row in state_history]

    fitted_measurements: dict[str, list[float]] = {}
    observation_rows: list[dict[str, Any]] = []
    rmses: list[float] = []
    residual_variances: list[float] = []

    for indicator, configured_weights in configured_measurements.items():
        inputs: list[list[float]] = []
        targets: list[float] = []
        for index, observed in enumerate(observations_by_time):
            if indicator not in observed:
                continue
            inputs.append(state_vectors[index])
            targets.append(float(observed[indicator]))

        if len(inputs) < max(4, len(state_keys)):
            fitted_measurements[indicator] = [float(value) for value in configured_weights]
            continue

        beta = _fit_ridge_coefficients(inputs, targets)
        intercept = float(beta[0])
        weights = [float(value) for value in beta[1:]]
        predictions = [intercept + sum(weights[col] * row[col] for col in range(len(weights))) for row in inputs]
        errors = [(prediction - target) ** 2 for prediction, target in zip(predictions, targets)]
        rmse = sqrt(sum(errors) / max(1, len(errors)))
        residual_variance = max(4.0, sum(errors) / max(1, len(errors)))
        rmses.append(rmse)
        residual_variances.append(residual_variance)
        fitted_measurements[indicator] = weights

        configured_primary = state_keys[max(range(len(configured_weights)), key=lambda idx: abs(float(configured_weights[idx])))]
        fitted_primary = state_keys[max(range(len(weights)), key=lambda idx: abs(weights[idx]))]
        observation_rows.append(
            {
                'indicator': indicator,
                'configured_primary_state': configured_primary,
                'fitted_primary_state': fitted_primary,
                'rmse': round(rmse, 2),
                'residual_variance': round(residual_variance, 2),
            }
        )

    if not rmses:
        return {
            'fit_rmse': 0.0,
            'quality': 'Unavailable',
            'blend_weight': 0.0,
            'summary': 'Filter calibration unavailable because fitted observation history is too sparse.',
            'configured_noise_floor': round(configured_measurement_noise_floor, 2),
            'fitted_noise_floor': 0.0,
            'blended_noise_floor': round(configured_measurement_noise_floor, 2),
            'configured_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
            'fitted_process_noise': 0.0,
            'blended_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
            'observations': [],
        }, configured_measurements, configured_process_noise, configured_measurement_noise_floor

    fit_rmse = round(sum(rmses) / max(1, len(rmses)), 2)
    quality, blend_weight = _quality_from_rmse(fit_rmse)
    blended_measurements = {
        indicator: [
            round(float(configured_measurements[indicator][index]) * (1.0 - blend_weight) + float(fitted_measurements[indicator][index]) * blend_weight, 4)
            for index in range(len(state_keys))
        ]
        for indicator in configured_measurements
    }

    process_errors = [[] for _ in state_keys]
    for index in range(1, len(state_vectors)):
        predicted_state = [
            sum(transition[row][col] * state_vectors[index - 1][col] for col in range(len(state_keys))) + float(transition_intercepts[row])
            for row in range(len(state_keys))
        ]
        for row in range(len(state_keys)):
            process_errors[row].append((state_vectors[index][row] - predicted_state[row]) ** 2)

    fitted_process_noise = [
        round(max(4.0, sum(errors) / max(1, len(errors))), 2)
        for errors in process_errors
    ]
    blended_process_noise = [
        round(float(configured_process_noise[index]) * (1.0 - blend_weight) + float(fitted_process_noise[index]) * blend_weight, 2)
        for index in range(len(state_keys))
    ]

    fitted_noise_floor = round(max(6.0, (sum(residual_variances) / max(1, len(residual_variances))) * 0.6), 2)
    blended_noise_floor = round(configured_measurement_noise_floor * (1.0 - blend_weight) + fitted_noise_floor * blend_weight, 2)

    observation_rows.sort(key=lambda item: item['rmse'], reverse=True)
    overview = {
        'fit_rmse': fit_rmse,
        'quality': quality,
        'blend_weight': round(blend_weight, 2),
        'summary': (
            f'Filter fit is {quality.lower()} with observation RMSE {fit_rmse:.1f}. '
            f'Blended measurement-noise floor is {blended_noise_floor:.1f}, versus configured {configured_measurement_noise_floor:.1f}.'
        ),
        'configured_noise_floor': round(configured_measurement_noise_floor, 2),
        'fitted_noise_floor': fitted_noise_floor,
        'blended_noise_floor': blended_noise_floor,
        'configured_process_noise': round(sum(configured_process_noise) / max(1, len(configured_process_noise)), 2),
        'fitted_process_noise': round(sum(fitted_process_noise) / max(1, len(fitted_process_noise)), 2),
        'blended_process_noise': round(sum(blended_process_noise) / max(1, len(blended_process_noise)), 2),
        'observations': observation_rows[:8],
    }
    return overview, blended_measurements, blended_process_noise, blended_noise_floor
