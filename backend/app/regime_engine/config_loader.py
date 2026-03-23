from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppSetting


settings = get_settings()


def load_file_config() -> dict[str, Any]:
    config_path = Path(settings.regime_config_path)
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_effective_config(db: Session) -> dict[str, Any]:
    file_config = load_file_config()
    override = db.query(AppSetting).filter(AppSetting.key == "regime_config").one_or_none()
    if override:
        return override.value_json
    return file_config
