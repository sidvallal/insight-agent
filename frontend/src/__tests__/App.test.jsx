import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../components/PlotlyChart.jsx', () => ({
  default: ({ chart }) => <div>plotly:{chart.data[0].type}</div>,
}));

vi.mock('../api.js', () => ({
  ask: vi.fn(),
  approve: vi.fn(),
  getHistory: vi.fn(),
  getMemory: vi.fn(),
  clearMemory: vi.fn(),
}));

import { approve, ask, clearMemory, getHistory, getMemory } from '../api.js';
import App from '../App.jsx';

const SQL = 'SELECT order_status, COUNT(*) FROM olist_orders_dataset GROUP BY 1';

function script(events) {
  return async (...args) => {
    const onEvent = args[args.length - 1];
    events.forEach(([name, data]) => onEvent(name, data));
  };
}

const answerEvents = [
  ['start', { thread_id: 't1' }],
  ['status', { label: 'Understood the question', kind: 'ok' }],
  ['sql', { sql: SQL, attempt: 1 }],
  ['result', { columns: ['order_status', 'orders'], rows: [['delivered', 1234], ['canceled', 5]], row_count: 2, truncated: false }],
  ['answer', { answer: 'Most orders are delivered.' }],
  ['chart', { chart: { data: [{ type: 'bar', x: [], y: [] }], layout: {} } }],
  ['done', { thread_id: 't1', status: 'ok', cache_hit: false, latency_ms: 1500 }],
];

beforeEach(() => {
  vi.clearAllMocks();
  getHistory.mockResolvedValue([{ id: 1, question: 'Earlier question', status: 'ok' }]);
  getMemory.mockResolvedValue(['I prefer bars']);
  clearMemory.mockResolvedValue({ cleared: true });
});

describe('App', () => {
  it('shows the sidebar with history and saved preferences', async () => {
    render(<App />);
    expect(await screen.findByText('Earlier question')).toBeInTheDocument();
    expect(await screen.findByText('I prefer bars')).toBeInTheDocument();
  });

  it('streams an answer: SQL, table, chart and text', async () => {
    ask.mockImplementation(script(answerEvents));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('Question'), 'Orders by status?');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('Most orders are delivered.')).toBeInTheDocument();
    expect(screen.getByText(SQL)).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();
    expect(screen.getByText('2 rows')).toBeInTheDocument();
    expect(await screen.findByText('plotly:bar')).toBeInTheDocument();
    expect(ask).toHaveBeenCalledWith('Orders by status?', null, expect.any(Function));
    expect(screen.getByLabelText('Question')).toHaveValue('');
  });

  it('reuses the thread id for the next question', async () => {
    ask.mockImplementation(script(answerEvents));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('Question'), 'first{enter}');
    await screen.findByText('Most orders are delivered.');
    await user.type(screen.getByLabelText('Question'), 'only delivered{enter}');

    await waitFor(() => expect(ask).toHaveBeenCalledTimes(2));
    expect(ask.mock.calls[1][1]).toBe('t1');
  });

  it('asks for approval, locks the input, and resumes after "Run it"', async () => {
    ask.mockImplementation(script([
      ['start', { thread_id: 't2' }],
      ['approval', { sql: 'SELECT * FROM big', estimated_cost: 250000, threshold: 100000 }],
      ['done', { thread_id: 't2', status: 'waiting_approval', cache_hit: false, latency_ms: 40 }],
    ]));
    approve.mockImplementation(script([
      ['answer', { answer: 'Approved and finished.' }],
      ['done', { thread_id: 't2', status: 'ok', cache_hit: false, latency_ms: 800 }],
    ]));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('Question'), 'big join{enter}');

    const card = await screen.findByRole('alert');
    expect(within(card).getByText(/This query looks expensive/)).toBeInTheDocument();
    expect(screen.getByLabelText('Question')).toBeDisabled();

    await user.click(within(card).getByRole('button', { name: 'Run it' }));

    expect(await screen.findByText('Approved and finished.')).toBeInTheDocument();
    expect(approve).toHaveBeenCalledWith('t2', true, expect.any(Function));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Question')).toBeEnabled();
  });

  it('sends "false" when the user cancels an expensive query', async () => {
    ask.mockImplementation(script([
      ['start', { thread_id: 't3' }],
      ['approval', { sql: 'SELECT * FROM big', estimated_cost: 250000, threshold: 100000 }],
      ['done', { thread_id: 't3', status: 'waiting_approval', cache_hit: false, latency_ms: 40 }],
    ]));
    approve.mockImplementation(script([
      ['answer', { answer: 'Okay, I did not run that query.' }],
      ['done', { thread_id: 't3', status: 'cancelled', cache_hit: false, latency_ms: 20 }],
    ]));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('Question'), 'big join{enter}');
    await user.click(await screen.findByRole('button', { name: 'Cancel' }));

    expect(await screen.findByText('Okay, I did not run that query.')).toBeInTheDocument();
    expect(approve).toHaveBeenCalledWith('t3', false, expect.any(Function));
  });

  it('shows a readable error when the request fails', async () => {
    ask.mockRejectedValue(new Error('The server answered with an error (500).'));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('Question'), 'anything{enter}');

    expect(await screen.findByText('The server answered with an error (500).')).toBeInTheDocument();
    expect(screen.getByLabelText('Question')).toBeEnabled();
  });

  it('starts a new chat', async () => {
    ask.mockImplementation(script(answerEvents));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('Question'), 'first{enter}');
    await screen.findByText('Most orders are delivered.');
    await user.click(screen.getByRole('button', { name: 'New chat' }));

    expect(screen.queryByText('Most orders are delivered.')).not.toBeInTheDocument();
    expect(screen.getByText('What would you like to know?')).toBeInTheDocument();
  });

  it('asks the question again when a history item is clicked, and clears preferences', async () => {
    ask.mockImplementation(script(answerEvents));
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole('button', { name: /Earlier question/ }));
    await waitFor(() => expect(ask).toHaveBeenCalledWith('Earlier question', null, expect.any(Function)));

    await user.click(screen.getByRole('button', { name: 'Clear preferences' }));
    expect(clearMemory).toHaveBeenCalled();
  });
});