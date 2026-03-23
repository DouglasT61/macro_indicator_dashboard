from __future__ import annotations

from app.core.database import Base, SessionLocal, engine
from app.services.seed_service import bootstrap_demo_only


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_demo_only(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
