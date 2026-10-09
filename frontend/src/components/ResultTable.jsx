const VISIBLE_ROWS = 50;

function format(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  return String(value);
}

export default function ResultTable({ result }) {
  if (!result || !result.columns.length) return null;

  const shown = result.rows.slice(0, VISIBLE_ROWS);
  const total = result.row_count;

  return (
    <div className="card table-card">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>{result.columns.map((c) => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {shown.map((row, i) => (
              <tr key={i}>{row.map((v, j) => <td key={j} className={typeof v === 'number' ? 'num' : ''}>{format(v)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="muted table-note">
        {result.truncated
          ? `Showing ${shown.length} of ${total.toLocaleString('en-US')}+ rows (the result was cut off at the row limit)`
          : total > shown.length
            ? `Showing ${shown.length} of ${total.toLocaleString('en-US')} rows`
            : `${total.toLocaleString('en-US')} row${total === 1 ? '' : 's'}`}
      </div>
    </div>
  );
}