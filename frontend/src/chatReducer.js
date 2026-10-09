// All chat state changes live here as a pure function, so they are easy to test.

export const initialState = { messages: [], busy: false, threadId: null, nextId: 1 };

function newAssistantMessage(id) {
  return {
    id, role: 'assistant',
    steps: [], sqls: [], result: null, chart: null, answer: '',
    approval: null, status: null, cacheHit: false, latencyMs: null, error: null,
  };
}

function applyEvent(message, name, data) {
  switch (name) {
    case 'status':
      return { ...message, steps: [...message.steps, { label: data.label, kind: data.kind }] };
    case 'rewritten':
      return { ...message, steps: [...message.steps, { label: `Understood as: "${data.question}"`, kind: 'ok' }] };
    case 'sql':
      return { ...message, sqls: [...message.sqls, { sql: data.sql, attempt: data.attempt }] };
    case 'result':
      return { ...message, result: data };
    case 'answer':
      return { ...message, answer: data.answer };
    case 'chart':
      return { ...message, chart: data.chart };
    case 'approval':
      return { ...message, approval: data };
    case 'done':
      return { ...message, status: data.status, cacheHit: data.cache_hit, latencyMs: data.latency_ms };
    case 'error':
      return { ...message, error: data.message };
    default:
      return message;
  }
}

function updateLastAssistant(state, change) {
  const messages = [...state.messages];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].role === 'assistant') {
      messages[i] = change(messages[i]);
      break;
    }
  }
  return { ...state, messages };
}

export function chatReducer(state, action) {
  switch (action.type) {
    case 'send':
      return {
        ...state,
        busy: true,
        nextId: state.nextId + 2,
        messages: [
          ...state.messages,
          { id: state.nextId, role: 'user', text: action.text },
          newAssistantMessage(state.nextId + 1),
        ],
      };

    case 'resume':   // the user answered an approval card
      return updateLastAssistant({ ...state, busy: true }, (m) => ({ ...m, approval: null, status: null }));

    case 'event': {
      let next = updateLastAssistant(state, (m) => applyEvent(m, action.name, action.data));
      if (action.name === 'start') next = { ...next, threadId: action.data.thread_id };
      if (action.name === 'done' || action.name === 'error') next = { ...next, busy: false };
      return next;
    }

    case 'failed':   // network or server failure
      return updateLastAssistant({ ...state, busy: false }, (m) => ({ ...m, error: action.message }));

    case 'reset':
      return initialState;

    default:
      return state;
  }
}

// An approval card is open when the last assistant message is waiting for a decision.
export function hasPendingApproval(state) {
  const last = [...state.messages].reverse().find((m) => m.role === 'assistant');
  return Boolean(last && last.approval);
}