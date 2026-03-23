from __future__ import annotations

from sqlalchemy.orm import Session

from app.regime_engine.config_loader import load_effective_config
from app.services.seed_service import refresh_market_data, seed_demo_data


def run_refresh(db: Session) -> None:
    seed_demo_data(db)
    config = load_effective_config(db)
    refresh_market_data(db, config)
