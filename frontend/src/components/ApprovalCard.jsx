export default function ApprovalCard({ approval, disabled, onDecide }) {
  return (
    <div className="card approval" role="alert">
      <strong>This query looks expensive</strong>
      <p className="muted">
        Estimated cost {Math.round(approval.estimated_cost).toLocaleString('en-US')} (limit{' '}
        {Math.round(approval.threshold).toLocaleString('en-US')}). It has not been run yet.
      </p>
      <pre><code>{approval.sql}</code></pre>
      <div className="row">
        <button type="button" className="primary" disabled={disabled} onClick={() => onDecide(true)}>
          Run it
        </button>
        <button type="button" className="ghost" disabled={disabled} onClick={() => onDecide(false)}>
          Cancel
        </button>
      </div>
    </div>
  );
}