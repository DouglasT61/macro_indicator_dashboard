from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import EventAnnotation, ManualInput
from app.regime_engine.config_loader import load_effective_config
from app.schemas.common import ApiMessage
from app.schemas.settings import EventAnnotationCreate, ManualInputCreate, SettingsResponse
from app.services.csv_import_service import import_indicator_csv
from app.services.refresh_service import run_refresh_in_new_session
from app.services.settings_service import get_alerts_enabled, get_dashboard_config, save_dashboard_config, set_alerts_enabled

router = APIRouter()


@router.get("/config", response_model=SettingsResponse)
def get_config(db: Session = Depends(get_db)) -> SettingsResponse:
    updated_at = datetime.now(timezone.utc)
    return SettingsResponse(updated_at=updated_at, config=get_dashboard_config(db), alerts_enabled=get_alerts_enabled(db))


@router.put("/config", response_model=SettingsResponse)
def update_config(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> SettingsResponse:
    saved = save_dashboard_config(db, payload)
    if background_tasks is not None:
        background_tasks.add_task(run_refresh_in_new_session)
    return SettingsResponse(updated_at=saved.updated_at, config=payload, alerts_enabled=get_alerts_enabled(db))


@router.post("/alerts-toggle", response_model=SettingsResponse)
def toggle_alerts(enabled: bool = Query(...), db: Session = Depends(get_db)) -> SettingsResponse:
    saved = set_alerts_enabled(db, enabled)
    return SettingsResponse(updated_at=saved.updated_at, config=get_dashboard_config(db), alerts_enabled=enabled)


@router.get("/manual-inputs")
def list_manual_inputs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(ManualInput).order_by(ManualInput.timestamp.desc()).all()
    return [{"id": row.id, "timestamp": row.timestamp, "key": row.key, "value": row.value, "notes": row.notes} for row in rows]


@router.post("/manual-inputs", response_model=ApiMessage)
def create_manual_input(
    payload: ManualInputCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> ApiMessage:
    db.add(ManualInput(timestamp=datetime.now(timezone.utc), key=payload.key, value=payload.value, notes=payload.notes))
    db.commit()
    if background_tasks is not None:
        background_tasks.add_task(run_refresh_in_new_session)
    return ApiMessage(message=f"Manual input '{payload.key}' saved. Refresh queued.", timestamp=datetime.now(timezone.utc))


@router.get("/events")
def list_events(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(EventAnnotation).order_by(EventAnnotation.timestamp.desc()).all()
    return [
        {
            "id": row.id,
            "timestamp": row.timestamp,
            "title": row.title,
            "description": row.description,
            "related_series": row.related_series,
            "severity": row.severity,
        }
        for row in rows
    ]


@router.post("/events", response_model=ApiMessage)
def create_event(payload: EventAnnotationCreate, db: Session = Depends(get_db)) -> ApiMessage:
    db.add(
        EventAnnotation(
            timestamp=datetime.now(timezone.utc),
            title=payload.title,
            description=payload.description,
            related_series=payload.related_series,
            severity=payload.severity,
        )
    )
    db.commit()
    return ApiMessage(message="Event annotation saved.", timestamp=datetime.now(timezone.utc))


@router.post("/import/{series_key}", response_model=ApiMessage)
def import_csv(
    series_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> ApiMessage:
    config = load_effective_config(db)
    count = import_indicator_csv(db, series_key, file, config["thresholds"].get(series_key))
    if background_tasks is not None:
        background_tasks.add_task(run_refresh_in_new_session)
    return ApiMessage(message=f"Imported {count} rows into {series_key}. Refresh queued.", timestamp=datetime.now(timezone.utc))
