import { useEffect, useReducer, useRef, useState } from 'react';
import { approve, ask, clearMemory, getHistory, getMemory } from './api.js';
import { chatReducer, hasPendingApproval, initialState } from './chatReducer.js';
import Message from './components/Message.jsx';
import Sidebar from './components/Sidebar.jsx';

const EXAMPLES = [
  'How many orders were placed in each month?',
  'Top 10 product categories by total item revenue',
  'What is the average review score for each order status?',
  'Remember that I prefer results sorted newest first',
];

export default function App() {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const [memories, setMemories] = useState([]);
  const bottomRef = useRef(null);

  const pending = hasPendingApproval(state);
  const locked = state.busy || pending;

  async function refreshSidebar() {
    try {
      const [h, m] = await Promise.all([getHistory(), getMemory()]);
      setHistory(h);
      setMemories(m);
    } catch {
      /* the sidebar is optional: keep the chat working if it fails */
    }
  }

  useEffect(() => { refreshSidebar(); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [state.messages]);

  async function run(stream) {
    try {
      await stream((name, data) => dispatch({ type: 'event', name, data }));
    } catch (error) {
      dispatch({ type: 'failed', message: error.message || 'Something went wrong.' });
    }
    refreshSidebar();
  }

  function send(text) {
    const question = text.trim();
    if (!question || locked) return;
    setInput('');
    dispatch({ type: 'send', text: question });
    run((onEvent) => ask(question, state.threadId, onEvent));
  }

  function decide(approved) {
    dispatch({ type: 'resume' });
    run((onEvent) => approve(state.threadId, approved, onEvent));
  }

  async function onClearMemory() {
    await clearMemory();
    refreshSidebar();
  }

  return (
    <div className="layout">
      <Sidebar
        history={history}
        memories={memories}
        disabled={locked}
        onNewChat={() => dispatch({ type: 'reset' })}
        onPick={send}
        onClearMemory={onClearMemory}
      />

      <main className="chat">
        <div className="messages" aria-live="polite">
          {state.messages.length === 0 && (
            <div className="empty">
              <h2>What would you like to know?</h2>
              <div className="examples">
                {EXAMPLES.map((example) => (
                  <button key={example} type="button" className="chip-button" onClick={() => send(example)}>
                    {example}
                  </button>
                ))}
              </div>
            </div>
          )}
          {state.messages.map((message) => (
            <Message key={message.id} message={message} busy={state.busy} onDecide={decide} />
          ))}
          <div ref={bottomRef} />
        </div>

        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={pending ? 'Answer the approval card above first…' : 'Ask a question about the data…'}
            maxLength={1000}
            disabled={locked}
            aria-label="Question"
          />
          <button type="submit" className="primary" disabled={locked || !input.trim()}>Send</button>
        </form>
      </main>
    </div>
  );
}