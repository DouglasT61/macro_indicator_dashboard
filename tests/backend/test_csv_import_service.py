"""Unit tests for app.services.csv_import_service.import_indicator_csv.

Covers every validation path added in the audit rewrite:
- Binary / non-UTF-8 file rejection (400)
- Empty CSV / missing header (400)
- Missing 'timestamp' or 'value' column (400, case-insensitive)
- Unparseable timestamps (row-level error collection)
- Non-numeric and non-finite (NaN/Inf) values (row-level error collection)
- Duplicate timestamp deduplication (last-wins)
- Unknown series key (404)
- Happy path: rows written and count returned

NOTE: app.models uses Python 3.10+ union syntax (``X | None``) in SQLAlchemy
Mapped[] annotations, which fails at import time on Python 3.9.  We stub
``app.models`` in sys.modules before importing the service under test so that
the test suite runs cleanly on the project's minimum Python version.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# ------------------------------------------------------------------
# Stub app.models for Python 3.9 compatibility
# app.models uses Mapped[X | None] annotations that fail on Python 3.9.
# We inject MagicMock *instances* (not the class) so that attribute
# access like IndicatorSeries.key returns a dynamic MagicMock.
# ------------------------------------------------------------------
_models_stub = MagicMock()
_models_stub.IndicatorSeries = MagicMock()   # instance → .key auto-stubbed
_models_stub.IndicatorValue = MagicMock()
sys.modules.setdefault("app.models", _models_stub)
sys.modules.setdefault("app.models.models", _models_stub)

from app.services.csv_import_service import import_indicator_csv  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_upload(content: str | bytes, filename: str = "test.csv") -> MagicMock:
    """Return a mock UploadFile whose .file.read() returns the given content."""
    upload = MagicMock()
    raw = content.encode("utf-8") if isinstance(content, str) else content
    upload.file.read.return_value = raw
    upload.filename = filename
    return upload


def _make_series(key: str = "test_series") -> MagicMock:
    series = MagicMock()
    series.id = 1
    series.key = key
    return series


def _make_db(series: Any | None) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = series
    db.query.return_value.filter.return_value.delete.return_value = None
    return db


GOOD_CSV = "timestamp,value\n2024-01-01T00:00:00Z,10.0\n2024-01-02T00:00:00Z,20.0\n"


# ---------------------------------------------------------------------------
# 404 — unknown series
# ---------------------------------------------------------------------------

def test_unknown_series_raises_404():
    db = _make_db(series=None)
    upload = _make_upload(GOOD_CSV)
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "nonexistent_key", upload, threshold=None)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# 400 — binary file
# ---------------------------------------------------------------------------

def test_binary_file_raises_400():
    db = _make_db(_make_series())
    upload = _make_upload(b"\xff\xfe binary garbage \x00\x01\x02", filename="data.xlsx")
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400
    assert "UTF-8" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 400 — empty CSV
# ---------------------------------------------------------------------------

def test_empty_csv_raises_400():
    db = _make_db(_make_series())
    upload = _make_upload("")
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# 400 — missing required columns
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("header", [
    "date,val\n2024-01-01,10\n",          # neither column name matches
    "timestamp,score\n2024-01-01,10\n",   # missing 'value'
    "date,value\n2024-01-01,10\n",        # missing 'timestamp'
])
def test_missing_required_columns_raises_400(header):
    db = _make_db(_make_series())
    upload = _make_upload(header)
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400
    assert "timestamp" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Case-insensitive column matching
# ---------------------------------------------------------------------------

def test_case_insensitive_column_headers_accepted():
    csv_content = "Timestamp,Value\n2024-01-01T00:00:00Z,42.0\n"
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    with patch("app.services.csv_import_service.compute_series_metrics") as mock_metrics:
        mock_metrics.return_value = [
            {
                "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "value": 42.0,
                "normalized_value": None,
                "zscore": 0.0,
                "moving_average_7": 42.0,
                "moving_average_30": 42.0,
                "percentile": 50.0,
                "rate_of_change": 0.0,
                "acceleration": 0.0,
            }
        ]
        count = import_indicator_csv(db, "test_series", upload, threshold=None)
    assert count == 1


# ---------------------------------------------------------------------------
# Row-level errors → 400 with error sample
# ---------------------------------------------------------------------------

def test_bad_timestamp_rows_collected_and_raised():
    csv_content = (
        "timestamp,value\n"
        "not-a-date,10.0\n"
        "also-bad,20.0\n"
    )
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400
    assert "2 total" in exc_info.value.detail


def test_non_numeric_value_rows_collected_and_raised():
    csv_content = (
        "timestamp,value\n"
        "2024-01-01T00:00:00Z,abc\n"
        "2024-01-02T00:00:00Z,xyz\n"
    )
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400


def test_nan_value_raises_400():
    csv_content = "timestamp,value\n2024-01-01T00:00:00Z,NaN\n"
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400


def test_inf_value_raises_400():
    csv_content = "timestamp,value\n2024-01-01T00:00:00Z,Inf\n"
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Z-suffix timestamp handling
# ---------------------------------------------------------------------------

def test_z_suffix_timestamp_parsed_correctly():
    csv_content = "timestamp,value\n2024-06-15T12:00:00Z,99.0\n"
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    with patch("app.services.csv_import_service.compute_series_metrics") as mock_metrics:
        mock_metrics.return_value = [
            {
                "timestamp": datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
                "value": 99.0,
                "normalized_value": None,
                "zscore": 0.0,
                "moving_average_7": 99.0,
                "moving_average_30": 99.0,
                "percentile": 50.0,
                "rate_of_change": 0.0,
                "acceleration": 0.0,
            }
        ]
        count = import_indicator_csv(db, "test_series", upload, threshold=None)
    assert count == 1


# ---------------------------------------------------------------------------
# Duplicate timestamp deduplication (last-wins)
# ---------------------------------------------------------------------------

def test_duplicate_timestamps_deduplicated_last_wins():
    csv_content = (
        "timestamp,value\n"
        "2024-01-01T00:00:00Z,10.0\n"
        "2024-01-01T00:00:00Z,99.0\n"   # duplicate — should win
    )
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    captured_pairs: list = []

    def capture_metrics(pairs, threshold):
        captured_pairs.extend(pairs)
        ts, val = pairs[0]
        return [
            {
                "timestamp": ts,
                "value": val,
                "normalized_value": None,
                "zscore": 0.0,
                "moving_average_7": val,
                "moving_average_30": val,
                "percentile": 50.0,
                "rate_of_change": 0.0,
                "acceleration": 0.0,
            }
        ]

    with patch("app.services.csv_import_service.compute_series_metrics", side_effect=capture_metrics):
        import_indicator_csv(db, "test_series", upload, threshold=None)

    assert len(captured_pairs) == 1
    _, val = captured_pairs[0]
    assert val == 99.0


# ---------------------------------------------------------------------------
# Empty valid rows after filtering → 400
# ---------------------------------------------------------------------------

def test_no_valid_rows_raises_400():
    csv_content = "timestamp,value\nnot-a-date,abc\n"
    db = _make_db(_make_series())
    upload = _make_upload(csv_content)
    with pytest.raises(HTTPException) as exc_info:
        import_indicator_csv(db, "test_series", upload, threshold=None)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Happy path — row count returned
# ---------------------------------------------------------------------------

def test_happy_path_returns_row_count():
    db = _make_db(_make_series())
    upload = _make_upload(GOOD_CSV)

    def fake_metrics(pairs, threshold):
        return [
            {
                "timestamp": ts,
                "value": val,
                "normalized_value": None,
                "zscore": 0.0,
                "moving_average_7": val,
                "moving_average_30": val,
                "percentile": 50.0,
                "rate_of_change": 0.0,
                "acceleration": 0.0,
            }
            for ts, val in pairs
        ]

    with patch("app.services.csv_import_service.compute_series_metrics", side_effect=fake_metrics):
        count = import_indicator_csv(db, "test_series", upload, threshold=None)

    assert count == 2
