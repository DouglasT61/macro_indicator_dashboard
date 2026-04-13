"""Pure-Python linear algebra utilities shared across state-space services.

Provides:
  - _transpose       — matrix transposition
  - _mat_mul         — matrix multiplication
  - _diag            — diagonal matrix from a vector
  - _solve_linear_system  — Gaussian elimination with partial pivoting
  - _fit_ridge_coefficients — weighted ridge regression (OLS + L2 penalty)

All inputs/outputs are plain ``list[list[float]]`` / ``list[float]`` to avoid
any NumPy dependency.  This module is intentionally free of side-effects and
safe to import at module level.
"""
from __future__ import annotations


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


def _diag(values: list[float]) -> list[list[float]]:
    n = len(values)
    return [[values[i] if i == j else 0.0 for j in range(n)] for i in range(n)]


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve *matrix* · x = *vector* via Gaussian elimination with partial pivoting."""
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
    ridge: float = 14.0,
    sample_weights: list[float] | None = None,
    anchor: list[float] | None = None,
    anchor_strength: float = 0.0,
) -> list[float]:
    """Fit a ridge-regularised linear model, optionally with per-sample weights
    and a Bayesian-style prior anchor.

    Returns a coefficient vector of length ``len(inputs[0]) + 1`` (intercept first).

    Parameters
    ----------
    inputs:
        Feature matrix, shape (n_samples, n_features).
    targets:
        Target vector, length n_samples.
    ridge:
        L2 penalty applied to non-intercept coefficients.  The intercept
        receives ``ridge * 0.1`` so it can adapt freely.
    sample_weights:
        Optional per-row importance weights.  Defaults to uniform (1.0).
    anchor:
        Prior coefficient values of length ``n_features + 1``.  Defaults to zeros.
    anchor_strength:
        Strength of the pull toward *anchor* (0 = disabled).
    """
    design = [[1.0, *row] for row in inputs]
    design_t = _transpose(design)
    weights = sample_weights or [1.0 for _ in targets]
    weighted_design = [
        [design[row][col] * weights[row] for col in range(len(design[row]))]
        for row in range(len(design))
    ]
    xtx = _mat_mul(design_t, weighted_design)
    weighted_targets = [targets[row] * weights[row] for row in range(len(targets))]
    xty = [
        sum(design_t[row][col] * weighted_targets[col] for col in range(len(targets)))
        for row in range(len(design_t))
    ]

    if anchor is None:
        anchor = [0.0 for _ in range(len(xtx))]
    for index in range(len(xtx)):
        penalty = ridge if index > 0 else ridge * 0.1
        prior_penalty = anchor_strength if index > 0 else anchor_strength * 0.1
        xtx[index][index] += penalty + prior_penalty
        xty[index] += float(anchor[index]) * prior_penalty

    return _solve_linear_system(xtx, xty)
