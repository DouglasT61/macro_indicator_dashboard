import type { EventAnnotationItem, IndicatorSnapshot } from '../types/api';

interface SparklineChartProps {
  indicator: IndicatorSnapshot;
  events: EventAnnotationItem[];
}

const STATUS_COLORS: Record<string, string> = {
  green: '#22c55e',
  yellow: '#facc15',
  orange: '#f97316',
  red: '#ef4444',
};

function buildSparkPath(values: number[], width: number, height: number) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return values
    .map((value, index) => {
      const x = values.length <= 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
}

function buildStepSparkPath(values: number[], width: number, height: number) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return values
    .flatMap((value, index) => {
      const x = values.length <= 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      if (index === 0) {
        return [`M ${x.toFixed(2)} ${y.toFixed(2)}`];
      }
      return [`L ${x.toFixed(2)} ${buildY(values[index - 1], min, range, height)}`, `L ${x.toFixed(2)} ${y.toFixed(2)}`];
    })
    .join(' ');
}

function buildY(value: number, min: number, range: number, height: number) {
  return (height - ((value - min) / range) * height).toFixed(2);
}

export function SparklineChart({ indicator, events }: SparklineChartProps) {
  const values = indicator.history.map((point) => point.value);
  const timestamps = indicator.history.map((point) => point.timestamp.slice(5, 10));
  const relatedEvents = events.filter((event) => event.related_series.includes(indicator.key));
  const width = 320;
  const height = 110;
  const eventIndexes = relatedEvents
    .map((event) => timestamps.indexOf(event.timestamp.slice(5, 10)))
    .filter((index) => index >= 0);

  if (!values.length) {
    return <div className="chart-fallback" style={{ height: 110 }}>No sparkline data.</div>;
  }

  const pathBuilder = indicator.chart_style === 'step' ? buildStepSparkPath : buildSparkPath;

  return (
    <div className="sparkline-chart">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
        {[0.25, 0.5, 0.75].map((ratio) => (
          <line key={ratio} x1="0" y1={height * ratio} x2={width} y2={height * ratio} stroke="rgba(148, 163, 184, 0.10)" strokeWidth="1" />
        ))}
        {eventIndexes.map((index) => {
          const x = values.length <= 1 ? width / 2 : (index / (values.length - 1)) * width;
          return <line key={index} x1={x} y1="0" x2={x} y2={height} stroke="#94a3b8" strokeWidth="1" strokeDasharray="4 4" opacity="0.6" />;
        })}
        <path d={pathBuilder(values, width, height)} fill="none" stroke={STATUS_COLORS[indicator.status]} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
    </div>
  );
}
