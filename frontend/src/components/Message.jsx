import ApprovalCard from './ApprovalCard.jsx';
import ChartView from './ChartView.jsx';
import ResultTable from './ResultTable.jsx';
import SqlBlock from './SqlBlock.jsx';

export default function Message({ message, busy, onDecide }) {
  if (message.role === 'user') {
    return <div className="bubble user">{message.text}</div>;
  }

  const working = busy && !message.answer && !message.approval && !message.error;

  return (
    <div className="assistant">
      {message.steps.length > 0 && (
        <ul className="steps" aria-label="Progress">
          {message.steps.map((step, i) => (
            <li key={i} className={step.kind === 'warning' ? 'warn' : ''}>{step.label}</li>
          ))}
          {working && <li className="working">Working…</li>}
        </ul>
      )}
      {message.steps.length === 0 && working && <div className="muted">Thinking…</div>}

      <SqlBlock sqls={message.sqls} />
      <ResultTable result={message.result} />
      {message.chart && <ChartView chart={message.chart} />}

      {message.approval && (
        <ApprovalCard approval={message.approval} disabled={busy} onDecide={onDecide} />
      )}

      {message.answer && <div className="bubble answer">{message.answer}</div>}
      {message.error && <div className="card error" role="alert">{message.error}</div>}

      {message.status && (
        <div className="muted meta">
          {message.cacheHit && <span className="chip">from cache</span>}
          {message.latencyMs != null && <span>{(message.latencyMs / 1000).toFixed(1)} s</span>}
        </div>
      )}
    </div>
  );
}