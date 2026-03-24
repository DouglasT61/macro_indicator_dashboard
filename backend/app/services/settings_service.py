from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppSetting
from app.regime_engine.config_loader import load_effective_config, load_file_config


settings = get_settings()


def _upsert_setting(db: Session, key: str, value_json: dict[str, Any], *, commit: bool = True, refresh: bool = True) -> AppSetting:
    setting = db.query(AppSetting).filter(AppSetting.key == key).one_or_none()
    if setting is None:
        setting = AppSetting(key=key, value_json=value_json, updated_at=datetime.now(timezone.utc))
        db.add(setting)
    else:
        setting.value_json = value_json
        setting.updated_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
    else:
        db.flush()
    if refresh:
        db.refresh(setting)
    return setting


def get_dashboard_config(db: Session) -> dict[str, Any]:
    return load_effective_config(db)


def save_dashboard_config(db: Session, config: dict[str, Any]) -> AppSetting:
    return _upsert_setting(db, 'regime_config', config)


def get_alerts_enabled(db: Session) -> bool:
    toggle = db.query(AppSetting).filter(AppSetting.key == 'alerts_enabled').one_or_none()
    if toggle is None:
        return settings.enable_alerts
    return bool(toggle.value_json.get('enabled', True))


def set_alerts_enabled(db: Session, enabled: bool) -> AppSetting:
    return _upsert_setting(db, 'alerts_enabled', {'enabled': enabled})


def get_source_status(db: Session) -> dict[str, Any]:
    status = db.query(AppSetting).filter(AppSetting.key == 'source_status').one_or_none()
    if status is None:
        return {
            'data_mode': 'demo',
            'providers': {
                'market_data': 'Seeded demo data active. Add API keys or import CSVs for live extensions.',
                'treasury': 'Demo adapter in use; public API connectors can be added without breaking the app.',
                'manual_overlays': 'Persisted in SQLite and included in regime scoring.',
                'shipping_data': 'Demo shipping chokepoint data active; PortWatch integration can override Hormuz transit stress when available.',
            },
        }
    return status.value_json


def save_source_status(db: Session, data_mode: str, providers: dict[str, str], *, commit: bool = True) -> AppSetting:
    payload = {'data_mode': data_mode, 'providers': providers}
    return _upsert_setting(db, 'source_status', payload, commit=commit)


def get_imported_series_keys(db: Session) -> set[str]:
    setting = db.query(AppSetting).filter(AppSetting.key == 'imported_series_keys').one_or_none()
    if setting is None:
        return set()
    keys = setting.value_json.get('keys', [])
    return {str(key) for key in keys}


def save_imported_series_keys(db: Session, keys: set[str], *, commit: bool = True) -> AppSetting:
    payload = {'keys': sorted(keys)}
    return _upsert_setting(db, 'imported_series_keys', payload, commit=commit)


def reset_config(db: Session) -> AppSetting:
    return save_dashboard_config(db, load_file_config())
