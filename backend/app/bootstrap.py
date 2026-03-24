from __future__ import annotations

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.services.seed_service import bootstrap_demo_only, ensure_bootstrap_state


def main() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    db = SessionLocal()
    try:
        if settings.demo_mode:
            bootstrap_demo_only(db)
        else:
            ensure_bootstrap_state(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
