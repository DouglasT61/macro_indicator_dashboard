import { SparklineChart } from './SparklineChart';
import type { EventAnnotationItem, IndicatorSnapshot } from '../types/api';

interface IndicatorTileProps {
  indicator: IndicatorSnapshot;
  events: EventAnnotationItem[];
}

const SOURCE_LABELS: Record<IndicatorSnapshot['source_class'], string> = {
  live: 'live',
  support: 'support',
  proxy: 'proxy',
  demo: 'unavailable',
  manual: 'manual',
  auto: 'auto',
};

function formatShortDate(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function buildAuctionEventSummary(indicator: IndicatorSnapshot) {
  const history = indicator.history ?? [];
  if (history.length === 0) {
    return null;
  }

  const changePoints = history.filter((point, index) => index === 0 || point.value !== history[index - 1].value);
  const latestTimestamp = new Date(history[history.length - 1].timestamp).getTime();
  const warning = indicator.warning_threshold ?? null;
  const critical = indicator.critical_threshold ?? null;

  const isStressed = (value: number) => {
    if (warning === null) {
      return false;
    }
    return indicator.direction === 'high' ? value >= warning : value <= warning;
  };

  const countSince = (days: number) => {
    const cutoff = latestTimestamp - days * 24 * 60 * 60 * 1000;
    return changePoints.filter((point) => {
      const ts = new Date(point.timestamp).getTime();
      return ts >= cutoff && isStressed(point.value);
    }).length;
  };

  const recentChanges = [...changePoints].slice(-3).reverse();
  const lastChange = changePoints.length >= 2 ? changePoints[changePoints.length - 1] : changePoints[0];
  const latestValue = history[history.length - 1].value;
  const thresholdLabel =
    critical !== null && (indicator.direction === 'high' ? latestValue >= critical : latestValue <= critical)
      ? 'critical'
      : isStressed(latestValue)
        ? 'warning'
        : 'background';

  return {
    lastChangeLabel: formatShortDate(lastChange.timestamp),
    stressed3m: countSince(90),
    stressed6m: countSince(180),
    recentChanges,
    thresholdLabel,
  };
}

function formatAuctionCount(value: number | undefined): string {
  if (!value) {
    return 'none';
  }
  return String(value);
}

export function IndicatorTile({ indicator, events }: IndicatorTileProps) {
  const isUnavailable = indicator.source_class === 'demo';
  const isSupport = indicator.source_class === 'support';
  const isProxy = indicator.source_class === 'proxy';
  const isAuto = indicator.source_class === 'auto';
  const isAuctionSeries = indicator.key.startsWith('auction_');
  const auctionSummary = isAuctionSeries ? buildAuctionEventSummary(indicator) : null;
  const auctionBreakdown = indicator.key === 'auction_stress' ? indicator.auction_breakdown ?? [] : [];
  const contribution = indicator.model_contribution;
  const dominantContribution = indicator.dominant_model_contribution ?? 0;
  const dominantRegimeLabel =
    indicator.dominant_model_regime === 'sticky'
      ? 'Sticky'
      : indicator.dominant_model_regime === 'convex'
        ? 'Convex'
        : indicator.dominant_model_regime === 'break'
          ? 'Break'
          : null;

  return (
    <article className={`indicator-tile indicator-tile--${indicator.status} ${isUnavailable ? 'indicator-tile--unavailable' : ''}`}>
      <div className="indicator-tile__header">
        <div>
          <h3>{indicator.name}</h3>
          <div className="indicator-tile__source-row">
            <p>{indicator.source}</p>
            <span className={`source-pill source-pill--${indicator.source_class}`}>{SOURCE_LABELS[indicator.source_class]}</span>
          </div>
        </div>
        <span className={`status-pill status-pill--${indicator.status}`}>{indicator.status}</span>
      </div>
      <div className="indicator-tile__value-row">
        <div className="indicator-tile__value">
          {isUnavailable
            ? dominantContribution.toFixed(2)
            : indicator.latest_value === null
              ? 'n/a'
              : indicator.latest_value.toFixed(2)}
        </div>
        <div className="indicator-tile__unit">{isUnavailable ? 'model score' : indicator.unit}</div>
      </div>
      {isAuctionSeries ? (
        <div className="indicator-tile__auction-summary">
          <div className="indicator-tile__auction-grid">
            <div className="indicator-tile__auction-stat">
              <span className="indicator-tile__auction-label">Window</span>
              <strong>{indicator.chart_window_label ?? 'event'}</strong>
            </div>
            <div className="indicator-tile__auction-stat">
              <span className="indicator-tile__auction-label">Last step</span>
              <strong>{auctionSummary?.lastChangeLabel ?? 'n/a'}</strong>
            </div>
            <div className="indicator-tile__auction-stat">
              <span className="indicator-tile__auction-label">Stressed events (3m)</span>
              <strong>{formatAuctionCount(auctionSummary?.stressed3m)}</strong>
            </div>
            <div className="indicator-tile__auction-stat">
              <span className="indicator-tile__auction-label">Stressed events (6m)</span>
              <strong>{formatAuctionCount(auctionSummary?.stressed6m)}</strong>
            </div>
          </div>
          <div className="indicator-tile__auction-threshold">
            Current state: {auctionSummary?.thresholdLabel ?? indicator.status}
          </div>
          <div className="indicator-tile__auction-threshold">
            {(auctionSummary?.stressed6m ?? 0) > 0
              ? 'Recent stressed auction events have occurred in the last 6 months.'
              : 'No new stressed auction step changes in the last 6 months.'}
          </div>
          {auctionBreakdown.length ? (
            <div className="indicator-tile__auction-breakdown">
              <div className="indicator-tile__auction-events-title">Composite breakdown</div>
              <div className="indicator-tile__auction-breakdown-grid">
                {auctionBreakdown.map((item) => (
                  <div key={item.key} className="indicator-tile__auction-breakdown-item">
                    <span>{item.label}</span>
                    <strong>{item.value.toFixed(1)}</strong>
                    <em>{Math.round(item.weight * 100)}%</em>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {auctionSummary?.recentChanges?.length ? (
            <div className="indicator-tile__auction-events">
              <div className="indicator-tile__auction-events-title">Last recorded step changes</div>
              {auctionSummary.recentChanges.map((point) => (
                <div key={point.timestamp} className="indicator-tile__auction-event">
                  <span>{formatShortDate(point.timestamp)}</span>
                  <strong>{point.value.toFixed(2)}</strong>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <>
          <div className="indicator-tile__metrics">
            <span>Z {isUnavailable ? 'n/a' : indicator.zscore?.toFixed(2) ?? 'n/a'}</span>
            <span>ROC {isUnavailable ? 'n/a' : indicator.rate_of_change?.toFixed(2) ?? 'n/a'}</span>
            <span>Accel {isUnavailable ? 'n/a' : indicator.acceleration?.toFixed(2) ?? 'n/a'}</span>
          </div>
          {indicator.chart_window_label ? <div className="indicator-tile__window">Chart window {indicator.chart_window_label}</div> : null}
        </>
      )}
      {isUnavailable ? (
        <div className="chart-fallback">Live measurement unavailable. Showing model contribution instead.</div>
      ) : isAuctionSeries ? null : (
        <SparklineChart indicator={indicator} events={events} />
      )}
      {isUnavailable && contribution ? (
        <div className="indicator-tile__contribution">
          <div className="indicator-tile__contribution-title">
            Model contribution{dominantRegimeLabel ? ` (${dominantRegimeLabel} lead)` : ''}
          </div>
          <div className="indicator-tile__contribution-grid">
            <span>Sticky {contribution.sticky.toFixed(2)}</span>
            <span>Convex {contribution.convex.toFixed(2)}</span>
            <span>Break {contribution.break.toFixed(2)}</span>
          </div>
        </div>
      ) : null}
      {isSupport ? <p className="indicator-tile__warning">This is a support-derived live construct, not a direct quoted market print.</p> : null}
      {isProxy ? <p className="indicator-tile__warning">This is a proxy-derived signal, not a direct market print.</p> : null}
      {isAuto ? <p className="indicator-tile__warning indicator-tile__warning--auto">This value is auto-refreshed from public-source overlays. Use manual input only if you need an override.</p> : null}
      {isUnavailable ? <p className="indicator-tile__warning indicator-tile__warning--critical">Underlying live feed is unavailable. This card is contributing through the model, not through a live market measurement.</p> : null}
      <p className="indicator-tile__narrative">{indicator.narrative}</p>
    </article>
  );
}
