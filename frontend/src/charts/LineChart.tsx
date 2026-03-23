interface SeriesInput {
  name: string;
  values: Array<{ timestamp: string; value: number }>;
  color: string;
}

interface ThresholdLine {
  label: string;
  value: number;
  color: string;
}

interface LineChartProps {
  title?: string;
  series: SeriesInput[];
  height?: number;
  thresholdLines?: ThresholdLine[];
}

const CHART_WIDTH = 960;
const PADDING = { top: 18, right: 18, bottom: 28, left: 38 };
const LEGEND_HEIGHT = 36;
const TITLE_HEIGHT = 24;

function buildPath(values: number[], chartHeight: number, min: number, max: number) {
  const width = CHART_WIDTH - PADDING.left - PADDING.right;
  const height = chartHeight - PADDING.top - PADDING.bottom;
  const range = max - min || 1;

  return values
    .map((value, index) => {
      const x = PADDING.left + (values.length <= 1 ? width / 2 : (index / (values.length - 1)) * width);
      const y = PADDING.top + height - ((value - min) / range) * height;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
}

export function LineChart({ title, series, height = 280, thresholdLines = [] }: LineChartProps) {
  const containerHeight = height + LEGEND_HEIGHT + (title ? TITLE_HEIGHT : 0);

  if (!series.length || !series[0]?.values.length) {
    return <div className="chart-fallback" style={{ minHeight: containerHeight }}>No chart data.</div>;
  }

  const timestamps = series[0].values.map((item) => item.timestamp.slice(5, 10));
  const allValues = [...series.flatMap((entry) => entry.values.map((point) => point.value)), ...thresholdLines.map((line) => line.value)];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const chartHeight = height;
  const width = CHART_WIDTH - PADDING.left - PADDING.right;
  const drawableHeight = chartHeight - PADDING.top - PADDING.bottom;
  const range = max - min || 1;

  return (
    <div className="svg-chart" style={{ minHeight: containerHeight }}>
      {title ? <div className="svg-chart__title">{title}</div> : null}
      <svg viewBox={`0 0 ${CHART_WIDTH} ${chartHeight}`} preserveAspectRatio="none" style={{ width: '100%', height: chartHeight }}>
        <rect x="0" y="0" width={CHART_WIDTH} height={chartHeight} fill="transparent" />
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = PADDING.top + drawableHeight * ratio;
          return <line key={ratio} x1={PADDING.left} y1={y} x2={CHART_WIDTH - PADDING.right} y2={y} stroke="rgba(148, 163, 184, 0.12)" strokeWidth="1" />;
        })}
        {thresholdLines.map((line) => {
          const y = PADDING.top + drawableHeight - ((line.value - min) / range) * drawableHeight;
          return (
            <g key={line.label}>
              <line x1={PADDING.left} y1={y} x2={CHART_WIDTH - PADDING.right} y2={y} stroke={line.color} strokeWidth="1.5" strokeDasharray="6 6" />
              <text x={CHART_WIDTH - PADDING.right - 4} y={y - 6} fill="#cbd5e1" fontSize="11" textAnchor="end">
                {line.label} ({line.value.toFixed(0)})
              </text>
            </g>
          );
        })}
        {series.map((entry) => (
          <path key={entry.name} d={buildPath(entry.values.map((point) => point.value), chartHeight, min, max)} fill="none" stroke={entry.color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        ))}
        {timestamps.map((label, index) => {
          if (index > 0 && index < timestamps.length - 1 && index % Math.ceil(timestamps.length / 6) !== 0) {
            return null;
          }
          const x = PADDING.left + (timestamps.length <= 1 ? width / 2 : (index / (timestamps.length - 1)) * width);
          return (
            <text key={`${label}-${index}`} x={x} y={chartHeight - 8} fill="#7f8b99" fontSize="11" textAnchor="middle">
              {label}
            </text>
          );
        })}
      </svg>
      <div className="svg-chart__legend">
        {series.map((entry) => (
          <span key={entry.name} className="svg-chart__legend-item">
            <span className="svg-chart__legend-swatch" style={{ backgroundColor: entry.color }} />
            {entry.name}
          </span>
        ))}
      </div>
    </div>
  );
}
