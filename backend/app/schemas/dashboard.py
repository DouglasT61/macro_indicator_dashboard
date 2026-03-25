from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimePoint(BaseModel):
    timestamp: datetime
    value: float


class ThresholdLine(BaseModel):
    label: str
    value: float
    color: str


class InterpretationChart(BaseModel):
    series: list[TimePoint] = Field(default_factory=list)
    thresholds: list[ThresholdLine] = Field(default_factory=list)


class IndicatorSnapshot(BaseModel):
    key: str
    name: str
    category: str
    unit: str
    source: str
    source_class: str | None = None
    latest_value: float | None = None
    normalized_value: float | None = None
    zscore: float | None = None
    rate_of_change: float | None = None
    acceleration: float | None = None
    status: str
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    direction: str = 'high'
    chart_style: str | None = None
    chart_window_label: str | None = None
    auction_breakdown: list[dict[str, Any]] | None = None
    model_contribution: dict[str, float] | None = None
    dominant_model_regime: str | None = None
    dominant_model_contribution: float | None = None
    narrative: str
    history: list[TimePoint] = Field(default_factory=list)


class RegimeCard(BaseModel):
    name: str
    score: float
    change_7d: float
    change_30d: float
    propagation_boost: float = 0.0
    top_drivers: list[str]


class RegimeOverview(BaseModel):
    current_regime: str
    sticky: RegimeCard
    convex: RegimeCard
    break_regime: RegimeCard = Field(alias='break')
    explanation: dict[str, Any]
    history: list[dict[str, Any]]


class StateSpaceState(BaseModel):
    key: str
    label: str
    value: float
    change_7d: float
    uncertainty: float
    dominant_measurements: list[str]


class StateSpaceDiagnosticPoint(BaseModel):
    timestamp: datetime
    dominant_regime: str
    dominant_probability: float
    probability_gap: float
    aligned_with_rule: bool


class StateSpaceDiagnostics(BaseModel):
    recent_disagreement_streak: int
    dominant_regime_flips: int
    max_probability_gap: float
    latest_probability_gap: float
    confidence_band: str
    tracking_quality: str


class StateSpaceForecastPoint(BaseModel):
    step: int
    timestamp: datetime
    sticky: float
    convex: float
    break_regime: float = Field(alias='break')


class StateSpaceForecastHorizon(BaseModel):
    days: int
    dominant_regime: str
    dominant_probability: float
    sticky: float
    convex: float
    break_regime: float = Field(alias='break')


class StateSpaceScenario(BaseModel):
    key: str
    label: str
    description: str
    dominant_regime: str
    dominant_probability: float
    sticky: float
    convex: float
    break_regime: float = Field(alias='break')
    state_impulse_summary: str


class StateSpaceForecastOverview(BaseModel):
    summary: str
    conditioning_cluster: str
    conditioning_label: str
    conditioning_confidence: float
    conditioning_summary: str
    baseline_path: list[StateSpaceForecastPoint] = Field(default_factory=list)
    horizons: list[StateSpaceForecastHorizon] = Field(default_factory=list)
    scenarios: list[StateSpaceScenario] = Field(default_factory=list)


class StateSpaceCalibrationEpisode(BaseModel):
    key: str
    label: str
    period: str
    target_regime: str
    calibrated_regime: str
    fit_score: float
    rmse: float
    sticky: float
    convex: float
    break_regime: float = Field(alias='break')


class StateSpaceTransitionLink(BaseModel):
    source: str
    target: str
    configured_weight: float
    fitted_weight: float
    blended_weight: float
    delta: float


class StateSpaceTransitionCalibration(BaseModel):
    fit_rmse: float
    quality: str
    blend_weight: float
    summary: str
    configured_persistence: float
    fitted_persistence: float
    blended_persistence: float
    drift_strength: float
    links: list[StateSpaceTransitionLink] = Field(default_factory=list)


class StateSpaceFilterObservation(BaseModel):
    indicator: str
    configured_primary_state: str
    fitted_primary_state: str
    rmse: float
    residual_variance: float


class StateSpaceObservationConditioning(BaseModel):
    cluster_key: str
    cluster_label: str
    cluster_confidence: float
    regime_key: str
    regime_probability: float
    average_trust: float
    boosted_indicators: list[str] = Field(default_factory=list)
    reduced_indicators: list[str] = Field(default_factory=list)
    summary: str


class StateSpaceFilterCalibration(BaseModel):
    fit_rmse: float
    quality: str
    blend_weight: float
    summary: str
    configured_noise_floor: float
    fitted_noise_floor: float
    blended_noise_floor: float
    configured_process_noise: float
    fitted_process_noise: float
    blended_process_noise: float
    observations: list[StateSpaceFilterObservation] = Field(default_factory=list)
    observation_conditioning: StateSpaceObservationConditioning


class StateSpaceIterationPoint(BaseModel):
    iteration: int
    transition_rmse: float
    filter_rmse: float
    parameter_delta: float
    dominant_regime: str
    dominant_probability: float
    transition_quality: str
    filter_quality: str


class StateSpaceIterationCalibration(BaseModel):
    iterations_run: int
    max_iterations: int
    tolerance: float
    converged: bool
    final_parameter_delta: float
    summary: str
    path: list[StateSpaceIterationPoint] = Field(default_factory=list)


class StateSpaceValidationEpisode(BaseModel):
    key: str
    label: str
    period: str
    target_regime: str
    configured_regime: str
    calibrated_regime: str
    iterative_regime: str
    configured_rmse: float
    calibrated_rmse: float
    iterative_rmse: float
    winner: str


class StateSpaceValidationOverview(BaseModel):
    summary: str
    configured_hit_rate: float
    calibrated_hit_rate: float
    iterative_hit_rate: float
    configured_avg_rmse: float
    calibrated_avg_rmse: float
    iterative_avg_rmse: float
    episodes: list[StateSpaceValidationEpisode] = Field(default_factory=list)


class StateSpaceTrustGate(BaseModel):
    status: str
    base_blend_weight: float
    effective_blend_weight: float
    guardrail_factor: float
    configured_avg_rmse: float
    iterative_avg_rmse: float
    configured_hit_rate: float
    iterative_hit_rate: float
    summary: str


class StateSpaceClusterFocus(BaseModel):
    key: str
    label: str
    confidence: float
    summary: str
    supporting_episodes: list[str] = Field(default_factory=list)


class StateSpaceCalibrationOverview(BaseModel):
    method: str
    sample_size: int
    fit_rmse: float
    quality: str
    blend_weight: float
    base_blend_weight: float
    summary: str
    configured_regime: str
    configured_probability: float
    calibrated_regime: str
    calibrated_probability: float
    configured_probability_history: list[dict[str, Any]] = Field(default_factory=list)
    calibrated_probability_history: list[dict[str, Any]] = Field(default_factory=list)
    episodes: list[StateSpaceCalibrationEpisode] = Field(default_factory=list)
    cluster_focus: StateSpaceClusterFocus
    trust_gate: StateSpaceTrustGate
    transition: StateSpaceTransitionCalibration
    filter: StateSpaceFilterCalibration
    iteration: StateSpaceIterationCalibration
    validation: StateSpaceValidationOverview


class StateSpaceOverview(BaseModel):
    current_regime: str
    current_probability: float
    rule_agreement: bool
    agreement_summary: str
    observation_coverage: float
    innovation_stress: float
    states: list[StateSpaceState]
    state_history: list[dict[str, Any]] = Field(default_factory=list)
    probability_history: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: StateSpaceDiagnostics
    disagreement_history: list[StateSpaceDiagnosticPoint] = Field(default_factory=list)
    forecast: StateSpaceForecastOverview
    calibration: StateSpaceCalibrationOverview


class EpisodeClusterScore(BaseModel):
    key: str
    label: str
    similarity: float
    episode_count: int
    lead_regime: str


class EpisodeAnalog(BaseModel):
    key: str
    label: str
    period: str
    regime_bias: str
    cluster: str
    cluster_label: str
    similarity: float
    profile_similarity: float
    regime_similarity: float
    summary: str
    closest_matches: list[str]
    furthest_matches: list[str]
    regime_scores: dict[str, float]


class BacktestOverview(BaseModel):
    summary: str
    dominant_cluster: str
    dominant_cluster_label: str
    cluster_confidence: float
    clusters: list[EpisodeClusterScore] = Field(default_factory=list)
    episodes: list[EpisodeAnalog] = Field(default_factory=list)


class CausalNode(BaseModel):
    key: str
    label: str
    status: str
    score: float
    base_score: float | None = None
    incoming_pressure: float | None = None
    explanation: str


class CrisisSignal(BaseModel):
    key: str
    label: str
    value: float | None = None
    status: str
    explanation: str


class AlertItem(BaseModel):
    id: int | None = None
    timestamp: datetime
    severity: str
    title: str
    body: str
    related_indicators: list[str]
    next_stage_consequence: str


class NarrativeBlock(BaseModel):
    daily: str
    weekly: str
    escalation: str


class Panel(BaseModel):
    id: str
    title: str
    description: str
    indicators: list[IndicatorSnapshot]


class ManualInputItem(BaseModel):
    id: int | None = None
    timestamp: datetime
    key: str
    value: float
    notes: str = ''


class EventAnnotationItem(BaseModel):
    id: int | None = None
    timestamp: datetime
    title: str
    description: str
    related_series: list[str]
    severity: str


class OrderingStage(BaseModel):
    label: str
    score: float
    status: str
    confidence_score: float
    confidence_label: str


class OrderingFrameworkOverview(BaseModel):
    summary: str
    lead_stage: str
    lead_score: float
    lead_confidence_label: str
    items: list[OrderingStage] = Field(default_factory=list)


class StagflationOverview(BaseModel):
    summary: str
    composite_score: float
    status: str
    inflation_score: float
    growth_score: float
    policy_constraint_score: float


class MigrationOverview(BaseModel):
    summary: str
    physical_score: float
    domestic_score: float
    financial_score: float
    financial_minus_physical: float


class DashboardOverview(BaseModel):
    generated_at: datetime
    data_mode: str
    regime: RegimeOverview
    state_space: StateSpaceOverview
    backtest: BacktestOverview
    headline_indicators: list[IndicatorSnapshot]
    causal_chain: list[CausalNode]
    crisis_monitor: list[CrisisSignal]
    systemic_stress_alert: bool
    alerts: list[AlertItem]
    narratives: NarrativeBlock
    panels: dict[str, list[Panel]]
    manual_inputs: list[ManualInputItem]
    event_annotations: list[EventAnnotationItem]
    source_status: dict[str, str]
    interpretation_chart: InterpretationChart
    ordering_framework: OrderingFrameworkOverview
    stagflation_overview: StagflationOverview
    migration_overview: MigrationOverview
