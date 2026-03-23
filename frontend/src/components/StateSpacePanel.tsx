import { LineChart } from '../charts/LineChart';
import type { StateSpaceOverview, StatusColor } from '../types/api';

interface StateSpacePanelProps {
  stateSpace: StateSpaceOverview;
}

const STATE_COLORS: Record<string, string> = {
  oil_shock: '#f97316',
  funding_stress: '#38bdf8',
  treasury_stress: '#ef4444',
  intervention_pressure: '#a78bfa',
  repression_risk: '#facc15',
};

function agreementTone(stateSpace: StateSpaceOverview): StatusColor {
  if (!stateSpace.rule_agreement && stateSpace.current_probability >= 45) {
    return 'orange';
  }
  if (stateSpace.current_probability >= 55) {
    return 'red';
  }
  if (stateSpace.current_probability >= 40) {
    return 'yellow';
  }
  return 'green';
}

function regimeTone(regime: string): StatusColor {
  if (regime === 'break') {
    return 'red';
  }
  if (regime === 'convex') {
    return 'orange';
  }
  return 'yellow';
}

function qualityTone(quality: string): StatusColor {
  if (quality === 'Strong') {
    return 'green';
  }
  if (quality === 'Usable') {
    return 'yellow';
  }
  return 'orange';
}

function leadProbability(row: { sticky: number; convex: number; break: number }) {
  return Math.max(row.sticky, row.convex, row.break);
}

export function StateSpacePanel({ stateSpace }: StateSpacePanelProps) {
  const tone = agreementTone(stateSpace);
  const transition = stateSpace.calibration.transition;
  const filter = stateSpace.calibration.filter;
  const observationConditioning = filter.observation_conditioning;
  const iteration = stateSpace.calibration.iteration;
  const validation = stateSpace.calibration.validation;
  const trustGate = stateSpace.calibration.trust_gate;
  const clusterFocus = stateSpace.calibration.cluster_focus;

  const probabilitySeries = [
    {
      name: 'Sticky Probability',
      color: '#f59e0b',
      values: stateSpace.probability_history.map((row) => ({ timestamp: row.timestamp, value: row.sticky })),
    },
    {
      name: 'Convex Probability',
      color: '#38bdf8',
      values: stateSpace.probability_history.map((row) => ({ timestamp: row.timestamp, value: row.convex })),
    },
    {
      name: 'Break Probability',
      color: '#ef4444',
      values: stateSpace.probability_history.map((row) => ({ timestamp: row.timestamp, value: row.break })),
    },
  ];

  const latentSeries = stateSpace.states.map((state) => ({
    name: state.label,
    color: STATE_COLORS[state.key] ?? '#cbd5e1',
    values: stateSpace.state_history.map((row) => ({
      timestamp: row.timestamp,
      value: Number(row[state.key] ?? 0),
    })),
  }));

  const disagreementSeries = [
    {
      name: 'Probability Gap',
      color: '#7dd3fc',
      values: stateSpace.disagreement_history.map((row) => ({ timestamp: row.timestamp, value: row.probability_gap })),
    },
  ];

  const forecastSeries = [
    {
      name: 'Sticky Forward',
      color: '#f59e0b',
      values: stateSpace.forecast.baseline_path.map((row) => ({ timestamp: row.timestamp, value: row.sticky })),
    },
    {
      name: 'Convex Forward',
      color: '#38bdf8',
      values: stateSpace.forecast.baseline_path.map((row) => ({ timestamp: row.timestamp, value: row.convex })),
    },
    {
      name: 'Break Forward',
      color: '#ef4444',
      values: stateSpace.forecast.baseline_path.map((row) => ({ timestamp: row.timestamp, value: row.break })),
    },
  ];

  const calibrationSeries = [
    {
      name: 'Configured Lead',
      color: '#64748b',
      values: stateSpace.calibration.configured_probability_history.map((row) => ({ timestamp: row.timestamp, value: leadProbability(row) })),
    },
    {
      name: 'Calibrated Lead',
      color: '#22c55e',
      values: stateSpace.calibration.calibrated_probability_history.map((row) => ({ timestamp: row.timestamp, value: leadProbability(row) })),
    },
  ];

  return (
    <section className="panel-shell state-space-shell">
      <div className="panel-shell__header">
        <div>
          <h2>Econometric Layer</h2>
          <p>{stateSpace.agreement_summary}</p>
        </div>
        <div className={`status-pill status-pill--${tone}`}>
          {stateSpace.current_regime.replace('_', ' ')} {stateSpace.current_probability.toFixed(1)}%
        </div>
      </div>

      <div className="state-space-metrics">
        <article className="state-space-metric-card">
          <span className="state-space-metric-card__label">Rule Agreement</span>
          <strong>{stateSpace.rule_agreement ? 'Aligned' : 'Diverging'}</strong>
        </article>
        <article className="state-space-metric-card">
          <span className="state-space-metric-card__label">Observation Coverage</span>
          <strong>{stateSpace.observation_coverage.toFixed(1)}%</strong>
        </article>
        <article className="state-space-metric-card">
          <span className="state-space-metric-card__label">Innovation Stress</span>
          <strong>{stateSpace.innovation_stress.toFixed(2)}</strong>
        </article>
        <article className="state-space-metric-card">
          <span className="state-space-metric-card__label">Confidence Band</span>
          <strong>{stateSpace.diagnostics.confidence_band}</strong>
        </article>
        <article className="state-space-metric-card">
          <span className="state-space-metric-card__label">Regime Flips</span>
          <strong>{stateSpace.diagnostics.dominant_regime_flips}</strong>
        </article>
        <article className="state-space-metric-card">
          <span className="state-space-metric-card__label">Tracking Quality</span>
          <strong>{stateSpace.diagnostics.tracking_quality}</strong>
        </article>
      </div>

      <div className="state-space-grid">
        {stateSpace.states.map((state) => (
          <article key={state.key} className="state-space-card">
            <div className="state-space-card__header">
              <h3>{state.label}</h3>
              <span>{state.uncertainty.toFixed(1)} sigma</span>
            </div>
            <div className="state-space-card__value">{state.value.toFixed(1)}</div>
            <div className="state-space-card__change">7d {state.change_7d >= 0 ? '+' : ''}{state.change_7d.toFixed(1)}</div>
            <ul className="state-space-card__list">
              {state.dominant_measurements.map((measurement) => (
                <li key={measurement}>{measurement}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <div className="state-space-chart-grid">
        <LineChart title="Latent State History" series={latentSeries} height={220} />
        <LineChart
          title="Econometric Regime Probabilities"
          series={probabilitySeries}
          height={220}
          thresholdLines={[
            { label: 'Watch', value: 40, color: '#facc15' },
            { label: 'Dominant', value: 55, color: '#ef4444' },
          ]}
        />
      </div>

      <div className="state-space-chart-grid state-space-chart-grid--compact">
        <LineChart
          title="Rule vs Econometric Gap"
          series={disagreementSeries}
          height={180}
          thresholdLines={[
            { label: 'Fragile', value: 10, color: '#facc15' },
            { label: 'High Conviction', value: 20, color: '#ef4444' },
          ]}
        />
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Diagnostics Summary</h3>
            <span>{stateSpace.diagnostics.latest_probability_gap.toFixed(1)} pt gap</span>
          </div>
          <div className="state-space-diagnostics-list">
            <div><span>Recent disagreement streak</span><strong>{stateSpace.diagnostics.recent_disagreement_streak}</strong></div>
            <div><span>Max probability gap</span><strong>{stateSpace.diagnostics.max_probability_gap.toFixed(1)}</strong></div>
            <div><span>Latest probability gap</span><strong>{stateSpace.diagnostics.latest_probability_gap.toFixed(1)}</strong></div>
            <div><span>Current model confidence</span><strong>{stateSpace.current_probability.toFixed(1)}%</strong></div>
          </div>
        </article>
      </div>

      <div className="state-space-forecast-header">
        <div>
          <h3>Calibration Layer</h3>
          <p>{stateSpace.calibration.summary}</p>
        </div>
      </div>

      <div className="state-space-forecast-grid">
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(stateSpace.calibration.quality)}`}>
          <div className="state-space-card__header">
            <h3>Calibration Quality</h3>
            <span>{stateSpace.calibration.sample_size} episodes</span>
          </div>
          <div className="state-space-card__value">{stateSpace.calibration.quality}</div>
          <div className="state-space-card__metrics-inline">
            <span>RMSE {stateSpace.calibration.fit_rmse.toFixed(1)}</span>
            <span>Base {(stateSpace.calibration.base_blend_weight * 100).toFixed(0)}%</span>
            <span>Live {(stateSpace.calibration.blend_weight * 100).toFixed(0)}%</span>
          </div>
        </article>
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(trustGate.status === 'Open' ? 'Strong' : trustGate.status === 'Reduced' ? 'Usable' : 'Fragile')}`}>
          <div className="state-space-card__header">
            <h3>Validation Trust Gate</h3>
            <span>{trustGate.status}</span>
          </div>
          <p className="state-space-card__summary">{trustGate.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Factor {(trustGate.guardrail_factor * 100).toFixed(0)}%</span>
            <span>Cfg RMSE {trustGate.configured_avg_rmse.toFixed(1)}</span>
            <span>Iter RMSE {trustGate.iterative_avg_rmse.toFixed(1)}</span>
          </div>
        </article>
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(clusterFocus.confidence >= 0.55 ? 'Strong' : clusterFocus.confidence >= 0.3 ? 'Usable' : 'Fragile')}`}>
          <div className="state-space-card__header">
            <h3>Subfamily Focus</h3>
            <span>{clusterFocus.label}</span>
          </div>
          <p className="state-space-card__summary">{clusterFocus.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Confidence {(clusterFocus.confidence * 100).toFixed(0)}%</span>
            <span>Support {clusterFocus.supporting_episodes.length}</span>
          </div>
        </article>
        <article className={`state-space-card state-space-card--forecast state-space-card--${regimeTone(stateSpace.calibration.configured_regime)}`}>
          <div className="state-space-card__header">
            <h3>Configured Read</h3>
            <span>{stateSpace.calibration.configured_regime.replace('_', ' ')}</span>
          </div>
          <div className="state-space-card__value">{stateSpace.calibration.configured_probability.toFixed(1)}%</div>
          <div className="state-space-card__change">Hand-specified regime loadings only</div>
        </article>
        <article className={`state-space-card state-space-card--forecast state-space-card--${regimeTone(stateSpace.calibration.calibrated_regime)}`}>
          <div className="state-space-card__header">
            <h3>Calibrated Read</h3>
            <span>{stateSpace.calibration.calibrated_regime.replace('_', ' ')}</span>
          </div>
          <div className="state-space-card__value">{stateSpace.calibration.calibrated_probability.toFixed(1)}%</div>
          <div className="state-space-card__change">Historical episode fit only</div>
        </article>
      </div>

      <div className="state-space-calibration-grid">
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(transition.quality)}`}>
          <div className="state-space-card__header">
            <h3>Transition Fit</h3>
            <span>{transition.quality}</span>
          </div>
          <p className="state-space-card__summary">{transition.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>RMSE {transition.fit_rmse.toFixed(1)}</span>
            <span>Blend {(transition.blend_weight * 100).toFixed(0)}%</span>
            <span>Drift {transition.drift_strength.toFixed(2)}</span>
          </div>
        </article>
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Persistence Shift</h3>
            <span>{transition.links.length} links</span>
          </div>
          <div className="state-space-diagnostics-list">
            <div><span>Configured persistence</span><strong>{transition.configured_persistence.toFixed(2)}</strong></div>
            <div><span>Fitted persistence</span><strong>{transition.fitted_persistence.toFixed(2)}</strong></div>
            <div><span>Blended persistence</span><strong>{transition.blended_persistence.toFixed(2)}</strong></div>
            <div><span>Drift strength</span><strong>{transition.drift_strength.toFixed(2)}</strong></div>
          </div>
        </article>
      </div>

      <div className="state-space-calibration-grid">
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(filter.quality)}`}>
          <div className="state-space-card__header">
            <h3>Filter Fit</h3>
            <span>{filter.quality}</span>
          </div>
          <p className="state-space-card__summary">{filter.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Obs RMSE {filter.fit_rmse.toFixed(1)}</span>
            <span>Blend {(filter.blend_weight * 100).toFixed(0)}%</span>
            <span>Noise floor {filter.blended_noise_floor.toFixed(1)}</span>
          </div>
        </article>
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(observationConditioning.average_trust >= 1.08 ? 'Strong' : observationConditioning.average_trust >= 0.98 ? 'Usable' : 'Fragile')}`}>
          <div className="state-space-card__header">
            <h3>Observation Weighting</h3>
            <span>{observationConditioning.cluster_label}</span>
          </div>
          <p className="state-space-card__summary">{observationConditioning.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Trust {observationConditioning.average_trust.toFixed(2)}x</span>
            <span>Cluster {(observationConditioning.cluster_confidence * 100).toFixed(0)}%</span>
            <span>Regime {observationConditioning.regime_key}</span>
          </div>
        </article>
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Noise Refit</h3>
            <span>{filter.observations.length} observations</span>
          </div>
          <div className="state-space-diagnostics-list">
            <div><span>Configured noise floor</span><strong>{filter.configured_noise_floor.toFixed(1)}</strong></div>
            <div><span>Fitted noise floor</span><strong>{filter.fitted_noise_floor.toFixed(1)}</strong></div>
            <div><span>Blended noise floor</span><strong>{filter.blended_noise_floor.toFixed(1)}</strong></div>
            <div><span>Avg process noise</span><strong>{filter.blended_process_noise.toFixed(1)}</strong></div>
          </div>
        </article>
      </div>

      <div className="state-space-calibration-grid">
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Boosted Measurements</h3>
            <span>{observationConditioning.boosted_indicators.length} items</span>
          </div>
          <div className="state-space-transition-list">
            {observationConditioning.boosted_indicators.map((item) => (
              <div key={item} className="state-space-transition-row">
                <div>
                  <strong>{item}</strong>
                  <span>Higher trust in this context</span>
                </div>
              </div>
            ))}
          </div>
        </article>
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Reduced Measurements</h3>
            <span>{observationConditioning.reduced_indicators.length} items</span>
          </div>
          <div className="state-space-transition-list">
            {observationConditioning.reduced_indicators.map((item) => (
              <div key={item} className="state-space-transition-row">
                <div>
                  <strong>{item}</strong>
                  <span>Lower trust in this context</span>
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="state-space-calibration-grid">
        <article className={`state-space-card state-space-card--forecast state-space-card--${iteration.converged ? 'green' : 'yellow'}`}>
          <div className="state-space-card__header">
            <h3>Iterative Estimation</h3>
            <span>{iteration.converged ? 'Converged' : 'Max passes'}</span>
          </div>
          <p className="state-space-card__summary">{iteration.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Passes {iteration.iterations_run}/{iteration.max_iterations}</span>
            <span>Tolerance {iteration.tolerance.toFixed(4)}</span>
            <span>Final delta {iteration.final_parameter_delta.toFixed(4)}</span>
          </div>
        </article>
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Iteration Path</h3>
            <span>{iteration.path.length} rows</span>
          </div>
          <div className="state-space-transition-list">
            {iteration.path.map((step) => (
              <div key={step.iteration} className="state-space-transition-row">
                <div>
                  <strong>Pass {step.iteration}</strong>
                  <span>{step.dominant_regime.replace(/_/g, ' ')} {step.dominant_probability.toFixed(1)}%</span>
                </div>
                <div className="state-space-transition-row__metrics">
                  <span>T-RMSE {step.transition_rmse.toFixed(1)}</span>
                  <span>F-RMSE {step.filter_rmse.toFixed(1)}</span>
                  <strong>{step.parameter_delta.toFixed(4)}</strong>
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="state-space-calibration-grid">
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(validation.iterative_avg_rmse <= validation.calibrated_avg_rmse ? 'Strong' : 'Usable')}`}>
          <div className="state-space-card__header">
            <h3>Out-of-Sample Validation</h3>
            <span>leave-one-out</span>
          </div>
          <p className="state-space-card__summary">{validation.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Cfg hit {validation.configured_hit_rate.toFixed(0)}%</span>
            <span>Cal hit {validation.calibrated_hit_rate.toFixed(0)}%</span>
            <span>Iter hit {validation.iterative_hit_rate.toFixed(0)}%</span>
          </div>
        </article>
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Validation RMSE</h3>
            <span>{validation.episodes.length} episodes</span>
          </div>
          <div className="state-space-diagnostics-list">
            <div><span>Configured avg</span><strong>{validation.configured_avg_rmse.toFixed(1)}</strong></div>
            <div><span>Calibrated avg</span><strong>{validation.calibrated_avg_rmse.toFixed(1)}</strong></div>
            <div><span>Iterative avg</span><strong>{validation.iterative_avg_rmse.toFixed(1)}</strong></div>
            <div><span>Live blend after gate</span><strong>{(trustGate.effective_blend_weight * 100).toFixed(0)}%</strong></div>
          </div>
        </article>
      </div>

      <div className="state-space-scenario-grid">
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Validation Episodes</h3>
            <span>winner by RMSE</span>
          </div>
          <div className="state-space-transition-list">
            {validation.episodes.map((episode) => (
              <div key={episode.key} className="state-space-transition-row">
                <div>
                  <strong>{episode.label}</strong>
                  <span>{episode.target_regime} | winner {episode.winner}</span>
                </div>
                <div className="state-space-transition-row__metrics">
                  <span>C {episode.configured_rmse.toFixed(1)}</span>
                  <span>Cal {episode.calibrated_rmse.toFixed(1)}</span>
                  <strong>I {episode.iterative_rmse.toFixed(1)}</strong>
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="state-space-chart-grid state-space-chart-grid--compact">
        <LineChart title="Configured vs Calibrated Lead Probability" series={calibrationSeries} height={180} />
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Transition Rewiring</h3>
            <span>top deltas</span>
          </div>
          <div className="state-space-transition-list">
            {transition.links.map((link) => (
              <div key={`${link.source}-${link.target}`} className="state-space-transition-row">
                <div>
                  <strong>{link.source.replace(/_/g, ' ')}</strong>
                  <span>{link.target.replace(/_/g, ' ')}</span>
                </div>
                <div className="state-space-transition-row__metrics">
                  <span>Cfg {link.configured_weight.toFixed(2)}</span>
                  <span>Fit {link.fitted_weight.toFixed(2)}</span>
                  <span>Blend {link.blended_weight.toFixed(2)}</span>
                  <strong>{link.delta >= 0 ? '+' : ''}{link.delta.toFixed(2)}</strong>
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="state-space-scenario-grid">
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Observation Rewiring</h3>
            <span>top noisy indicators</span>
          </div>
          <div className="state-space-transition-list">
            {filter.observations.map((observation) => (
              <div key={observation.indicator} className="state-space-transition-row">
                <div>
                  <strong>{observation.indicator.replace(/_/g, ' ')}</strong>
                  <span>{observation.configured_primary_state.replace(/_/g, ' ')}{' -> '}{observation.fitted_primary_state.replace(/_/g, ' ')}</span>
                </div>
                <div className="state-space-transition-row__metrics">
                  <span>RMSE {observation.rmse.toFixed(1)}</span>
                  <span>Var {observation.residual_variance.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="state-space-chart-grid state-space-chart-grid--compact">
        <div className="state-space-scenario-grid">
          {stateSpace.calibration.episodes.map((episode) => (
            <article key={episode.key} className={`state-space-card state-space-card--scenario state-space-card--${regimeTone(episode.calibrated_regime)}`}>
              <div className="state-space-card__header">
                <h3>{episode.label}</h3>
                <span>{episode.period}</span>
              </div>
              <div className="state-space-card__metrics-inline">
                <span>Target {episode.target_regime}</span>
                <span>Fit {episode.calibrated_regime}</span>
              </div>
              <div className="state-space-card__value">{episode.fit_score.toFixed(1)}</div>
              <div className="state-space-card__metrics-inline">
                <span>RMSE {episode.rmse.toFixed(1)}</span>
                <span>Sticky {episode.sticky.toFixed(1)}</span>
                <span>Convex {episode.convex.toFixed(1)}</span>
                <span>Break {episode.break.toFixed(1)}</span>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="state-space-forecast-header">
        <div>
          <h3>Forecast Layer</h3>
          <p>{stateSpace.forecast.summary}</p>
        </div>
      </div>

      <div className="state-space-forecast-grid">
        <article className={`state-space-card state-space-card--forecast state-space-card--${qualityTone(stateSpace.forecast.conditioning_confidence >= 0.55 ? 'Strong' : stateSpace.forecast.conditioning_confidence >= 0.3 ? 'Usable' : 'Fragile')}`}>
          <div className="state-space-card__header">
            <h3>Forecast Conditioning</h3>
            <span>{stateSpace.forecast.conditioning_label}</span>
          </div>
          <p className="state-space-card__summary">{stateSpace.forecast.conditioning_summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Confidence {(stateSpace.forecast.conditioning_confidence * 100).toFixed(0)}%</span>
            <span>Cluster {stateSpace.forecast.conditioning_cluster}</span>
          </div>
        </article>
        {stateSpace.forecast.horizons.map((horizon) => (
          <article key={horizon.days} className={`state-space-card state-space-card--forecast state-space-card--${regimeTone(horizon.dominant_regime)}`}>
            <div className="state-space-card__header">
              <h3>{horizon.days}d Horizon</h3>
              <span>{horizon.dominant_regime.replace('_', ' ')}</span>
            </div>
            <div className="state-space-card__value">{horizon.dominant_probability.toFixed(1)}%</div>
            <div className="state-space-card__metrics-inline">
              <span>Sticky {horizon.sticky.toFixed(1)}</span>
              <span>Convex {horizon.convex.toFixed(1)}</span>
              <span>Break {horizon.break.toFixed(1)}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="state-space-chart-grid state-space-chart-grid--compact">
        <LineChart
          title="Baseline Forward Probabilities"
          series={forecastSeries}
          height={180}
          thresholdLines={[
            { label: 'Watch', value: 40, color: '#facc15' },
            { label: 'Dominant', value: 55, color: '#ef4444' },
          ]}
        />
        <div className="state-space-scenario-grid">
          {stateSpace.forecast.scenarios.map((scenario) => (
            <article key={scenario.key} className={`state-space-card state-space-card--scenario state-space-card--${regimeTone(scenario.dominant_regime)}`}>
              <div className="state-space-card__header">
                <h3>{scenario.label}</h3>
                <span>{scenario.dominant_regime.replace('_', ' ')}</span>
              </div>
              <p className="state-space-card__summary">{scenario.description}</p>
              <div className="state-space-card__value">{scenario.dominant_probability.toFixed(1)}%</div>
              <div className="state-space-card__metrics-inline">
                <span>Sticky {scenario.sticky.toFixed(1)}</span>
                <span>Convex {scenario.convex.toFixed(1)}</span>
                <span>Break {scenario.break.toFixed(1)}</span>
              </div>
              <div className="state-space-card__change">Impulse {scenario.state_impulse_summary}</div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
