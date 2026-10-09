import Plotly from 'plotly.js-basic-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';

const Plot = createPlotlyComponent(Plotly);

export default function PlotlyChart({ chart }) {
  const layout = {
    ...chart.layout,
    autosize: true,
    margin: { l: 56, r: 16, t: 48, b: 72 },
    font: { family: 'system-ui, sans-serif', size: 12 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
  };

  return (
    <Plot
      data={chart.data}
      layout={layout}
      config={{ displaylogo: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%', height: '340px' }}
    />
  );
}