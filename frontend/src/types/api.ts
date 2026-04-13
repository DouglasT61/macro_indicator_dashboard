export type StatusColor = 'green' | 'yellow' | 'orange' | 'red' | 'neutral';

export interface TimePoint {
  timestamp: string;
  value: number;
}

export interface IndicatorSnapshot {
  key: string;
  name: string;
  category: string;
  unit: string;
  source: string;
  source_class: 'live' | 'support' | 'proxy' | 'demo' | 'manual' | 'auto';
  latest_value: number | null;
  normalized_value: number | null;
  zscore: number | null;
  rate_of_change: number | null;
  acceleration: number | null;
  status: StatusColor;
  warning_threshold: number | null;
  critical_threshold: number | null;
  direction: 'high' | 'low';
  chart_style?: 'line' | 'step' | null;
  chart_window_label?: string | null;
  auction_breakdown?: Array<{
    key: string;
    label: string;
    weight: number;
    value: number;
  }> | null;
  model_contribution?: {
    sticky: number;
    convex: number;
    break: number;
  } | null;
  dominant_model_regime?: 'sticky' | 'convex' | 'break' | null;
  dominant_model_contribution?: number | null;
  narrative: string;
  history: TimePoint[];
}

export interface RegimeCard {
  name: string;
  score: number;
  change_7d: number;
  change_30d: number;
  propagation_boost: number;
  top_drivers: string[];
}

export interface RegimeOverview {
  current_regime: string;
  sticky: RegimeCard;
  convex: RegimeCard;
  break: RegimeCard;
  explanation: {
    current_regime: 'sticky' | 'convex' | 'break';
    summary: Record<string, string[]>;
    propagation?: Record<string, unknown>;
  };
  history: Array<{
    timestamp: string;
    sticky_score: number;
    convex_score: number;
    break_score: number;
  }>;
}

export interface StateSpaceState {
  key: string;
  label: string;
  value: number;
  change_7d: number;
  uncertainty: number;
  dominant_measurements: string[];
}

export interface StateSpaceHistoryPoint {
  timestamp: string;
  [key: string]: string | number;
}

export interface StateSpaceProbabilityPoint {
  timestamp: string;
  sticky: number;
  convex: number;
  break: number;
}

export interface StateSpaceDiagnosticPoint {
  timestamp: string;
  dominant_regime: 'sticky' | 'convex' | 'break';
  dominant_probability: number;
  probability_gap: number;
  aligned_with_rule: boolean;
}

export interface StateSpaceDiagnostics {
  recent_disagreement_streak: number;
  dominant_regime_flips: number;
  max_probability_gap: number;
  latest_probability_gap: number;
  confidence_band: string;
  tracking_quality: string;
}

export interface StateSpaceForecastPoint {
  step: number;
  timestamp: string;
  sticky: number;
  convex: number;
  break: number;
}

export interface StateSpaceForecastHorizon {
  days: number;
  dominant_regime: 'sticky' | 'convex' | 'break' | string;
  dominant_probability: number;
  sticky: number;
  convex: number;
  break: number;
}

export interface StateSpaceScenario {
  key: string;
  label: string;
  description: string;
  dominant_regime: 'sticky' | 'convex' | 'break' | string;
  dominant_probability: number;
  sticky: number;
  convex: number;
  break: number;
  state_impulse_summary: string;
}

export interface StateSpaceForecastOverview {
  summary: string;
  conditioning_cluster: string;
  conditioning_label: string;
  conditioning_confidence: number;
  conditioning_summary: string;
  baseline_path: StateSpaceForecastPoint[];
  horizons: StateSpaceForecastHorizon[];
  scenarios: StateSpaceScenario[];
}

export interface StateSpaceCalibrationEpisode {
  key: string;
  label: string;
  period: string;
  target_regime: 'sticky' | 'convex' | 'break' | string;
  calibrated_regime: 'sticky' | 'convex' | 'break' | string;
  fit_score: number;
  rmse: number;
  sticky: number;
  convex: number;
  break: number;
}

export interface StateSpaceTransitionLink {
  source: string;
  target: string;
  configured_weight: number;
  fitted_weight: number;
  blended_weight: number;
  delta: number;
}

export interface StateSpaceTransitionCalibration {
  fit_rmse: number;
  quality: string;
  blend_weight: number;
  summary: string;
  configured_persistence: number;
  fitted_persistence: number;
  blended_persistence: number;
  drift_strength: number;
  links: StateSpaceTransitionLink[];
}

export interface StateSpaceFilterObservation {
  indicator: string;
  configured_primary_state: string;
  fitted_primary_state: string;
  rmse: number;
  residual_variance: number;
}

export interface StateSpaceObservationConditioning {
  cluster_key: string;
  cluster_label: string;
  cluster_confidence: number;
  regime_key: string;
  regime_probability: number;
  average_trust: number;
  boosted_indicators: string[];
  reduced_indicators: string[];
  summary: string;
}

export interface StateSpaceFilterCalibration {
  fit_rmse: number;
  quality: string;
  blend_weight: number;
  summary: string;
  configured_noise_floor: number;
  fitted_noise_floor: number;
  blended_noise_floor: number;
  configured_process_noise: number;
  fitted_process_noise: number;
  blended_process_noise: number;
  observations: StateSpaceFilterObservation[];
  observation_conditioning: StateSpaceObservationConditioning;
}

export interface StateSpaceIterationPoint {
  iteration: number;
  transition_rmse: number;
  filter_rmse: number;
  parameter_delta: number;
  dominant_regime: string;
  dominant_probability: number;
  transition_quality: string;
  filter_quality: string;
}

export interface StateSpaceIterationCalibration {
  iterations_run: number;
  max_iterations: number;
  tolerance: number;
  converged: boolean;
  final_parameter_delta: number;
  summary: string;
  path: StateSpaceIterationPoint[];
}

export interface StateSpaceValidationEpisode {
  key: string;
  label: string;
  period: string;
  target_regime: string;
  configured_regime: string;
  calibrated_regime: string;
  iterative_regime: string;
  configured_rmse: number;
  calibrated_rmse: number;
  iterative_rmse: number;
  winner: string;
}

export interface StateSpaceValidationOverview {
  summary: string;
  configured_hit_rate: number;
  calibrated_hit_rate: number;
  iterative_hit_rate: number;
  configured_avg_rmse: number;
  calibrated_avg_rmse: number;
  iterative_avg_rmse: number;
  episodes: StateSpaceValidationEpisode[];
}

export interface StateSpaceTrustGate {
  status: string;
  base_blend_weight: number;
  effective_blend_weight: number;
  guardrail_factor: number;
  configured_avg_rmse: number;
  iterative_avg_rmse: number;
  configured_hit_rate: number;
  iterative_hit_rate: number;
  summary: string;
}

export interface StateSpaceClusterFocus {
  key: string;
  label: string;
  confidence: number;
  summary: string;
  supporting_episodes: string[];
}

export interface StateSpaceCalibrationOverview {
  method: string;
  sample_size: number;
  fit_rmse: number;
  quality: string;
  blend_weight: number;
  base_blend_weight: number;
  summary: string;
  configured_regime: 'sticky' | 'convex' | 'break' | string;
  configured_probability: number;
  calibrated_regime: 'sticky' | 'convex' | 'break' | string;
  calibrated_probability: number;
  configured_probability_history: StateSpaceProbabilityPoint[];
  calibrated_probability_history: StateSpaceProbabilityPoint[];
  episodes: StateSpaceCalibrationEpisode[];
  cluster_focus: StateSpaceClusterFocus;
  trust_gate: StateSpaceTrustGate;
  transition: StateSpaceTransitionCalibration;
  filter: StateSpaceFilterCalibration;
  iteration: StateSpaceIterationCalibration;
  validation: StateSpaceValidationOverview;
}

export interface StateSpaceOverview {
  current_regime: string;
  current_probability: number;
  rule_agreement: boolean;
  agreement_summary: string;
  observation_coverage: number;
  innovation_stress: number;
  states: StateSpaceState[];
  state_history: StateSpaceHistoryPoint[];
  probability_history: StateSpaceProbabilityPoint[];
  diagnostics: StateSpaceDiagnostics;
  disagreement_history: StateSpaceDiagnosticPoint[];
  forecast: StateSpaceForecastOverview;
  calibration: StateSpaceCalibrationOverview;
}

export interface EpisodeClusterScore {
  key: string;
  label: string;
  similarity: number;
  episode_count: number;
  lead_regime: string;
}

export interface EpisodeAnalog {
  key: string;
  label: string;
  period: string;
  regime_bias: 'sticky' | 'convex' | 'break' | string;
  cluster: string;
  cluster_label: string;
  similarity: number;
  profile_similarity: number;
  regime_similarity: number;
  summary: string;
  closest_matches: string[];
  furthest_matches: string[];
  regime_scores: Record<'sticky' | 'convex' | 'break', number>;
}

export interface BacktestOverview {
  summary: string;
  dominant_cluster: string;
  dominant_cluster_label: string;
  cluster_confidence: number;
  clusters: EpisodeClusterScore[];
  episodes: EpisodeAnalog[];
}

export interface CausalNode {
  key: string;
  label: string;
  status: StatusColor;
  score: number;
  base_score: number | null;
  incoming_pressure: number | null;
  explanation: string;
}

export interface CrisisSignal {
  key: string;
  label: string;
  value: number | null;
  status: StatusColor;
  explanation: string;
}

export interface AlertItem {
  id?: number;
  timestamp: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  body: string;
  related_indicators: string[];
  next_stage_consequence: string;
}

export interface NarrativeBlock {
  daily: string;
  weekly: string;
  escalation: string;
}

export interface Panel {
  id: string;
  title: string;
  description: string;
  indicators: IndicatorSnapshot[];
}

export interface ManualInputItem {
  id?: number;
  timestamp: string;
  key: string;
  value: number;
  notes: string;
}

export interface EventAnnotationItem {
  id?: number;
  timestamp: string;
  title: string;
  description: string;
  related_series: string[];
  severity: 'info' | 'warning' | 'critical';
}

export interface ThresholdLine {
  label: string;
  value: number;
  color: string;
}

export interface OrderingStage {
  label: string;
  score: number;
  status: string;
  confidence_score: number;
  confidence_label: string;
}

export interface OrderingFrameworkOverview {
  summary: string;
  lead_stage: string;
  lead_score: number;
  lead_confidence_label: string;
  items: OrderingStage[];
}

export interface StagflationOverview {
  summary: string;
  composite_score: number;
  status: string;
  inflation_score: number;
  growth_score: number;
  policy_constraint_score: number;
}

export interface MigrationOverview {
  summary: string;
  lead_stage: string;
  lead_score: number;
  lead_confidence_label: string;
  items: OrderingStage[];
}


export interface HormuzTrafficStats {
  latest_count: number;
  avg_30d: number;
  avg_longterm: number;
  latest_date: string;
  source: string;
}

export interface DashboardOverview {
  generated_at: string;
  data_mode: string;
  regime: RegimeOverview;
  state_space: StateSpaceOverview;
  backtest: BacktestOverview;
  headline_indicators: IndicatorSnapshot[];
  causal_chain: CausalNode[];
  crisis_monitor: CrisisSignal[];
  systemic_stress_alert: boolean;
  alerts: AlertItem[];
  narratives: NarrativeBlock;
  panels: Record<string, Panel[]>;
  manual_inputs: ManualInputItem[];
  event_annotations: EventAnnotationItem[];
  source_status: Record<string, string>;
  interpretation_chart: {
    series: TimePoint[];
    thresholds: ThresholdLine[];
  };
  ordering_framework: OrderingFrameworkOverview;
  stagflation_overview: StagflationOverview;
  migration_overview: MigrationOverview;
  hormuz_traffic: HormuzTrafficStats | null;
}

export interface SettingsResponse {
  updated_at: string;
  config: Record<string, unknown>;
  alerts_enabled: boolean;
}
