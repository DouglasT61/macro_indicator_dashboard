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

export function StateSpacePanel({ stateSpace }: StateSpacePanelProps) {
  const tone = agreementTone(stateSpace);
  const observationConditioning = stateSpace.calibration.filter.observation_conditioning;

  const latentSeries = stateSpace.states.map((state) => ({
    name: state.label,
    color: STATE_COLORS[state.key] ?? '#cbd5e1',
    values: stateSpace.state_history.map((row) => ({
      timestamp: row.timestamp,
      value: Number(row[state.key] ?? 0),
    })),
  }));

  const confidenceSeries = [
    {
      name: 'Sticky Share',
      color: '#f59e0b',
      values: stateSpace.probability_history.map((row) => ({ timestamp: row.timestamp, value: row.sticky })),
    },
    {
      name: 'Convex Share',
      color: '#38bdf8',
      values: stateSpace.probability_history.map((row) => ({ timestamp: row.timestamp, value: row.convex })),
    },
    {
      name: 'Break Share',
      color: '#ef4444',
      values: stateSpace.probability_history.map((row) => ({ timestamp: row.timestamp, value: row.break })),
    },
  ];

  const disagreementSeries = [
    {
      name: 'Share Gap',
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

  return (
    <section className="panel-shell state-space-shell">
      <div className="panel-shell__header">
        <div>
          <h2>Latent-State Layer</h2>
          <p>{stateSpace.agreement_summary}</p>
        </div>
        <div className={`status-pill status-pill--${tone}`}>
          {stateSpace.current_regime.replace('_', ' ')} {stateSpace.current_probability.toFixed(1)}% share
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
          <span className="state-space-metric-card__label">Dispersion Band</span>
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
          title="Regime Share"
          series={confidenceSeries}
          height={220}
          thresholdLines={[
            { label: 'Building', value: 40, color: '#facc15' },
            { label: 'Leading', value: 55, color: '#ef4444' },
          ]}
        />
      </div>

      <div className="state-space-chart-grid state-space-chart-grid--compact">
        <LineChart
          title="Rule vs Latent-State Share Gap"
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
            <div><span>Max share gap</span><strong>{stateSpace.diagnostics.max_probability_gap.toFixed(1)}</strong></div>
            <div><span>Latest share gap</span><strong>{stateSpace.diagnostics.latest_probability_gap.toFixed(1)}</strong></div>
            <div><span>Current regime share</span><strong>{stateSpace.current_probability.toFixed(1)}%</strong></div>
          </div>
        </article>
      </div>

      <div className="state-space-forecast-header">
        <div>
          <h3>Configured Model Notes</h3>
          <p>{stateSpace.calibration.summary}</p>
        </div>
      </div>

      <div className="state-space-forecast-grid">
        <article className={`state-space-card state-space-card--forecast state-space-card--${regimeTone(stateSpace.calibration.configured_regime)}`}>
          <div className="state-space-card__header">
            <h3>Configured Read</h3>
            <span>{stateSpace.calibration.configured_regime.replace('_', ' ')}</span>
          </div>
          <div className="state-space-card__value">{stateSpace.calibration.configured_probability.toFixed(1)}%</div>
          <div className="state-space-card__change">Relative regime share from the configured latent-state filter</div>
        </article>
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Episode Context</h3>
            <span>{stateSpace.calibration.cluster_focus.label}</span>
          </div>
          <p className="state-space-card__summary">{stateSpace.calibration.cluster_focus.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Weight {(stateSpace.calibration.cluster_focus.confidence * 100).toFixed(0)}%</span>
            <span>Support {stateSpace.calibration.cluster_focus.supporting_episodes.length}</span>
          </div>
        </article>
        <article className="state-space-card state-space-card--diagnostics">
          <div className="state-space-card__header">
            <h3>Observation Weighting</h3>
            <span>{observationConditioning.cluster_label}</span>
          </div>
          <p className="state-space-card__summary">{observationConditioning.summary}</p>
          <div className="state-space-card__metrics-inline">
            <span>Avg trust {observationConditioning.average_trust.toFixed(2)}</span>
            <span>Boosted {observationConditioning.boosted_indicators.length}</span>
          </div>
        </article>
      </div>

      <div className="state-space-forecast-header">
        <div>
          <h3>Forward Regime Balance</h3>
          <p>{stateSpace.forecast.summary}</p>
        </div>
      </div>

      <div className="state-space-forecast-grid">
        <article className="state-space-card state-space-card--diagnostics">
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
            <div className="state-space-card__change">Relative regime share</div>
            <div className="state-space-card__metrics-inline">
              <span>Sticky {horizon.sticky.toFixed(1)}</span>
              <span>Convex {horizon.convex.toFixed(1)}</span>
              <span>Break {horizon.break.toFixed(1)}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="state-space-chart-grid state-space-chart-grid--compact">
        <LineChart title="Forward Regime Share" series={forecastSeries} height={180} />
        <div className="state-space-scenario-grid">
          {stateSpace.forecast.scenarios.map((scenario) => (
            <article key={scenario.key} className={`state-space-card state-space-card--scenario state-space-card--${regimeTone(scenario.dominant_regime)}`}>
              <div className="state-space-card__header">
                <h3>{scenario.label}</h3>
                <span>{scenario.dominant_regime.replace('_', ' ')}</span>
              </div>
              <p className="state-space-card__summary">{scenario.description}</p>
              <div className="state-space-card__value">{scenario.dominant_probability.toFixed(1)}%</div>
              <div className="state-space-card__change">Break share {scenario.break.toFixed(1)}%</div>
              <div className="state-space-card__metrics-inline">
                <span>Sticky {scenario.sticky.toFixed(1)}</span>
                <span>Convex {scenario.convex.toFixed(1)}</span>
                <span>Break {scenario.break.toFixed(1)}</span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
