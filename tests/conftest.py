"""Shared fakes: tests never call the real LLM, ChromaDB or PostgreSQL."""

import pytest

from src import gateway, llm
from src.graph.nodes import retrieve


class FakeLLM:
    """Returns scripted answers in order and records every prompt it receives."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answers.pop(0)


@pytest.fixture
def fake_llm(monkeypatch):
    def install(answers):
        fake = FakeLLM(answers)
        monkeypatch.setattr(llm, "ask_llm", fake)
        return fake

    return install


@pytest.fixture
def fake_retrieval(monkeypatch):
    monkeypatch.setattr(
        retrieve, "retrieve_schema",
        lambda question, k=4: [{"table": "olist_orders_dataset", "content": "order columns", "distance": 0.1}],
    )
    monkeypatch.setattr(
        retrieve, "retrieve_examples",
        lambda question, k=3, exclude_ids=None: [
            {"id": "E001", "question": "How many orders?", "content": "Question: q\nSQL: SELECT 1", "distance": 0.1}
        ],
    )


@pytest.fixture
def fake_db(monkeypatch):
    """Fake database: maps SQL text -> (columns, rows) or an Exception to raise."""

    def install(mapping):
        calls = []

        def run_query(sql):
            calls.append(sql)
            outcome = mapping[sql]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(gateway, "run_agent_query", run_query)
        return calls

    return install
