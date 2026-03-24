from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.regime_engine.config_loader import load_effective_config
from app.services.seed_service import refresh_market_data, seed_demo_data
from app.services.settings_service import get_source_status, save_source_status

_REFRESH_STATE_LOCK = Lock()
_refresh_running = False
_refresh_queued = False


def _update_refresh_status(db: Session, message: str) -> None:
    source_status = get_source_status(db)
    providers = dict(source_status.get('providers', {}))
    providers['refresh_status'] = message
    save_source_status(db, source_status.get('data_mode', 'mixed'), providers)


def is_refresh_running() -> bool:
    with _REFRESH_STATE_LOCK:
        return _refresh_running or _refresh_queued


def mark_refresh_queued() -> bool:
    global _refresh_queued
    with _REFRESH_STATE_LOCK:
        if _refresh_running or _refresh_queued:
            return False
        _refresh_queued = True
        return True


def _begin_refresh_run() -> bool:
    global _refresh_running, _refresh_queued
    with _REFRESH_STATE_LOCK:
        if _refresh_running:
            return False
        _refresh_queued = False
        _refresh_running = True
        return True


def _finish_refresh_run() -> None:
    global _refresh_running
    with _REFRESH_STATE_LOCK:
        _refresh_running = False


def run_refresh(db: Session) -> None:
    _update_refresh_status(db, f"Refresh started at {datetime.now(timezone.utc).isoformat()}.")
    config = load_effective_config(db)
    try:
        refresh_market_data(db, config)
    except Exception as exc:
        db.rollback()
        _update_refresh_status(db, f"Refresh failed at {datetime.now(timezone.utc).isoformat()}: {exc.__class__.__name__}.")
        raise
    _update_refresh_status(db, f"Refresh completed at {datetime.now(timezone.utc).isoformat()}.")


def run_refresh_in_new_session() -> None:
    if not _begin_refresh_run():
        db = SessionLocal()
        try:
            _update_refresh_status(db, f"Refresh skipped at {datetime.now(timezone.utc).isoformat()}: already running.")
        finally:
            db.close()
        return
    db = SessionLocal()
    try:
        run_refresh(db)
    finally:
        db.close()
        _finish_refresh_run()
