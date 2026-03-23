from __future__ import annotations

import csv
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

    content = upload.file.read().decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    parsed: list[tuple[datetime, float]] = []
    for row in reader:
        if "timestamp" not in row or "value" not in row:
            raise HTTPException(status_code=400, detail="CSV must contain timestamp and value columns")
        parsed.append((datetime.fromisoformat(row["timestamp"]).astimezone(timezone.utc), float(row["value"])))

    if not parsed:
        raise HTTPException(status_code=400, detail="No rows found in uploaded CSV")

    records = compute_series_metrics(sorted(parsed, key=lambda item: item[0]), threshold)
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
    db.commit()
    return len(records)
