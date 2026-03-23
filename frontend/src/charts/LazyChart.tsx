import { Suspense, lazy } from 'react';

const ReactECharts = lazy(() => import('echarts-for-react'));

interface LazyChartProps {
  option: Record<string, unknown>;
  style?: React.CSSProperties;
}

export function LazyChart({ option, style }: LazyChartProps) {
  return (
    <Suspense fallback={<div className="chart-fallback" style={style}>Loading chart...</div>}>
      <ReactECharts option={option} style={style} />
    </Suspense>
  );
}
