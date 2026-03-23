import { SparklineChart } from './SparklineChart';
import type { EventAnnotationItem, IndicatorSnapshot } from '../types/api';

interface CompactIndicatorRowProps {
  indicator: IndicatorSnapshot;
  events: EventAnnotationItem[];
}

const SOURCE_LABELS: Record<IndicatorSnapshot['source_class'], string> = {
  live: 'live',
  proxy: 'proxy',
  demo: 'unavailable',
  manual: 'manual',
  auto: 'auto',
};

export function CompactIndicatorRow({ indicator, events }: CompactIndicatorRowProps) {
  const isUnavailable = indicator.source_class === 'demo';
  const valueText = isUnavailable ? 'n/a' : indicator.latest_value.toFixed(2);
  return (
    <article className={`compact-indicator compact-indicator--${indicator.status} ${isUnavailable ? 'compact-indicator--unavailable' : ''}`}>
      <div className="compact-indicator__main">
        <div className="compact-indicator__title-block">
          <strong>{indicator.name}</strong>
          <div className="compact-indicator__meta">
            <span>{indicator.source}</span>
            <span className={`source-pill source-pill--${indicator.source_class}`}>{SOURCE_LABELS[indicator.source_class]}</span>
            <span className={`status-pill status-pill--${indicator.status}`}>{indicator.status}</span>
          </div>
        </div>
        <div className="compact-indicator__value-block">
          <span className="compact-indicator__value">{valueText}</span>
          <span className="compact-indicator__unit">{isUnavailable ? 'unavailable' : indicator.unit}</span>
        </div>
        <div className="compact-indicator__stats">
          <span>Z {isUnavailable ? 'n/a' : indicator.zscore?.toFixed(2) ?? 'n/a'}</span>
          <span>ROC {isUnavailable ? 'n/a' : indicator.rate_of_change?.toFixed(2) ?? 'n/a'}</span>
          <span>Accel {isUnavailable ? 'n/a' : indicator.acceleration?.toFixed(2) ?? 'n/a'}</span>
        </div>
      </div>
      <div className="compact-indicator__sparkline">
        {isUnavailable ? <div className="chart-fallback">Unavailable</div> : <SparklineChart indicator={indicator} events={events} />}
      </div>
    </article>
  );
}
