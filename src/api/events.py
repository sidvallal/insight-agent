"""Turn LangGraph node updates into the events the browser receives.

Events (name -> data):
    start      {thread_id}
    status     {label, kind}                      progress line ("ok" or "warning")
    rewritten  {question}                         follow-up turned into a full question
    sql        {sql, attempt}
    result     {columns, rows, row_count, truncated}
    answer     {answer}
    chart      {chart}                            a Plotly figure as JSON
    approval   {sql, estimated_cost, threshold}   waiting for a human decision
    done       {thread_id, status, cache_hit, latency_ms}
    error      {message}
"""

import json

from src import config
from src.graph.nodes.approval import CANCELLED_MESSAGE
from src.graph.nodes.router import MEMORY, OUT_OF_SCOPE

Event = tuple[str, dict]


def sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def result_event(update: dict) -> Event:
    rows = update.get("rows") or []
    return "result", {
        "columns": update.get("columns") or [],
        "rows": rows[: config.API_MAX_ROWS],
        "row_count": update.get("row_count", len(rows)),
        "truncated": bool(update.get("truncated")),
    }


def events_for_update(node: str, update: dict) -> list[Event]:
    """Events to send after `node` finished with `update` (the node's returned state)."""
    if node == "router":
        label = {OUT_OF_SCOPE: "Not a data question", MEMORY: "Saving a preference"}.get(
            update.get("route"), "Understood the question")
        return [("status", {"label": label, "kind": "ok"})]

    if node == "rewrite_question":
        return [("rewritten", {"question": update["question"]})]

    if node == "retrieve_schema":
        tables = [chunk["table"] for chunk in update.get("schema_context", [])]
        return [("status", {"label": f"Found relevant tables: {', '.join(tables)}", "kind": "ok"})]

    if node in ("generate_sql", "fix_sql"):
        return [("sql", {"sql": update["sql"], "attempt": update.get("retries", 0) + 1})]

    if node == "execute_sql":
        error = update.get("error")
        if error:
            return [("status", {"label": f"Query failed, trying again: {error[:120]}", "kind": "warning"})]
        return [result_event(update)]

    if node == "analyst":
        return [("answer", {"answer": update.get("answer", "")})]

    if node == "chart":
        return [("chart", {"chart": update["chart"]})] if update.get("chart") else []

    if node in ("refuse", "save_memory", "cancelled"):
        return [("answer", {"answer": update.get("answer", "")})]

    if node == "cache_lookup" and update.get("cache_hit"):
        events: list[Event] = [
            ("status", {"label": "Answered from cache", "kind": "ok"}),
            ("sql", {"sql": update["sql"], "attempt": 1}),
            result_event(update),
            ("answer", {"answer": update.get("answer", "")}),
        ]
        if update.get("chart"):
            events.append(("chart", {"chart": update["chart"]}))
        return events

    return []


def final_status(values: dict) -> str:
    """One word describing how the turn ended (stored in the history)."""
    if values.get("error"):
        return "error"
    if values.get("route") == OUT_OF_SCOPE:
        return "refused"
    if values.get("route") == MEMORY:
        return "memory"
    if values.get("answer") == CANCELLED_MESSAGE:
        return "cancelled"
    return "ok"