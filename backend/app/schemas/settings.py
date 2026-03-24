from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ThresholdConfig(BaseModel):
    warning: float
    critical: float
    direction: str


class SignalWeight(BaseModel):
    indicator: str
    weight: float
    mode: str
    description: str


class RegimeConfigModel(BaseModel):
    thresholds: dict[str, ThresholdConfig]
    regimes: dict[str, list[SignalWeight]]
    alert_rules: dict[str, dict[str, Any]]
    causal_groups: dict[str, list[str]]

    model_config = ConfigDict(extra="allow")


class SettingsResponse(BaseModel):
    updated_at: datetime
    config: dict[str, Any]
    alerts_enabled: bool


class ManualInputCreate(BaseModel):
    key: str
    value: float
    notes: str = ""


class EventAnnotationCreate(BaseModel):
    title: str
    description: str = ""
    related_series: list[str]
    severity: str = "info"
