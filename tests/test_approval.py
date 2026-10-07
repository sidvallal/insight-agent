"""Human approval for expensive queries (LangGraph interrupt)."""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src import config, gateway
from src.graph.builder import build_graph
from src.graph.nodes.approval import CANCELLED_MESSAGE

SQL = "SELECT COUNT(*) FROM olist_orders_dataset"
CONFIG = {"configurable": {"thread_id": "approval"}}


def pending_interrupts(graph):
    snapshot = graph.get_state(CONFIG)
    return [i for task in snapshot.tasks for i in task.interrupts]


def test_cheap_query_runs_without_asking(fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: 10.0)
    fake_llm(["SQL question", SQL, "3 orders."])
    fake_db({SQL: (["count"], [[3]])})
    graph = build_graph(checkpointer=MemorySaver(), require_approval=True)

    state = graph.invoke({"question": "How many orders?"}, CONFIG)

    assert state["answer"] == "3 orders."
    assert pending_interrupts(graph) == []


def test_expensive_query_waits_and_runs_after_approval(fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: config.APPROVAL_COST_THRESHOLD * 10)
    fake_llm(["SQL question", SQL, "3 orders."])
    calls = fake_db({SQL: (["count"], [[3]])})
    graph = build_graph(checkpointer=MemorySaver(), require_approval=True)

    graph.invoke({"question": "How many orders?"}, CONFIG)

    waiting = pending_interrupts(graph)
    assert len(waiting) == 1
    assert waiting[0].value["sql"] == SQL
    assert waiting[0].value["estimated_cost"] > config.APPROVAL_COST_THRESHOLD
    assert calls == []                                   # nothing ran yet

    state = graph.invoke(Command(resume=True), CONFIG)

    assert state["answer"] == "3 orders."
    assert calls == [SQL]


def test_rejected_query_is_never_executed(fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: config.APPROVAL_COST_THRESHOLD * 10)
    fake_llm(["SQL question", SQL])
    calls = fake_db({SQL: (["count"], [[3]])})
    graph = build_graph(checkpointer=MemorySaver(), require_approval=True)

    graph.invoke({"question": "How many orders?"}, CONFIG)
    state = graph.invoke(Command(resume=False), CONFIG)

    assert state["answer"] == CANCELLED_MESSAGE
    assert calls == []


def test_unknown_cost_goes_straight_to_execution(fake_llm, fake_retrieval, fake_db, monkeypatch):
    monkeypatch.setattr(gateway, "estimate_cost", lambda sql: None)
    fake_llm(["SQL question", SQL, "3 orders."])
    fake_db({SQL: (["count"], [[3]])})
    graph = build_graph(checkpointer=MemorySaver(), require_approval=True)

    state = graph.invoke({"question": "How many orders?"}, CONFIG)

    assert state["answer"] == "3 orders."


def test_approval_requires_a_checkpointer():
    with pytest.raises(ValueError):
        build_graph(require_approval=True)