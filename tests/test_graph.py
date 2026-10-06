"""Graph wiring tests with a fake LLM, fake retrieval and fake database."""

import pytest

from src import config
from src.graph.builder import build_graph, should_retry
from src.graph.nodes.execute_sql import EMPTY_RESULT_MESSAGE
from src.graph.nodes.router import FOLLOW_UP, OUT_OF_SCOPE, SQL, parse_route

GOOD = "SELECT COUNT(*) FROM olist_orders_dataset"


def run(question="How many orders are there?"):
    return build_graph().invoke({"question": question, "retries": 0})


# ---- router -----------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("SQL question", SQL),
    ("sql question.", SQL),
    ("Follow-up", FOLLOW_UP),
    ("**Out of scope**", OUT_OF_SCOPE),
    ("out of scope.", OUT_OF_SCOPE),
    ("something unexpected", SQL),   # never refuse because of a formatting slip
])
def test_parse_route(text, expected):
    assert parse_route(text) == expected


# ---- retry decision ---------------------------------------------------------

def test_should_retry_decisions():
    assert should_retry({"error": "boom", "retries": 0}) == "fix_sql"
    assert should_retry({"error": "boom", "retries": config.MAX_RETRIES - 1}) == "fix_sql"
    assert should_retry({"error": "boom", "retries": config.MAX_RETRIES}) == "analyst"
    assert should_retry({"error": "", "retries": 0}) == "analyst"


# ---- end-to-end paths -------------------------------------------------------

def test_happy_path(fake_llm, fake_retrieval, fake_db):
    llm = fake_llm(["SQL question", GOOD, "There are 3 orders."])
    fake_db({GOOD: (["count"], [[3]])})

    state = run()

    assert state["sql"] == GOOD
    assert state["rows"] == [[3]]
    assert state["retries"] == 0
    assert state["answer"] == "There are 3 orders."
    # the table name must reach the SQL-generation prompt
    assert "olist_orders_dataset" in llm.prompts[1]


def test_out_of_scope_is_refused_without_sql(fake_llm, fake_retrieval, fake_db):
    llm = fake_llm(["Out of scope"])
    calls = fake_db({})

    state = run("Write a Python program")

    assert "e-commerce database" in state["answer"]
    assert calls == []            # no query executed
    assert len(llm.prompts) == 1  # no further LLM calls (router only)


def test_sql_error_is_repaired_once(fake_llm, fake_retrieval, fake_db):
    bad = "SELECT COUNT(*) FROM wrong_table"
    fake_llm(["SQL question", bad, GOOD, "There are 3 orders."])
    fake_db({bad: Exception('relation "wrong_table" does not exist'), GOOD: (["count"], [[3]])})

    state = run()

    assert state["sql"] == GOOD
    assert state["retries"] == 1
    assert state["error"] == ""


def test_retries_stop_at_the_cap(fake_llm, fake_retrieval, fake_db):
    bad = "SELECT * FROM nope"
    # router, first SQL, then MAX_RETRIES fixes (all still bad)
    fake_llm(["SQL question"] + [bad] * (1 + config.MAX_RETRIES))
    calls = fake_db({bad: Exception("relation does not exist")})

    state = run()

    assert state["retries"] == config.MAX_RETRIES
    assert len(calls) == 1 + config.MAX_RETRIES
    assert "could not be executed" in state["answer"]


def test_empty_result_gets_one_repair_attempt(fake_llm, fake_retrieval, fake_db):
    first = "SELECT * FROM olist_orders_dataset WHERE order_status = 'Delivered'"
    second = "SELECT * FROM olist_orders_dataset WHERE order_status = 'delivered'"
    llm = fake_llm(["SQL question", first, second, "There are 2 delivered orders."])
    fake_db({first: (["order_id"], []), second: (["order_id"], [["o1"], ["o3"]])})

    state = run()

    assert state["sql"] == second
    assert state["retries"] == 1
    assert EMPTY_RESULT_MESSAGE in llm.prompts[2]   # the fix prompt explains why


def test_genuinely_empty_result_stops_after_one_repair(fake_llm, fake_retrieval, fake_db):
    sql = "SELECT * FROM olist_orders_dataset WHERE order_status = 'unknown'"
    fake_llm(["SQL question", sql, sql])
    calls = fake_db({sql: (["order_id"], [])})

    state = run()

    assert state["retries"] == 1
    assert len(calls) == 2
    assert "no data" in state["answer"]


def test_large_result_is_truncated_for_the_llm(fake_llm, fake_retrieval, fake_db):
    sql = "SELECT order_id FROM olist_orders_dataset"
    rows = [[f"o{i}"] for i in range(100)]
    llm = fake_llm(["SQL question", sql, "Many orders."])
    fake_db({sql: (["order_id"], rows)})

    state = run()

    assert len(state["rows"]) == 100                     # full result kept in state
    analyst_prompt = llm.prompts[-1]
    assert "o19" in analyst_prompt and "o20" not in analyst_prompt
    assert "first 20 of 100 rows" in analyst_prompt     # the LLM is told it is partial
