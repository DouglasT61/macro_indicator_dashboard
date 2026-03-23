from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.refresh_service import run_refresh


settings = get_settings()


class SchedulerManager:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(timezone="UTC")

    def start(self) -> None:
        if not settings.scheduler_enabled or self.scheduler.running:
            return
        trigger = CronTrigger(hour=settings.refresh_hour, minute=settings.refresh_minute)
        self.scheduler.add_job(self._job_wrapper, trigger=trigger, id="daily-refresh", replace_existing=True)
        if settings.bootstrap_on_startup:
            self.scheduler.add_job(
                self._job_wrapper,
                trigger="date",
                run_date=datetime.now(timezone.utc) + timedelta(seconds=30),
                id="startup-refresh",
                replace_existing=True,
            )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    @staticmethod
    def _job_wrapper() -> None:
        db = SessionLocal()
        try:
            run_refresh(db)
        finally:
            db.close()


scheduler_manager = SchedulerManager()
