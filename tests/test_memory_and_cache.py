"""Long-term memory commands, preferences in prompts, and the answer cache."""

import pytest

from src import cache, memory
from src.graph.builder import build_graph

SQL = "SELECT COUNT(*) FROM olist_orders_dataset"


@pytest.mark.parametrize("text,expected", [
    ("Remember that I prefer revenue in descending order", True),
    ("remember to round money to 2 decimals", True),
    ("Always show the newest month first", True),
    ("From now on use English category names", True),
    ("I prefer bar charts", True),
    ("How many orders are there?", False),
    ("Show me the remembered orders", False),
    ("What is the always-on discount rate?", False),
])
def test_is_memory_command(text, expected):
    assert memory.is_memory_command(text) is expected


def test_extract_memory_strips_the_command_words():
    assert memory.extract_memory("Remember that I prefer revenue in BRL") == "I prefer revenue in BRL"
    assert memory.extract_memory("Always show 2 decimals") == "Always show 2 decimals"


@pytest.fixture
def fake_memory(monkeypatch):
    saved = {}

    monkeypatch.setattr(memory, "add_memory", lambda user, text: saved.setdefault(user, []).append(text))
    monkeypatch.setattr(memory, "list_memories", lambda user: saved.get(user, []))
    return saved


def test_remember_command_is_saved_without_calling_the_llm(fake_llm, fake_retrieval, fake_db, fake_memory):
    llm = fake_llm([])
    state = build_graph().invoke({"question": "Remember that I prefer revenue in BRL", "user_id": "u1"})

    assert fake_memory["u1"] == ["I prefer revenue in BRL"]
    assert "I'll remember" in state["answer"]
    assert llm.prompts == []


def test_memory_command_needs_a_user_id(fake_llm, fake_retrieval, fake_db, fake_memory):
    fake_llm(["SQL question", SQL, "ok"])
    fake_db({SQL: (["count"], [[3]])})

    state = build_graph().invoke({"question": "Always count orders"})   # no user_id

    assert fake_memory == {}
    assert state["route"] == "SQL question"


def test_saved_preferences_reach_the_sql_prompt(fake_llm, fake_retrieval, fake_db, fake_memory):
    fake_memory["u1"] = ["I prefer revenue in descending order"]
    llm = fake_llm(["SQL question", SQL, "ok"])
    fake_db({SQL: (["count"], [[3]])})

    build_graph().invoke({"question": "How many orders?", "user_id": "u1"})

    assert "USER PREFERENCES" in llm.prompts[1]
    assert "revenue in descending order" in llm.prompts[1]


def test_no_preferences_means_the_prompt_is_unchanged(fake_llm, fake_retrieval, fake_db, fake_memory):
    llm = fake_llm(["SQL question", SQL, "ok"])
    fake_db({SQL: (["count"], [[3]])})

    build_graph().invoke({"question": "How many orders?", "user_id": "u1"})

    assert "USER PREFERENCES" not in llm.prompts[1]


def test_memory_failure_never_blocks_a_question(monkeypatch, fake_llm, fake_retrieval, fake_db):
    def broken(user):
        raise RuntimeError("db down")

    monkeypatch.setattr(memory, "list_memories", broken)
    fake_llm(["SQL question", SQL, "ok"])
    fake_db({SQL: (["count"], [[3]])})

    state = build_graph().invoke({"question": "How many orders?", "user_id": "u1"})

    assert state["answer"] == "ok"


# ---- cache ------------------------------------------------------------------

def test_cache_key_ignores_case_spacing_and_punctuation():
    assert cache.make_key("How many  orders?") == cache.make_key("how many orders")
    assert cache.make_key("how many orders") != cache.make_key("how many sellers")
    assert cache.make_key("q", "pref A") != cache.make_key("q", "pref B")


def test_cache_entries_expire(monkeypatch):
    cache.clear()
    cache.put("k", {"a": 1})
    assert cache.get("k") == {"a": 1}

    from src import config
    monkeypatch.setattr(config, "CACHE_TTL_SECONDS", -1)
    assert cache.get("k") is None


def test_repeated_question_is_answered_from_the_cache(fake_llm, fake_retrieval, fake_db):
    cache.clear()
    llm = fake_llm(["SQL question", SQL, "3 orders.",     # first call: full path
                    "SQL question"])                      # second call: only the router
    calls = fake_db({SQL: (["count"], [[3]])})
    graph = build_graph(use_cache=True)

    first = graph.invoke({"question": "How many orders?"})
    second = graph.invoke({"question": "how many orders"})

    assert second["cache_hit"] is True
    assert second["answer"] == "3 orders."
    assert second["sql"] == SQL
    assert len(calls) == 1
    assert len(llm.prompts) == 4


def test_failed_queries_are_not_cached(fake_llm, fake_retrieval, fake_db):
    cache.clear()
    bad = "SELECT * FROM nope"
    fake_llm(["SQL question"] + [bad] * 4 + ["could not run"])
    fake_db({bad: Exception("relation does not exist")})

    build_graph(use_cache=True).invoke({"question": "broken question"})

    assert cache.get(cache.make_key("broken question")) is None