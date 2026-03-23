from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.regime_engine.config_loader import load_effective_config
from app.services.seed_service import refresh_market_data, seed_demo_data
from app.services.settings_service import get_source_status, save_source_status


def _update_refresh_status(db: Session, message: str) -> None:
    source_status = get_source_status(db)
    providers = dict(source_status.get('providers', {}))
    providers['refresh_status'] = message
    save_source_status(db, source_status.get('data_mode', 'mixed'), providers)


def run_refresh(db: Session) -> None:
    _update_refresh_status(db, f"Refresh started at {datetime.now(timezone.utc).isoformat()}.")
    seed_demo_data(db)
    config = load_effective_config(db)
    try:
        refresh_market_data(db, config)
    except Exception as exc:
        _update_refresh_status(db, f"Refresh failed at {datetime.now(timezone.utc).isoformat()}: {exc.__class__.__name__}.")
        raise
    _update_refresh_status(db, f"Refresh completed at {datetime.now(timezone.utc).isoformat()}.")


def run_refresh_in_new_session() -> None:
    db = SessionLocal()
    try:
        run_refresh(db)
    finally:
        db.close()
