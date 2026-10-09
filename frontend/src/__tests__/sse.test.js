import { describe, expect, it } from 'vitest';
import { createSseParser } from '../sse.js';

function collect(chunks) {
  const events = [];
  const parser = createSseParser((name, data) => events.push([name, data]));
  chunks.forEach((chunk) => parser.push(chunk));
  parser.end();
  return events;
}

describe('createSseParser', () => {
  it('parses complete events', () => {
    const events = collect(['event: start\ndata: {"thread_id":"t1"}\n\nevent: done\ndata: {"status":"ok"}\n\n']);
    expect(events).toEqual([['start', { thread_id: 't1' }], ['done', { status: 'ok' }]]);
  });

  it('handles an event split across several chunks', () => {
    const events = collect(['event: sq', 'l\ndata: {"sql":"SEL', 'ECT 1"}\n', '\n']);
    expect(events).toEqual([['sql', { sql: 'SELECT 1' }]]);
  });

  it('accepts Windows line endings, even split between chunks', () => {
    const events = collect(['event: status\r\ndata: {"label":"x"}\r', '\n\r\n']);
    expect(events).toEqual([['status', { label: 'x' }]]);
  });

  it('flushes a last event that has no blank line after it', () => {
    expect(collect(['event: done\ndata: {"a":1}'])).toEqual([['done', { a: 1 }]]);
  });

  it('ignores blocks without data and keeps unicode intact', () => {
    const events = collect([': comment\n\nevent: answer\ndata: {"answer":"Café — 5 €"}\n\n']);
    expect(events).toEqual([['answer', { answer: 'Café — 5 €' }]]);
  });
});