"""API tests: real FastAPI app and graph, fake LLM / database / history."""

import json

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from src import config, gateway, history, memory
from src.api.events import events_for_update, final_status
from src.api.main import create_app
from src.graph.builder import build_graph

SQL = "SELECT order_status, COUNT(*) AS orders FROM olist_orders_dataset GROUP BY 1"
RESULT = (["order_status", "orders"], [["delivered", 10], ["canceled", 2]])


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def names(events):
    return [name for name, _ in events]


@pytest.fixture
def logged(monkeypatch):
    """Capture history writes and silence the real memory store."""
    rows = []
    monkeypatch.setattr(history, "log_query", lambda *args: rows.append(args))
    monkeypatch.setattr(memory, "list_memories", lambda user: [])
    return rows


@pytest.fixture
def client(logged):
    graph = build_graph(checkpointer=MemorySaver(), use_cache=False, require_approval=True)
    with TestClient(create_app(graph)) as test_client:
        yield test_client


def ask(client, question="Orders by status?", **extra):
    response = client.post("/ask", json={"question": question, **extra})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


# ---- /ask ---------------------------------------------------------------------

def test_ask_streams_the_whole_answer_in_order(client, logged, fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: 10.0)
    fake_llm(["SQL question", SQL, "Delivered orders dominate."])
    fake_db({SQL: RESULT})

    events = ask(client)

    assert names(events) == ["start", "status", "status", "sql", "result", "answer", "chart", "done"]
    data = dict(events)
    assert data["sql"]["sql"] == SQL
    assert data["result"] == {"columns": RESULT[0], "rows": RESULT[1], "row_count": 2, "truncated": False}
    assert data["answer"]["answer"] == "Delivered orders dominate."
    assert data["chart"]["chart"]["data"][0]["type"] == "bar"
    assert data["done"]["status"] == "ok"
    assert data["done"]["thread_id"] == data["start"]["thread_id"]


def test_finished_question_is_written_to_the_history(client, logged, fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: 10.0)
    fake_llm(["SQL question", SQL, "ok"])
    fake_db({SQL: RESULT})

    ask(client, user_id="alice")

    user, thread, question, sql, row_count, status, latency = logged[0]
    assert (user, question, sql, row_count, status) == ("alice", "Orders by status?", SQL, 2, "ok")


def test_follow_up_reuses_the_thread(client, logged, fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: 10.0)
    second_sql = SQL + " ORDER BY 2 DESC"
    llm = fake_llm(["SQL question", SQL, "first", "Follow-up", "Orders by status, sorted?", second_sql, "second"])
    fake_db({SQL: RESULT, second_sql: RESULT})

    first = ask(client)
    thread_id = dict(first)["start"]["thread_id"]
    second = ask(client, "sort that", thread_id=thread_id)

    assert "rewritten" in names(second)
    assert dict(second)["rewritten"]["question"] == "Orders by status, sorted?"


def test_out_of_scope_is_refused_with_a_status(client, logged, fake_llm, fake_retrieval, fake_db):
    fake_llm(["Out of scope"])

    events = ask(client, "Write me a poem")

    assert dict(events)["done"]["status"] == "refused"
    assert "e-commerce database" in dict(events)["answer"]["answer"]


def test_failed_query_is_retried_and_reported(client, logged, fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: 10.0)
    bad = "SELECT * FROM nope"
    fake_llm(["SQL question", bad, SQL, "ok"])
    fake_db({bad: Exception("relation does not exist"), SQL: RESULT})

    events = ask(client)

    warnings = [d for n, d in events if n == "status" and d["kind"] == "warning"]
    assert warnings and "relation does not exist" in warnings[0]["label"]
    assert [d["attempt"] for n, d in events if n == "sql"] == [1, 2]
    assert dict(events)["done"]["status"] == "ok"


def test_result_rows_sent_to_the_browser_are_capped(client, logged, fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: 10.0)
    monkeypatch.setattr(config, "API_MAX_ROWS", 3)
    rows = [[f"o{i}"] for i in range(10)]
    fake_llm(["SQL question", "SELECT order_id FROM olist_orders_dataset", "many"])
    fake_db({"SELECT order_id FROM olist_orders_dataset": (["order_id"], rows)})

    result = dict(ask(client))["result"]

    assert len(result["rows"]) == 3 and result["row_count"] == 10


@pytest.mark.parametrize("payload", [{"question": ""}, {"question": "x" * 1001}, {}])
def test_invalid_questions_are_rejected(client, payload):
    assert client.post("/ask", json=payload).status_code == 422


def test_unexpected_failure_becomes_an_error_event(logged):
    class BrokenGraph:
        def stream(self, *args, **kwargs):
            raise RuntimeError("boom")
            yield

    with TestClient(create_app(BrokenGraph())) as broken:
        events = ask(broken)

    assert names(events) == ["start", "error"]
    assert events[1][1]["message"] == "boom"


# ---- approval -----------------------------------------------------------------

def expensive(monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: config.APPROVAL_COST_THRESHOLD * 5)


def test_expensive_query_pauses_and_can_be_approved(client, logged, fake_llm, fake_retrieval, fake_db, monkeypatch):
    expensive(monkeypatch)
    fake_llm(["SQL question", SQL, "approved answer"])
    calls = fake_db({SQL: RESULT})

    paused = ask(client)
    thread_id = dict(paused)["start"]["thread_id"]

    assert names(paused)[-2:] == ["approval", "done"]
    assert dict(paused)["approval"]["sql"] == SQL
    assert dict(paused)["done"]["status"] == "waiting_approval"
    assert calls == [] and logged == []                    # nothing ran, nothing logged yet

    response = client.post("/approve", json={"thread_id": thread_id, "approve": True})
    resumed = parse_sse(response.text)

    assert dict(resumed)["answer"]["answer"] == "approved answer"
    assert dict(resumed)["done"]["status"] == "ok"
    assert calls == [SQL] and len(logged) == 1


def test_rejected_query_is_cancelled(client, logged, fake_llm, fake_retrieval, fake_db, monkeypatch):
    expensive(monkeypatch)
    fake_llm(["SQL question", SQL])
    calls = fake_db({SQL: RESULT})

    thread_id = dict(ask(client))["start"]["thread_id"]
    resumed = parse_sse(client.post("/approve", json={"thread_id": thread_id, "approve": False}).text)

    assert dict(resumed)["done"]["status"] == "cancelled"
    assert calls == []


# ---- other endpoints ----------------------------------------------------------

def test_history_and_memory_endpoints(client, monkeypatch):
    monkeypatch.setattr(history, "list_history", lambda user, limit: [{"question": f"{user}:{limit}"}])
    monkeypatch.setattr(memory, "list_memories", lambda user: ["I prefer bars"])
    cleared = []
    monkeypatch.setattr(memory, "clear_memories", lambda user: cleared.append(user))

    assert client.get("/history?user_id=bob&limit=5").json() == [{"question": "bob:5"}]
    assert client.get("/memory").json() == {"memories": ["I prefer bars"]}
    assert client.delete("/memory?user_id=bob").json() == {"cleared": True}
    assert cleared == ["bob"]


def test_health_reports_database_state(client, monkeypatch):
    from src import db

    monkeypatch.setattr(db, "run_query", lambda sql: (["x"], [[1]]))
    assert client.get("/health").json() == {"status": "ok", "database": True}

    def down(sql):
        raise RuntimeError("no db")

    monkeypatch.setattr(db, "run_query", down)
    assert client.get("/health").json() == {"status": "degraded", "database": False}


def test_cors_allows_the_frontend_origin(client):
    response = client.options(
        "/ask",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


# ---- event mapping ------------------------------------------------------------

def test_cache_hit_replays_the_stored_answer():
    update = {"cache_hit": True, "sql": SQL, "columns": RESULT[0], "rows": RESULT[1],
              "row_count": 2, "answer": "cached", "chart": {"data": [], "layout": {}}}

    assert names(events_for_update("cache_lookup", update)) == ["status", "sql", "result", "answer", "chart"]
    assert events_for_update("cache_lookup", {"cache_hit": False}) == []


def test_final_status_values():
    assert final_status({"error": "x"}) == "error"
    assert final_status({"route": "Out of scope"}) == "refused"
    assert final_status({"route": "Memory"}) == "memory"
    assert final_status({"route": "SQL question", "answer": "fine"}) == "ok"

def test_root_points_to_the_docs_and_health(client):
    assert client.get("/").json() == {"name": "InsightAgent API", "docs": "/docs", "health": "/health"}

def test_a_history_entry_can_be_deleted(client, monkeypatch):
    deleted = []
    monkeypatch.setattr(history, "delete_entry", lambda user, entry_id: deleted.append((user, entry_id)) or True)

    response = client.delete("/history/7?user_id=alice")

    assert response.json() == {"deleted": True}
    assert deleted == [("alice", 7)]


def test_deleting_a_missing_or_foreign_entry_gives_404(client, monkeypatch):
    monkeypatch.setattr(history, "delete_entry", lambda user, entry_id: False)

    assert client.delete("/history/999").status_code == 404
    assert client.delete("/history/not-a-number").status_code == 422


def test_the_whole_history_can_be_cleared(client, monkeypatch):
    monkeypatch.setattr(history, "clear_history", lambda user: 5)

    assert client.delete("/history?user_id=alice").json() == {"deleted": 5}