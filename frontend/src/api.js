import { createSseParser } from './sse.js';

export const USER_ID = 'demo';
const BASE = import.meta.env.VITE_API_URL ?? '/api';

// POST and read the Server-Sent Events stream, calling onEvent(name, data) for each event.
export async function streamPost(path, body, onEvent) {
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) {
    throw new Error(`The server answered with an error (${response.status}).`);
  }

  const parser = createSseParser(onEvent);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parser.push(decoder.decode(value, { stream: true }));
  }
  parser.end();
}

async function getJson(path, options) {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  return response.json();
}

export const ask = (question, threadId, onEvent) =>
  streamPost('/ask', { question, thread_id: threadId, user_id: USER_ID }, onEvent);

export const approve = (threadId, approved, onEvent) =>
  streamPost('/approve', { thread_id: threadId, approve: approved }, onEvent);

export const getHistory = () => getJson(`/history?user_id=${USER_ID}`);
export const getMemory = () => getJson(`/memory?user_id=${USER_ID}`).then((d) => d.memories);
export const clearMemory = () => getJson(`/memory?user_id=${USER_ID}`, { method: 'DELETE' });