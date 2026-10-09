import { Suspense, lazy } from 'react';

// Plotly is large, so it is only downloaded when a chart is actually shown.
const PlotlyChart = lazy(() => import('./PlotlyChart.jsx'));

export default function ChartView({ chart }) {
  return (
    <div className="card chart" data-testid="chart">
      <Suspense fallback={<div className="muted pad">Loading chart…</div>}>
        <PlotlyChart chart={chart} />
      </Suspense>
    </div>
  );
}