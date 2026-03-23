$env:PYTHONPATH = 'backend;vendor_py'
python -c "from app.core.database import Base, engine, SessionLocal; from app.services.seed_service import seed_demo_data; Base.metadata.create_all(bind=engine); db = SessionLocal(); seed_demo_data(db); db.close(); print('Demo seed complete.')"
