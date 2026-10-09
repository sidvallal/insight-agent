import { useState } from 'react';

export default function SqlBlock({ sqls }) {
  const [copied, setCopied] = useState(false);
  if (!sqls.length) return null;

  const latest = sqls[sqls.length - 1];

  async function copy() {
    try {
      await navigator.clipboard.writeText(latest.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard may be blocked; ignore */
    }
  }

  return (
    <details className="card sql" open>
      <summary>
        SQL{latest.attempt > 1 ? ` (attempt ${latest.attempt}, after fixing an error)` : ''}
      </summary>
      <button type="button" className="ghost copy" onClick={copy}>
        {copied ? 'Copied' : 'Copy'}
      </button>
      <pre><code>{latest.sql}</code></pre>
    </details>
  );
}