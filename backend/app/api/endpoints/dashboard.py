from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ApiMessage
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import get_dashboard_overview
from app.services.export_service import build_daily_summary_markdown
from app.services.refresh_service import run_refresh_in_new_session

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
def dashboard_overview(db: Session = Depends(get_db)) -> DashboardOverview:
    return DashboardOverview.model_validate(get_dashboard_overview(db))


@router.post("/refresh", response_model=ApiMessage)
def refresh_dashboard(background_tasks: BackgroundTasks) -> ApiMessage:
    background_tasks.add_task(run_refresh_in_new_session)
    return ApiMessage(message="Dashboard refresh queued.", timestamp=datetime.now(timezone.utc))


@router.get("/export/daily-summary", response_class=PlainTextResponse)
def export_daily_summary(db: Session = Depends(get_db)) -> str:
    return build_daily_summary_markdown(db)
