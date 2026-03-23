import type { BacktestOverview } from '../types/api';

interface EpisodeComparisonPanelProps {
  backtest: BacktestOverview;
}

function clusterTone(key: string) {
  if (key === 'plumbing') {
    return 'break';
  }
  if (key === 'funding') {
    return 'convex';
  }
  if (key === 'shipping' || key === 'energy') {
    return 'sticky';
  }
  return 'convex';
}

export function EpisodeComparisonPanel({ backtest }: EpisodeComparisonPanelProps) {
  const topEpisode = backtest.episodes[0];

  return (
    <section className="panel-shell episode-shell">
      <div className="panel-shell__header">
        <div>
          <h2>Historical Analogs</h2>
          <p>{backtest.summary}</p>
        </div>
      </div>

      <div className="episode-cluster-row">
        <article className={`episode-shape-card episode-shape-card--${clusterTone(backtest.dominant_cluster)}`}>
          <span>Dominant Subfamily</span>
          <strong>{backtest.dominant_cluster_label}</strong>
          <small>{(backtest.cluster_confidence * 100).toFixed(0)}% confidence</small>
        </article>
        {backtest.clusters.map((cluster) => (
          <article key={cluster.key} className={`episode-shape-card episode-shape-card--${clusterTone(cluster.key)}`}>
            <span>{cluster.label}</span>
            <strong>{cluster.similarity.toFixed(1)}</strong>
            <small>{cluster.episode_count} eps | {cluster.lead_regime}</small>
          </article>
        ))}
      </div>

      {topEpisode ? (
        <div className="episode-shape-row">
          <article className="episode-shape-card episode-shape-card--sticky">
            <span>Sticky Shape</span>
            <strong>{topEpisode.regime_scores.sticky.toFixed(1)}</strong>
          </article>
          <article className="episode-shape-card episode-shape-card--convex">
            <span>Convex Shape</span>
            <strong>{topEpisode.regime_scores.convex.toFixed(1)}</strong>
          </article>
          <article className="episode-shape-card episode-shape-card--break">
            <span>Break Shape</span>
            <strong>{topEpisode.regime_scores.break.toFixed(1)}</strong>
          </article>
        </div>
      ) : null}

      <div className="episode-grid">
        {backtest.episodes.map((episode) => (
          <article key={episode.key} className="episode-card">
            <div className="episode-card__header">
              <div>
                <h3>{episode.label}</h3>
                <p>{episode.period}</p>
              </div>
              <div className="episode-card__score">{episode.similarity.toFixed(1)}</div>
            </div>
            <p className="episode-card__summary">{episode.summary}</p>
            <div className="episode-card__metrics">
              <span>Profile {episode.profile_similarity.toFixed(1)}</span>
              <span>Regime {episode.regime_similarity.toFixed(1)}</span>
              <span>Bias {episode.regime_bias}</span>
              <span>Cluster {episode.cluster_label}</span>
            </div>
            <div className="episode-card__lists">
              <div>
                <strong>Closest</strong>
                <ul>
                  {episode.closest_matches.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <strong>Largest gaps</strong>
                <ul>
                  {episode.furthest_matches.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
