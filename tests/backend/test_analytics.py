"""Unit tests for app.services.analytics.

Covers edge cases identified in the audit:
- Zero-variance (constant) series → zscore always 0, percentile 50
- Single-point series → all rolling metrics at neutral defaults
- normalize_value: high/low direction, zero-span guard, clamping
- compute_percentile: empty window fallback, boundary values
- rolling_change: short-series fallback
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.analytics import (
    clamp,
    compute_percentile,
    compute_series_metrics,
    determine_status,
    normalize_value,
    rolling_change,
)

_T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
_T1 = datetime(2024, 1, 2, tzinfo=timezone.utc)
_T2 = datetime(2024, 1, 3, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

def test_clamp_within_range():
    assert clamp(50.0) == 50.0


def test_clamp_below_lower():
    assert clamp(-10.0) == 0.0


def test_clamp_above_upper():
    assert clamp(110.0) == 100.0


def test_clamp_custom_bounds():
    assert clamp(5.0, lower=10.0, upper=20.0) == 10.0
    assert clamp(25.0, lower=10.0, upper=20.0) == 20.0


# ---------------------------------------------------------------------------
# compute_percentile
# ---------------------------------------------------------------------------

def test_percentile_empty_window_returns_fifty():
    assert compute_percentile([], 99.0) == 50.0


def test_percentile_single_element_equal():
    # value == only element → rank = (0 + 0.5*1)/1 = 0.5 → 50.0
    assert compute_percentile([42.0], 42.0) == 50.0


def test_percentile_all_below():
    # value larger than all window items
    assert compute_percentile([1.0, 2.0, 3.0], 10.0) == 100.0


def test_percentile_all_above():
    # value smaller than all window items
    assert compute_percentile([10.0, 20.0, 30.0], 0.0) == 0.0


# ---------------------------------------------------------------------------
# normalize_value
# ---------------------------------------------------------------------------

def test_normalize_value_no_threshold_returns_none():
    assert normalize_value(50.0, None) is None
    assert normalize_value(50.0, {}) is None


def test_normalize_value_high_direction_clamps_at_zero():
    threshold = {"warning": 10.0, "critical": 20.0, "direction": "high"}
    # value below warning → score < 0 → clamped to 0
    assert normalize_value(5.0, threshold) == 0.0


def test_normalize_value_high_direction_clamps_at_hundred():
    threshold = {"warning": 10.0, "critical": 20.0, "direction": "high"}
    assert normalize_value(30.0, threshold) == 100.0


def test_normalize_value_high_direction_midpoint():
    threshold = {"warning": 0.0, "critical": 100.0, "direction": "high"}
    assert normalize_value(50.0, threshold) == 50.0


def test_normalize_value_low_direction():
    threshold = {"warning": 100.0, "critical": 50.0, "direction": "low"}
    # value == warning → score = 0 → clamped to 0
    assert normalize_value(100.0, threshold) == 0.0
    # value == critical → score = 100
    assert normalize_value(50.0, threshold) == 100.0


def test_normalize_value_zero_span_guard():
    # warning == critical → span forced to 1.0 to avoid ZeroDivisionError
    threshold = {"warning": 50.0, "critical": 50.0, "direction": "high"}
    result = normalize_value(51.0, threshold)
    assert result is not None  # must not raise
    assert 0.0 <= result <= 100.0


# ---------------------------------------------------------------------------
# determine_status
# ---------------------------------------------------------------------------

def test_determine_status_no_threshold_returns_green():
    assert determine_status(999.0, None) == "green"


def test_determine_status_high_direction_levels():
    threshold = {"warning": 40.0, "critical": 80.0, "direction": "high"}
    assert determine_status(10.0, threshold) == "green"
    assert determine_status(45.0, threshold) == "orange"
    assert determine_status(90.0, threshold) == "red"


def test_determine_status_low_direction_levels():
    # warning=60, critical=20, span=40, caution=60+20=80
    threshold = {"warning": 60.0, "critical": 20.0, "direction": "low"}
    assert determine_status(85.0, threshold) == "green"   # above caution (80)
    assert determine_status(70.0, threshold) == "yellow"  # between warning(60) and caution(80)
    assert determine_status(55.0, threshold) == "orange"  # below warning, above critical
    assert determine_status(10.0, threshold) == "red"     # below critical (20)


# ---------------------------------------------------------------------------
# compute_series_metrics — single-point series
# ---------------------------------------------------------------------------

def test_single_point_series_neutral_defaults():
    result = compute_series_metrics([(_T0, 42.0)])
    assert len(result) == 1
    row = result[0]
    assert row["value"] == 42.0
    assert row["zscore"] == 0.0        # std_30 is 0 for single point
    assert row["rate_of_change"] == 0.0
    assert row["acceleration"] == 0.0
    assert row["moving_average_7"] == 42.0
    assert row["moving_average_30"] == 42.0


# ---------------------------------------------------------------------------
# compute_series_metrics — zero-variance (constant) series
# ---------------------------------------------------------------------------

def test_zero_variance_series_zscore_always_zero():
    series = [(_T0, 55.0), (_T1, 55.0), (_T2, 55.0)]
    results = compute_series_metrics(series)
    for row in results:
        assert row["zscore"] == 0.0, f"Expected zscore=0 but got {row['zscore']}"


def test_zero_variance_series_percentile_fifty():
    series = [(_T0, 55.0), (_T1, 55.0), (_T2, 55.0)]
    results = compute_series_metrics(series)
    # All equal → each value is at the 50th percentile of its window
    for row in results:
        assert row["percentile"] == 50.0, f"Expected percentile=50 but got {row['percentile']}"


# ---------------------------------------------------------------------------
# compute_series_metrics — rate_of_change and acceleration
# ---------------------------------------------------------------------------

def test_roc_and_acceleration():
    series = [(_T0, 10.0), (_T1, 20.0), (_T2, 35.0)]
    results = compute_series_metrics(series)
    # roc[0] = 0, roc[1] = 10, roc[2] = 15
    assert results[0]["rate_of_change"] == 0.0
    assert results[1]["rate_of_change"] == 10.0
    assert results[2]["rate_of_change"] == 15.0
    # acceleration[2] = roc[2] - roc[1] = 15 - 10 = 5
    assert results[2]["acceleration"] == 5.0


# ---------------------------------------------------------------------------
# compute_series_metrics — threshold propagation
# ---------------------------------------------------------------------------

def test_normalized_value_propagated_with_threshold():
    threshold = {"warning": 10.0, "critical": 20.0, "direction": "high"}
    series = [(_T0, 15.0)]
    result = compute_series_metrics(series, threshold)
    # normalized = (15-10)/(20-10)*100 = 50
    assert result[0]["normalized_value"] == 50.0


def test_normalized_value_none_without_threshold():
    series = [(_T0, 42.0)]
    result = compute_series_metrics(series, threshold=None)
    assert result[0]["normalized_value"] is None


# ---------------------------------------------------------------------------
# rolling_change
# ---------------------------------------------------------------------------

def test_rolling_change_normal():
    assert rolling_change([10.0, 20.0, 30.0, 40.0], lookback=2) == 20.0


def test_rolling_change_series_too_short_returns_zero():
    assert rolling_change([10.0, 20.0], lookback=5) == 0.0


def test_rolling_change_single_element():
    assert rolling_change([42.0], lookback=1) == 0.0
