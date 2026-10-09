export default function Sidebar({ history, memories, onNewChat, onPick, onClearMemory, disabled }) {
  return (
    <aside className="sidebar">
      <h1>InsightAgent</h1>
      <p className="muted">Ask questions about the Olist e-commerce data.</p>
      <button type="button" className="primary wide" onClick={onNewChat} disabled={disabled}>
        New chat
      </button>

      <section>
        <h2>Saved preferences</h2>
        {memories.length === 0 ? (
          <p className="muted small">None yet. Try: “Remember that I prefer results sorted newest first”.</p>
        ) : (
          <>
            <ul className="plain">
              {memories.map((m) => <li key={m}>{m}</li>)}
            </ul>
            <button type="button" className="ghost small" onClick={onClearMemory}>Clear preferences</button>
          </>
        )}
      </section>

      <section>
        <h2>Recent questions</h2>
        {history.length === 0 ? (
          <p className="muted small">Nothing asked yet.</p>
        ) : (
          <ul className="plain history">
            {history.map((h) => (
              <li key={h.id}>
                <button type="button" className="link" onClick={() => onPick(h.question)} disabled={disabled} title="Ask again">
                  <span className={`dot ${h.status}`} aria-hidden="true" />
                  {h.question}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}