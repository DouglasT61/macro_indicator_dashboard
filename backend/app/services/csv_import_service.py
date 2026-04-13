from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from io import StringIO

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models import IndicatorSeries, IndicatorValue
from app.services.analytics import compute_series_metrics


def import_indicator_csv(db: Session, series_key: str, upload: UploadFile, threshold: dict | None) -> int:
    series = db.query(IndicatorSeries).filter(IndicatorSeries.key == series_key).one_or_none()
    if series is None:
        raise HTTPException(status_code=404, detail=f"Unknown series key: {series_key}")

    # --- Content decode (rejects binary files such as .xlsx) ---
    try:
        content = upload.file.read().decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded CSV. Binary files (e.g. .xlsx) are not supported.",
        )

    reader = csv.DictReader(StringIO(content))

    # --- Pre-flight header check (case-insensitive, before iterating rows) ---
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")

    lower_fields = {f.strip().lower(): f for f in reader.fieldnames}
    if "timestamp" not in lower_fields or "value" not in lower_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                f"CSV must contain 'timestamp' and 'value' columns (case-insensitive). "
                f"Found columns: {list(reader.fieldnames)}"
            ),
        )
    ts_col = lower_fields["timestamp"]
    val_col = lower_fields["value"]

    # --- Row-level parsing with per-row error collection ---
    parsed: list[tuple[datetime, float]] = []
    errors: list[str] = []

    for row_num, row in enumerate(reader, start=2):  # row 1 = header
        raw_ts = (row.get(ts_col) or "").strip()
        raw_val = (row.get(val_col) or "").strip()

        # Parse timestamp — handle Z-suffix valid in ISO 8601 but rejected by
        # fromisoformat() before Python 3.11.
        try:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).astimezone(timezone.utc)
        except (ValueError, AttributeError):
            errors.append(f"Row {row_num}: unparseable timestamp '{raw_ts}'")
            continue

        # Parse value — reject non-numeric, NaN, and Inf.
        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: non-numeric value '{raw_val}'")
            continue
        if math.isnan(val) or math.isinf(val):
            errors.append(f"Row {row_num}: non-finite value '{raw_val}'")
            continue

        parsed.append((ts, val))

    if errors:
        sample = errors[:10]
        suffix = f" … and {len(errors) - 10} more" if len(errors) > 10 else ""
        raise HTTPException(
            status_code=400,
            detail=f"CSV parsing errors ({len(errors)} total): {'; '.join(sample)}{suffix}",
        )

    if not parsed:
        raise HTTPException(status_code=400, detail="No valid rows found in uploaded CSV.")

    # --- Deduplicate by timestamp (last occurrence wins) before DB write ---
    # Without dedup, duplicate timestamps would trigger a UniqueConstraint violation
    # mid-commit with no user-facing explanation.
    deduped: dict[datetime, float] = {}
    for ts, val in parsed:
        deduped[ts] = val
    ordered = sorted(deduped.items(), key=lambda item: item[0])

    records = compute_series_metrics(ordered, threshold)

    db.query(IndicatorValue).filter(IndicatorValue.series_id == series.id).delete()
    db.flush()
    for record in records:
        db.add(
            IndicatorValue(
                series_id=series.id,
                timestamp=record["timestamp"],
                value=record["value"],
                normalized_value=record["normalized_value"],
                zscore=record["zscore"],
                moving_average_7=record["moving_average_7"],
                moving_average_30=record["moving_average_30"],
                percentile=record["percentile"],
                rate_of_change=record["rate_of_change"],
                acceleration=record["acceleration"],
            )
        )
    series.last_updated = records[-1]["timestamp"]
    series.source = "manual/csv-import"
    db.commit()
    return len(records)
