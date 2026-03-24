from __future__ import annotations

from collections.abc import Sequence
from statistics import mean, pstdev
from typing import Any


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def compute_percentile(window: Sequence[float], value: float) -> float:
    if not window:
        return 50.0
    ordered = sorted(float(item) for item in window)
    less = sum(1 for item in ordered if item < value)
    equal = sum(1 for item in ordered if item == value)
    rank = (less + 0.5 * equal) / len(ordered)
    return round(rank * 100.0, 2)


def normalize_value(value: float, threshold: dict[str, Any] | None) -> float | None:
    if not threshold:
        return None

    warning = float(threshold["warning"])
    critical = float(threshold["critical"])
    direction = threshold.get("direction", "high")

    if direction == "high":
        span = critical - warning if critical != warning else 1.0
        score = ((value - warning) / span) * 100.0
        return round(clamp(score), 2)

    span = warning - critical if critical != warning else 1.0
    score = ((warning - value) / span) * 100.0
    return round(clamp(score), 2)


def determine_status(value: float, threshold: dict[str, Any] | None) -> str:
    if not threshold:
        return "green"

    warning = float(threshold["warning"])
    critical = float(threshold["critical"])
    direction = threshold.get("direction", "high")

    if direction == "high":
        span = abs(critical - warning) if critical != warning else max(abs(warning), 1.0)
        caution = warning - (0.5 * span)
        if value >= critical:
            return "red"
        if value >= warning:
            return "orange"
        if value >= caution:
            return "yellow"
        return "green"

    span = abs(warning - critical) if critical != warning else max(abs(warning), 1.0)
    caution = warning + (0.5 * span)
    if value <= critical:
        return "red"
    if value <= warning:
        return "orange"
    if value <= caution:
        return "yellow"
    return "green"


def compute_series_metrics(
    values: Sequence[tuple[Any, float]], threshold: dict[str, Any] | None = None
) -> list[dict[str, float | Any | None]]:
    enriched: list[dict[str, float | Any | None]] = []
    prior_roc = 0.0

    for index, (timestamp, value) in enumerate(values):
        window_30 = [item[1] for item in values[max(0, index - 29) : index + 1]]
        window_7 = [item[1] for item in values[max(0, index - 6) : index + 1]]
        avg_30 = mean(window_30)
        std_30 = pstdev(window_30) if len(window_30) > 1 else 0.0
        zscore = 0.0 if std_30 == 0 else (value - avg_30) / std_30
        roc = 0.0 if index == 0 else value - values[index - 1][1]
        acceleration = 0.0 if index < 2 else roc - prior_roc
        prior_roc = roc
        enriched.append(
            {
                "timestamp": timestamp,
                "value": round(value, 4),
                "normalized_value": normalize_value(value, threshold),
                "zscore": round(zscore, 4),
                "moving_average_7": round(mean(window_7), 4),
                "moving_average_30": round(avg_30, 4),
                "percentile": compute_percentile(window_30, value),
                "rate_of_change": round(roc, 4),
                "acceleration": round(acceleration, 4),
            }
        )
    return enriched


def rolling_change(values: Sequence[float], lookback: int) -> float:
    if len(values) <= lookback:
        return 0.0
    return round(values[-1] - values[-1 - lookback], 2)
