from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.endpoints import dashboard as dashboard_endpoints
from app.api.endpoints import settings as settings_endpoints
from app.core.database import Base, get_db
from app.models import AppSetting


def build_test_client(tmp_path: Path) -> tuple[TestClient, sessionmaker]:
    db_path = tmp_path / 'api-test.db'
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(dashboard_endpoints.router, prefix='/api/v1/dashboard')
    app.include_router(settings_endpoints.router, prefix='/api/v1/settings')

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def test_refresh_endpoint_reports_already_running(tmp_path, monkeypatch) -> None:
    client, _ = build_test_client(tmp_path)
    monkeypatch.setattr(dashboard_endpoints, 'mark_refresh_queued', lambda: False)

    response = client.post('/api/v1/dashboard/refresh')

    assert response.status_code == 200
    assert response.json()['message'] == 'Dashboard refresh already running.'


def test_config_update_validates_payload(tmp_path) -> None:
    client, _ = build_test_client(tmp_path)

    response = client.put('/api/v1/settings/config', json={'not_a_real_config': True})

    assert response.status_code == 422


def test_config_update_persists_valid_payload(tmp_path, monkeypatch) -> None:
    client, _ = build_test_client(tmp_path)
    monkeypatch.setattr(settings_endpoints, 'mark_refresh_queued', lambda: False)

    valid_payload = {
        'thresholds': {},
        'regimes': {'sticky': [], 'convex': [], 'break': []},
        'causal_groups': {},
        'alert_rules': {},
    }

    response = client.put('/api/v1/settings/config', json=valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert body['config'] == valid_payload


def test_import_csv_pins_series_without_queueing_refresh(tmp_path, monkeypatch) -> None:
    client, TestingSessionLocal = build_test_client(tmp_path)
    refresh_called = False

    def fake_import_indicator_csv(db, series_key, file, thresholds):
        return 3

    def fake_mark_refresh_queued():
        nonlocal refresh_called
        refresh_called = True
        return True

    monkeypatch.setattr(settings_endpoints, 'import_indicator_csv', fake_import_indicator_csv)
    monkeypatch.setattr(settings_endpoints, 'mark_refresh_queued', fake_mark_refresh_queued)

    response = client.post(
        '/api/v1/settings/import/test_series',
        files={'file': ('test.csv', BytesIO(b'timestamp,value\n2026-01-01,1\n'), 'text/csv')},
    )

    assert response.status_code == 200
    assert 'pinned and will not be overwritten by refresh' in response.json()['message']
    assert refresh_called is False

    with TestingSessionLocal() as db:
        setting = db.query(AppSetting).filter(AppSetting.key == 'imported_series_keys').one_or_none()
        assert setting is not None
        assert 'test_series' in setting.value_json['keys']


def test_export_route_uses_dashboard_summary_builder(tmp_path, monkeypatch) -> None:
    client, _ = build_test_client(tmp_path)
    monkeypatch.setattr(settings_endpoints, 'mark_refresh_queued', lambda: False)
    monkeypatch.setattr(dashboard_endpoints, 'build_daily_summary_markdown', lambda db: '# Test Summary\n')

    response = client.get('/api/v1/dashboard/export/daily-summary')

    assert response.status_code == 200
    assert response.text == '# Test Summary\n'


def test_get_config_uses_persisted_updated_at(tmp_path) -> None:
    client, TestingSessionLocal = build_test_client(tmp_path)
    updated_at = datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc)

    with TestingSessionLocal() as db:
        db.add(AppSetting(key='regime_config', value_json={'thresholds': {}, 'regimes': {}, 'causal_groups': {}, 'alert_rules': {}}, updated_at=updated_at))
        db.commit()

    response = client.get('/api/v1/settings/config')

    assert response.status_code == 200
    assert response.json()['updated_at'].startswith('2026-03-24T12:00:00')
