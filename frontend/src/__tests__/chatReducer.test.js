import { describe, expect, it } from 'vitest';
import { chatReducer, hasPendingApproval, initialState } from '../chatReducer.js';

const run = (events, state = initialState) =>
  events.reduce((s, [name, data]) => chatReducer(s, { type: 'event', name, data }), state);

const sent = () => chatReducer(initialState, { type: 'send', text: 'Orders by status?' });
const lastAssistant = (state) => state.messages[state.messages.length - 1];

describe('chatReducer', () => {
  it('adds a user message and an empty assistant message when sending', () => {
    const state = sent();
    expect(state.busy).toBe(true);
    expect(state.messages.map((m) => m.role)).toEqual(['user', 'assistant']);
    expect(state.messages[0].text).toBe('Orders by status?');
  });

  it('builds the assistant message from a stream of events', () => {
    const state = run([
      ['start', { thread_id: 'abc' }],
      ['status', { label: 'Understood the question', kind: 'ok' }],
      ['sql', { sql: 'SELECT 1', attempt: 1 }],
      ['result', { columns: ['n'], rows: [[1]], row_count: 1, truncated: false }],
      ['answer', { answer: 'One.' }],
      ['chart', { chart: { data: [], layout: {} } }],
      ['done', { status: 'ok', cache_hit: true, latency_ms: 1200 }],
    ], sent());

    const message = lastAssistant(state);
    expect(state.threadId).toBe('abc');
    expect(state.busy).toBe(false);
    expect(message.steps).toHaveLength(1);
    expect(message.sqls[0].sql).toBe('SELECT 1');
    expect(message.result.row_count).toBe(1);
    expect(message.answer).toBe('One.');
    expect(message.chart).not.toBeNull();
    expect(message.cacheHit).toBe(true);
  });

  it('keeps every SQL attempt and shows warnings as steps', () => {
    const state = run([
      ['sql', { sql: 'bad', attempt: 1 }],
      ['status', { label: 'Query failed', kind: 'warning' }],
      ['sql', { sql: 'good', attempt: 2 }],
    ], sent());
    expect(lastAssistant(state).sqls.map((s) => s.attempt)).toEqual([1, 2]);
    expect(lastAssistant(state).steps[0].kind).toBe('warning');
  });

  it('records a rewritten follow-up as a step', () => {
    const state = run([['rewritten', { question: 'Delivered orders per month?' }]], sent());
    expect(lastAssistant(state).steps[0].label).toContain('Delivered orders per month?');
  });

  it('pauses on approval, then resumes and clears the card', () => {
    let state = run([
      ['approval', { sql: 'SELECT ...', estimated_cost: 5e5, threshold: 1e5 }],
      ['done', { status: 'waiting_approval', cache_hit: false, latency_ms: 50 }],
    ], sent());
    expect(hasPendingApproval(state)).toBe(true);
    expect(state.busy).toBe(false);

    state = chatReducer(state, { type: 'resume' });
    expect(hasPendingApproval(state)).toBe(false);
    expect(state.busy).toBe(true);

    state = run([['answer', { answer: 'Done' }], ['done', { status: 'ok', cache_hit: false, latency_ms: 90 }]], state);
    expect(lastAssistant(state).answer).toBe('Done');
    expect(state.busy).toBe(false);
  });

  it('shows server errors and network failures and stops being busy', () => {
    const fromServer = run([['error', { message: 'boom' }]], sent());
    expect(lastAssistant(fromServer).error).toBe('boom');
    expect(fromServer.busy).toBe(false);

    const failed = chatReducer(sent(), { type: 'failed', message: 'offline' });
    expect(lastAssistant(failed).error).toBe('offline');
    expect(failed.busy).toBe(false);
  });

  it('only changes the latest assistant message', () => {
    let state = run([['answer', { answer: 'first' }], ['done', { status: 'ok', cache_hit: false, latency_ms: 1 }]], sent());
    state = chatReducer(state, { type: 'send', text: 'second' });
    state = run([['answer', { answer: 'second answer' }]], state);
    const answers = state.messages.filter((m) => m.role === 'assistant').map((m) => m.answer);
    expect(answers).toEqual(['first', 'second answer']);
  });

  it('starts over on reset', () => {
    expect(chatReducer(sent(), { type: 'reset' })).toEqual(initialState);
  });
});