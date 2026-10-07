"""Chat with the agent in the terminal (follow-ups, memory, charts, approval).

    python -m scripts.chat

Optional environment variables:
    CHAT_USER=alice        whose saved preferences to use (default: demo)
    CHAT_THREAD=my-chat    continue a previous conversation (needs CHECKPOINTER=postgres to survive restarts)
"""

import os
import uuid

# Keep conversation checkpoints small: only the first rows of big results are stored.
os.environ.setdefault("STATE_MAX_ROWS", "1000")

from langgraph.types import Command  # noqa: E402

from src.graph.builder import build_graph  # noqa: E402
from src.graph.checkpoint import get_checkpointer  # noqa: E402

PREVIEW_ROWS = 10


def pending_interrupts(graph, config) -> list:
    snapshot = graph.get_state(config)
    return [item for task in snapshot.tasks for item in task.interrupts]


def show(state: dict) -> None:
    if state.get("sql"):
        print(f"\nSQL: {state['sql']}")

    rows = state.get("rows") or []
    if rows:
        print(" | ".join(state["columns"]))
        for row in rows[:PREVIEW_ROWS]:
            print(" | ".join(str(value) for value in row))
        total = state.get("row_count", len(rows))
        if state.get("truncated"):
            print(f"... ({total:,}+ rows: the result was cut off at the row limit)")
        elif total > PREVIEW_ROWS:
            print(f"... ({total:,} rows in total)")

    chart = state.get("chart")
    if chart:
        kind = chart["data"][0]["type"]
        print(f"[chart ready: {'line' if kind == 'scatter' else kind}]")
    if state.get("cache_hit"):
        print("[answered from cache]")

    print(f"\n{state.get('answer', '')}")


def main() -> None:
    user_id = os.getenv("CHAT_USER", "demo")
    thread_id = os.getenv("CHAT_THREAD") or uuid.uuid4().hex[:8]
    config = {"configurable": {"thread_id": thread_id}}

    graph = build_graph(checkpointer=get_checkpointer(), use_cache=True, require_approval=True)
    print(f"InsightAgent  (user: {user_id}, thread: {thread_id}).  Type 'exit' to quit.")
    print("Try: a question, then a follow-up like 'now only delivered orders', or 'Remember that I prefer ...'")

    while True:
        try:
            question = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        state = graph.invoke({"question": question, "user_id": user_id}, config)

        while waiting := pending_interrupts(graph, config):
            info = waiting[0].value
            print(f"\nThis query looks expensive (estimated cost {info['estimated_cost']:,.0f}):")
            print(info["sql"])
            approved = input("Run it? [y/N] ").strip().lower() == "y"
            state = graph.invoke(Command(resume=approved), config)

        show(state)


if __name__ == "__main__":
    main()